import os
import asyncio
import threading
import logging
from pathlib import Path
from typing import Optional, Any
import urllib.request
import urllib.error
import json
from datetime import datetime, timedelta, time
import zoneinfo
from dotenv import load_dotenv

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select

from backend.database import SessionLocal
from backend.models import CallRecord, Agent

current_dir = Path(__file__).resolve().parent
load_dotenv(current_dir / ".env")
load_dotenv(current_dir.parent / ".env")

logger = logging.getLogger("DiscordBotService")

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0") or "0")
DISCORD_ACCEPTED_CHANNEL_ID = int(os.getenv("DISCORD_ACCEPTED_CHANNEL_ID", "0") or "0")
DISCORD_CLOSED_CHANNEL_ID = int(os.getenv("DISCORD_CLOSED_CHANNEL_ID", "0") or "0")

intents = discord.Intents.default()
intents.message_content = False
bot = commands.Bot(command_prefix="!", intents=intents)

_bot_loop = None

# กำหนด Timezone ประเทศไทยและเวลาแจ้งเตือนรอบประจำวัน
BKK_TZ = zoneinfo.ZoneInfo("Asia/Bangkok")
ALERT_TIMES = [
    time(hour=9, minute=0, tzinfo=BKK_TZ),
    time(hour=13, minute=0, tzinfo=BKK_TZ)
]


# ==========================================
# 👥 Dropdown เลือกพนักงานจาก Database
# ==========================================
class AgentSelectDropdown(Select):
    def __init__(self, record_id: int):
        self.record_id = record_id

        db = SessionLocal()
        options = []
        try:
            agents = (
                db.query(Agent)
                .filter(Agent.is_active.is_(True))
                .order_by(Agent.agent_code.asc())
                .all()
            )
            for a in agents:
                label = f"{a.firstname} {a.lastname}"
                if a.nickname:
                    label += f" ({a.nickname})"
                desc = f"รหัส: {a.agent_code} | {a.department or 'Call Center'}"
                options.append(
                    discord.SelectOption(
                        label=label[:100],
                        value=str(a.agent_code),
                        description=desc[:100],
                        emoji="👤"
                    )
                )
        except Exception as e:
            logger.error(f"Error querying agents: {e}")
        finally:
            db.close()

        if not options:
            options.append(
                discord.SelectOption(
                    label="ไม่พบข้อมูลพนักงานในระบบ",
                    value="none",
                    description="กรุณาเพิ่มพนักงานในระบบก่อน"
                )
            )

        super().__init__(
            placeholder="🔍 เลือกพนักงานเพื่อรับผิดชอบเคสนี้...",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id=f"select_agent_{record_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        # ⚡ ตอบกลับ Discord ทันทีเพื่อป้องกัน Interaction Timeout 3 วินาที
        await interaction.response.defer(ephemeral=True)

        selected_agent_code = self.values[0]
        if selected_agent_code == "none":
            await interaction.followup.send("❌ ไม่สามารถเลือกได้เนื่องจากไม่มีข้อมูลพนักงาน", ephemeral=True)
            return

        db = SessionLocal()
        try:
            record = db.query(CallRecord).filter(CallRecord.id == self.record_id).first()
            if not record:
                record = db.query(CallRecord).order_by(CallRecord.id.desc()).first()

            agent = db.query(Agent).filter(Agent.agent_code == selected_agent_code).first()

            if not agent:
                await interaction.followup.send("❌ ไม่พบข้อมูลพนักงานในระบบ", ephemeral=True)
                return

            staff_display = f"{agent.firstname} {agent.lastname}"
            if agent.nickname:
                staff_display += f" ({agent.nickname})"

            actual_record_id = record.id if record else self.record_id

            # 🛠️ บันทึกลง Database
            if record:
                record.assigned_agent_code = agent.agent_code
                if hasattr(record, "handled_by"):
                    record.handled_by = agent.agent_code
                if hasattr(record, "handled_at"):
                    record.handled_at = datetime.now()
                if hasattr(record, "case_stage"):
                    record.case_stage = "in_progress"

                record.status = "done"
                record.is_active = True
                db.commit()
                db.refresh(record)

            # ค้นหาห้อง "#รับเคสมาแล้ว"
            target_accepted_channel = None
            if DISCORD_ACCEPTED_CHANNEL_ID:
                target_accepted_channel = bot.get_channel(DISCORD_ACCEPTED_CHANNEL_ID)
                if not target_accepted_channel:
                    try:
                        target_accepted_channel = await bot.fetch_channel(DISCORD_ACCEPTED_CHANNEL_ID)
                    except Exception:
                        pass

            if not target_accepted_channel and interaction.guild:
                target_accepted_channel = discord.utils.get(
                    interaction.guild.text_channels, name="รับเคสมาแล้ว"
                )

            # คัดลอกและอัปเดต Embed
            old_embed = None
            if interaction.message and interaction.message.embeds:
                old_embed = interaction.message.embeds[0]

            new_embed = discord.Embed(
                title=old_embed.title if old_embed else "📋 รายงานการวิเคราะห์เคส",
                color=0xF1C40F,  # สีเหลือง: กำลังดำเนินการ
                timestamp=discord.utils.utcnow()
            )

            if old_embed:
                for f in old_embed.fields:
                    if f.name == "ผู้รับผิดชอบ":
                        new_embed.add_field(name="ผู้รับผิดชอบ", value=f"👤 {staff_display}", inline=f.inline)
                    elif f.name == "สถานะ":
                        new_embed.add_field(name="สถานะ", value="🟡 กำลังดำเนินการ", inline=f.inline)
                    elif f.name == "⚙️ การดำเนินการล่าสุด":
                        new_embed.add_field(name="⚙️ การดำเนินการล่าสุด", value=f"รับเคสแล้วโดย {staff_display}", inline=False)
                    else:
                        new_embed.add_field(name=f.name, value=f.value, inline=f.inline)
                if old_embed.footer:
                    new_embed.set_footer(text=old_embed.footer.text)

            # ชุดปุ่มสำหรับการ์ดในห้อง "#รับเคสมาแล้ว"
            accepted_view = View(timeout=None)
            accepted_view.add_item(
                Button(
                    label=f"ผู้รับผิดชอบ: {staff_display}",
                    style=discord.ButtonStyle.secondary,
                    disabled=True,
                    emoji="👤"
                )
            )
            accepted_view.add_item(
                Button(
                    label="ปิดเคส",
                    style=discord.ButtonStyle.danger,
                    emoji="🔒",
                    custom_id=f"btn_close_{actual_record_id}"
                )
            )

            # 1. ส่งการ์ดใหม่เข้าห้อง "#รับเคสมาแล้ว"
            if target_accepted_channel:
                await target_accepted_channel.send(
                    content=f"🔔 @here 📌 **[เคสติดตามงาน] มอบหมายให้: {staff_display} (กำลังดำเนินการ)**",
                    embed=new_embed,
                    view=accepted_view
                )

            # 2. อัปเดตข้อความเดิมในห้องหลัก (จะถูกลบอัตโนมัติเมื่อครบ 1 วัน)
            if interaction.message:
                moved_view = View(timeout=None)
                moved_view.add_item(
                    Button(
                        label=f"ย้ายไปห้องรับเคสมาแล้ว โดย {staff_display}",
                        style=discord.ButtonStyle.secondary,
                        disabled=True,
                        emoji="✅"
                    )
                )
                try:
                    await interaction.message.edit(
                        content=f"✅ **[เคสย้ายแล้ว]** เคส CLM-2026-{str(actual_record_id).zfill(6)} ถูกรับงานโดย {staff_display} และย้ายไปห้อง **#รับเคสมาแล้ว** เรียบร้อย",
                        embed=new_embed,
                        view=moved_view
                    )
                except Exception:
                    pass

            await interaction.followup.send(
                f"🎉 เคส CLM-2026-{str(actual_record_id).zfill(6)} มอบหมายให้คุณ **{staff_display}** เรียบร้อยแล้ว และย้ายไปที่ห้อง **#รับเคสมาแล้ว** แล้วครับ",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error assigning agent: {e}")
            await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}", ephemeral=True)
        finally:
            db.close()


class AgentSelectView(View):
    def __init__(self, record_id: int):
        super().__init__(timeout=120)
        self.add_item(AgentSelectDropdown(record_id=record_id))


# ==========================================
# 🛰️ BOT EVENTS & INTERACTIONS
# ==========================================
@bot.event
async def on_ready():
    logger.info(f"🤖 [Discord Bot] ออนไลน์เรียบร้อยแล้วในชื่อ {bot.user}")

    # เริ่ม Background Tasks ตรวจสอบข้อความและแจ้งเตือน
    if not cleanup_old_discord_messages.is_running():
        cleanup_old_discord_messages.start()

    if not check_unclaimed_urgent_cases.is_running():
        check_unclaimed_urgent_cases.start()


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        cid = interaction.data.get("custom_id", "")

        # 🟢 เมื่อกดปุ่ม "รับเคส"
        if cid.startswith("btn_claim_"):
            await interaction.response.defer(ephemeral=True)

            try:
                record_id = int(cid.replace("btn_claim_", ""))
            except ValueError:
                record_id = 1

            view = AgentSelectView(record_id=record_id)
            await interaction.followup.send(
                "📋 **กรุณาเลือกพนักงานเพื่อรับผิดชอบเคสนี้:**",
                view=view,
                ephemeral=True
            )

        # 🔴 เมื่อกดปุ่ม "ปิดเคส" -> ส่งต่อไปห้อง #ปิดเคส
        elif cid.startswith("btn_close_"):
            await interaction.response.defer(ephemeral=True)

            try:
                record_id = int(cid.replace("btn_close_", ""))
            except ValueError:
                record_id = 1

            db = SessionLocal()
            try:
                record = db.query(CallRecord).filter(CallRecord.id == record_id).first()
                if record:
                    record.status = "done"
                    if hasattr(record, "case_stage"):
                        record.case_stage = "resolved"
                    db.commit()

                # ค้นหาห้อง #ปิดเคส จาก ID หรือชื่อห้อง
                target_closed_channel = None
                if DISCORD_CLOSED_CHANNEL_ID:
                    target_closed_channel = bot.get_channel(DISCORD_CLOSED_CHANNEL_ID)
                    if not target_closed_channel:
                        try:
                            target_closed_channel = await bot.fetch_channel(DISCORD_CLOSED_CHANNEL_ID)
                        except Exception:
                            pass

                if not target_closed_channel and interaction.guild:
                    target_closed_channel = discord.utils.get(
                        interaction.guild.text_channels, name="ปิดเคส"
                    )

                # สร้าง Embed สรุปการปิดเคส
                closed_embed = None
                if interaction.message and interaction.message.embeds:
                    closed_embed = interaction.message.embeds[0]
                    for i, field in enumerate(closed_embed.fields):
                        if field.name == "สถานะ":
                            closed_embed.set_field_at(i, name="สถานะ", value="✅ ปิดเคสแล้ว", inline=True)
                        elif field.name == "⚙️ การดำเนินการล่าสุด":
                            closed_embed.set_field_at(i, name="⚙️ การดำเนินการล่าสุด", value=f"ปิดเคสโดย {interaction.user.display_name}", inline=False)
                    closed_embed.color = 0x95A5A6  # สีเทา: ดำเนินการเสร็จสิ้น

                closed_view = View(timeout=None)
                closed_view.add_item(
                    Button(
                        label=f"ปิดเคสแล้ว โดย {interaction.user.display_name}",
                        style=discord.ButtonStyle.secondary,
                        disabled=True,
                        emoji="🔒"
                    )
                )

                # 1. ย้ายการ์ดไปโพสต์ในห้อง #ปิดเคส
                if target_closed_channel:
                    await target_closed_channel.send(
                        content=f"🏁 **[ปิดเคสสำเร็จ]** เคส CLM-2026-{str(record_id).zfill(6)} ปิดงานโดย {interaction.user.mention}",
                        embed=closed_embed,
                        view=closed_view
                    )

                # 2. 🧹 ลบการ์ดเดิมออกจากห้อง #รับเคสมาแล้ว ทันที
                if interaction.message:
                    try:
                        await interaction.message.delete()
                    except discord.NotFound:
                        pass
                    except Exception as del_err:
                        logger.warning(f"Could not delete message: {del_err}")

                await interaction.followup.send(f"🔒 ปิดเคส ID: #{record_id} เรียบร้อยแล้ว และย้ายไปห้อง **#ปิดเคส** แล้วครับ", ephemeral=True)
            except Exception as e:
                logger.error(f"Close case error: {e}")
                await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}", ephemeral=True)
            finally:
                db.close()


# ========================================================
# 🧹 Task 1: ล้างข้อความเก่าอัตโนมัติ (ตรวจเช็กทุกชั่วโมง)
# ========================================================
@tasks.loop(hours=1)
async def cleanup_old_discord_messages():
    """
    - ห้องทั่วไป: ลบการ์ดที่รับงานแล้วเมื่ออายุครบ 1 วัน (24 ชม.)
    - ห้องรับเคสมาแล้ว: ลบการ์ดที่ปิดเคสแล้วเมื่ออายุครบ 2 วัน (48 ชม.)
    - ห้องปิดเคส: ลบประวัติการ์ดปิดเคสแล้วเมื่ออายุครบ 2 วัน (ช่วง 1-3 วัน)
    """
    if not bot.is_ready():
        return

    now = datetime.now(BKK_TZ)

    # 1. ห้องทั่วไป (ลบการ์ดที่รับงานแล้วครบ 1 วัน)
    general_channel_id = DISCORD_CHANNEL_ID
    if general_channel_id:
        channel = bot.get_channel(general_channel_id)
        if channel:
            try:
                async for msg in channel.history(limit=50):
                    if msg.author == bot.user:
                        age = now - msg.created_at.astimezone(BKK_TZ)
                        is_moved = "[เคสย้ายแล้ว]" in msg.content or "ย้ายไปห้องรับเคสมาแล้ว" in str(msg.components)
                        if is_moved and age >= timedelta(days=1):
                            await msg.delete()
                            logger.info(f"🧹 ลบข้อความเคสย้ายแล้วในห้องทั่วไป ID: {msg.id}")
            except Exception as e:
                logger.error(f"Error cleaning general channel: {e}")

    # 2. ห้องรับเคสมาแล้ว (ลบการ์ดค้างเก่าหลังครบ 2 วัน)
    accepted_channel_id = DISCORD_ACCEPTED_CHANNEL_ID
    if accepted_channel_id:
        channel = bot.get_channel(accepted_channel_id)
        if channel:
            try:
                async for msg in channel.history(limit=50):
                    if msg.author == bot.user:
                        age = now - msg.created_at.astimezone(BKK_TZ)
                        is_closed = "ปิดเคสเรียบร้อยแล้ว" in msg.content or "ปิดเคสแล้ว" in str(msg.components)
                        if is_closed and age >= timedelta(days=2):
                            await msg.delete()
                            logger.info(f"🧹 ลบข้อความในห้องรับเคสมาแล้ว ID: {msg.id}")
            except Exception as e:
                logger.error(f"Error cleaning accepted channel: {e}")

    # 3. ห้องปิดเคส (ลบข้อความเก่าหลังผ่านไป 2 วัน)
    closed_channel_id = DISCORD_CLOSED_CHANNEL_ID
    target_clean_closed = bot.get_channel(closed_channel_id) if closed_channel_id else None
    if not target_clean_closed and bot.guilds:
        target_clean_closed = discord.utils.get(bot.guilds[0].text_channels, name="ปิดเคส")

    if target_clean_closed:
        try:
            async for msg in target_clean_closed.history(limit=50):
                if msg.author == bot.user:
                    age = now - msg.created_at.astimezone(BKK_TZ)
                    if age >= timedelta(days=2):
                        await msg.delete()
                        logger.info(f"🧹 ลบข้อความเก่าในห้องปิดเคส ID: {msg.id}")
        except Exception as e:
            logger.error(f"Error cleaning closed channel: {e}")


# ========================================================
# ⏰ Task 2: แจ้งเตือนเคสค้างที่ยังไม่มีคนรับ (วันทำงาน 09:00, 13:00)
# ========================================================
@tasks.loop(time=ALERT_TIMES)
async def check_unclaimed_urgent_cases():
    """แจ้งเตือนทุกวันจันทร์ - ศุกร์ เวลา 09:00 และ 13:00 น. หากมีเคส VVIP ค้างรอรับงาน"""
    if not bot.is_ready():
        return

    now = datetime.now(BKK_TZ)
    # จันทร์(0) ถึง ศุกร์(4) — เสาร์และอาทิตย์ไม่แจ้งเตือน
    if now.weekday() > 4:
        return

    db = SessionLocal()
    try:
        unclaimed_cases = db.query(CallRecord).filter(
            CallRecord.is_active.is_(True),
            (CallRecord.assigned_agent_code == None) | (CallRecord.assigned_agent_code == ""),
            ~CallRecord.filename.like("manual_%")
        ).all()

        unclaimed_vvip = [
            c for c in unclaimed_cases 
            if str(c.brand or "").strip().lower() == "omazz" or str(getattr(c, "priority", "")).lower() == "vvip"
        ]

        if not unclaimed_vvip:
            return

        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title=f"⚠️ แจ้งเตือน: มีเคส VVIP ค้างรอรับงาน {len(unclaimed_vvip)} เคส",
                description="กรุณาตรวจสอบและกดรับมอบหมายงานเพื่อประกบดูแลลูกค้าโดยเร็ว",
                color=0xE74C3C,
                timestamp=discord.utils.utcnow()
            )
            
            case_list_str = ""
            for c in unclaimed_vvip[:5]:
                case_list_str += f"• **CLM-2026-{str(c.id).zfill(6)}** | เบอร์: `{c.customer_phone or '-'}` ({str(c.issue or 'ไม่ระบุ')[:30]})\n"

            if len(unclaimed_vvip) > 5:
                case_list_str += f"...และอีก {len(unclaimed_vvip) - 5} เคสบนหน้าเว็บ War Room"

            embed.add_field(name="📋 รายการเคสค้าง", value=case_list_str, inline=False)
            embed.set_footer(text="OMAZZ CALLING • Daily Schedule Notification")

            await channel.send(
                content="📢 @here **แจ้งเตือนรอบงานประจำวัน (09:00 / 13:00)**",
                embed=embed
            )
    except Exception as e:
        logger.error(f"Error running daily alert: {e}")
    finally:
        db.close()


# ==========================================
# 🔄 ซิงค์การรับเคสจากหน้าเว็บส่งเข้า Discord
# ==========================================
async def notify_web_claim_to_discord(case_id: int, agent_code: str):
    """ส่งข้อความเข้าห้อง #รับเคสมาแล้ว เมื่อมีการมอบหมายงานจากหน้าเว็บ"""
    if not bot.is_ready():
        return

    db = SessionLocal()
    agent_name = agent_code
    record = None
    try:
        ag = db.query(Agent).filter(Agent.agent_code == agent_code).first()
        if ag:
            agent_name = f"{ag.firstname} {ag.lastname}" + (f" ({ag.nickname})" if ag.nickname else "")
        record = db.query(CallRecord).filter(CallRecord.id == case_id).first()
    finally:
        db.close()

    # ล็อกเป้าหมายไปที่ห้อง 1559837806476525618 (#รับเคสมาแล้ว)
    target_channel_id = DISCORD_ACCEPTED_CHANNEL_ID or 1559837806476525618
    target_channel = bot.get_channel(target_channel_id)
    if not target_channel:
        try:
            target_channel = await bot.fetch_channel(target_channel_id)
        except Exception as e:
            logger.error(f"Cannot fetch accepted channel ID {target_channel_id}: {e}")

    if target_channel:
        brand = record.brand if record else "Omazz"
        phone = record.customer_phone if record else "-"
        issue = record.issue if record else "-"

        embed = discord.Embed(
            title=f"📋 รายงานการวิเคราะห์เคส ({brand})",
            description=f"เคส **CLM-2026-{str(case_id).zfill(6)}** ได้รับการมอบหมายงานเรียบร้อยแล้ว",
            color=0xF1C40F, # สีเหลือง: กำลังดำเนินการ
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="แบรนด์", value=str(brand), inline=True)
        embed.add_field(name="ลูกค้า", value=str(phone), inline=True)
        embed.add_field(name="สถานะ", value="🟡 กำลังดำเนินการ", inline=True)
        embed.add_field(name="ผู้รับผิดชอบ", value=f"👤 **{agent_name}** (`{agent_code}`)", inline=True)
        embed.add_field(name="📌 ประเด็นปัญหา", value=str(issue)[:200], inline=False)
        embed.set_footer(text="OMAZZ CALLING • Workflow Control")

        view = View(timeout=None)
        view.add_item(
            Button(
                label=f"ผู้รับผิดชอบ: {agent_name}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                emoji="👤"
            )
        )
        view.add_item(
            Button(
                label="ปิดเคส",
                style=discord.ButtonStyle.danger,
                emoji="🔒",
                custom_id=f"btn_close_{case_id}"
            )
        )

        await target_channel.send(
            content=f"🔔 @here 📌 **[เคสติดตามงาน] มอบหมายให้: {agent_name} (กำลังดำเนินการ)**",
            embed=embed,
            view=view
        )
        logger.info(f"✅ ยิงการ์ดเข้าห้อง #รับเคสมาแล้ว (ID: {target_channel.id}) สำเร็จ")

def trigger_discord_claim_notification(case_id: int, agent_code: str):
    """ฟังก์ชันสั่งให้ Event Loop ของบอทส่งข้อความข้าม Thread"""
    global _bot_loop
    if _bot_loop and _bot_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            notify_web_claim_to_discord(case_id, agent_code),
            _bot_loop
        )


# ==========================================
# 📨 SEND FUNCTIONS
# ==========================================
def _send_ticket_card_bot_api(
    token: str,
    channel_id: int,
    ref_id: str,
    brand: str,
    customer_phone: str,
    score: str,
    issue: str,
    summary: str,
) -> bool:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (CallCenterAI, 1.0)",
    }

    safe_phone = str(customer_phone or "-")
    if safe_phone.strip() in ["", "—"]:
        safe_phone = "-"

    try:
        numeric_id = int(ref_id)
    except ValueError:
        numeric_id = 1

    payload = {
        "content": "🚨 **[เคสติดตามงาน] มอบหมายให้: ยังไม่ระบุ (รอรับงาน)**",
        "embeds": [
            {
                "title": f"📋 รายงานการวิเคราะห์เคส ({brand})",
                "color": 0x2B2D31,
                "fields": [
                    {"name": "แบรนด์", "value": str(brand or "Unknown"), "inline": True},
                    {"name": "ลูกค้า", "value": safe_phone, "inline": True},
                    {"name": "คะแนนพนักงาน", "value": str(score or "-"), "inline": True},
                    {"name": "สถานะ", "value": "⏳ รอดำเนินการ", "inline": True},
                    {"name": "ผู้รับผิดชอบ", "value": "ยังไม่ระบุ", "inline": True},
                    {"name": "ความสำคัญ", "value": "🔴 สูง", "inline": True},
                    {"name": "รหัสเคส", "value": f"CLM-2026-{str(numeric_id).zfill(6)}", "inline": False},
                    {"name": "📌 ประเด็นปัญหา", "value": str(issue or "-"), "inline": False},
                    {"name": "📝 สรุปเนื้อหา", "value": str(summary or "-")[:1000], "inline": False},
                    {"name": "⚙️ การดำเนินการล่าสุด", "value": "รอรับงาน", "inline": False},
                ],
                "footer": {"text": "OMAZZ CALLING • Intelligence Dashboard Alert"},
            }
        ],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 3,
                        "label": "รับเคส",
                        "emoji": {"name": "🙋‍♂️"},
                        "custom_id": f"btn_claim_{numeric_id}",
                    },
                    {
                        "type": 2,
                        "style": 4,
                        "label": "ปิดเคส",
                        "emoji": {"name": "🔒"},
                        "custom_id": f"btn_close_{numeric_id}",
                    },
                ]
            }
        ]
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status in (200, 201)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        logger.error(f"HTTPError {e.code} sending to Discord: {err_msg}")
        return False
    except Exception as e:
        logger.error(f"Send Bot API Error: {e}")
        return False


async def send_interactive_case_alert(
    channel_id: Optional[int] = None,
    case_id: Optional[str] = None,
    record_id: Optional[Any] = None,
    brand: Optional[str] = None,
    customer_phone: Optional[str] = None,
    score: Optional[str] = None,
    issue: Optional[str] = None,
    summary: Optional[str] = None,
    **kwargs,
) -> bool:
    target_id_str = str(case_id or record_id or kwargs.get("id", "1"))
    target_channel_id = channel_id or DISCORD_CHANNEL_ID
    token = DISCORD_BOT_TOKEN

    safe_phone = str(customer_phone or kwargs.get("customer_phone", "-"))
    safe_brand = str(brand or kwargs.get("brand", "Unknown"))
    safe_score = str(score or kwargs.get("score", "-"))
    safe_issue = str(issue or kwargs.get("issue", "-"))
    safe_summary = str(summary or kwargs.get("summary", "-"))

    if token and target_channel_id:
        return await asyncio.to_thread(
            _send_ticket_card_bot_api,
            token=token,
            channel_id=int(target_channel_id),
            ref_id=target_id_str,
            brand=safe_brand,
            customer_phone=safe_phone,
            score=safe_score,
            issue=safe_issue,
            summary=safe_summary,
        )
    return False


class DiscordBotService:
    async def send_case_alert(self, case_data: dict):
        success = await send_interactive_case_alert(
            record_id=case_data.get("id"),
            case_id=case_data.get("id"),
            brand=case_data.get("brand"),
            customer_phone=case_data.get("customer_phone"),
            score=case_data.get("agent_score"),
            issue=case_data.get("issue"),
            summary=case_data.get("summary")
        )
        if not success:
            raise Exception("Discord API ปฏิเสธคำขอ")
        return {"success": True}


def run_discord_bot_background(token: Optional[str] = None):
    global _bot_loop
    active_token = (token or DISCORD_BOT_TOKEN).strip()
    if not active_token:
        return

    def _thread_target():
        global _bot_loop
        _bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_bot_loop)
        try:
            _bot_loop.run_until_complete(bot.start(active_token))
        except Exception as e:
            logger.error(f"❌ [Discord Bot Error]: {e}")
        finally:
            try:
                _bot_loop.close()
            except Exception:
                pass

    t = threading.Thread(target=_thread_target, daemon=True, name="DiscordBotWorker")
    t.start()