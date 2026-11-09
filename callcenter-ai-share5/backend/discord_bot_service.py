import os
import asyncio
import threading
import logging
from pathlib import Path
from typing import Optional, Any
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

import discord
from discord.ext import commands
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

intents = discord.Intents.default()
intents.message_content = False
bot = commands.Bot(command_prefix="!", intents=intents)


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
        selected_agent_code = self.values[0]
        if selected_agent_code == "none":
            await interaction.response.send_message("❌ ไม่สามารถเลือกได้เนื่องจากไม่มีข้อมูลพนักงาน", ephemeral=True)
            return

        db = SessionLocal()
        try:
            # Do not assign a different case if this Discord card has a stale or invalid ID.
            record = db.query(CallRecord).filter(CallRecord.id == self.record_id).first()
            if not record:
                await interaction.response.send_message(
                    f"❌ ไม่พบเคส #{self.record_id} ในระบบ กรุณาส่งเคสนี้เข้า Discord ใหม่",
                    ephemeral=True,
                )
                return

            agent = db.query(Agent).filter(Agent.agent_code == selected_agent_code).first()

            if not agent:
                await interaction.response.send_message("❌ ไม่พบข้อมูลพนักงานในระบบ", ephemeral=True)
                return

            staff_display = f"{agent.firstname} {agent.lastname}"
            if agent.nickname:
                staff_display += f" ({agent.nickname})"

            actual_record_id = record.id
            record.assigned_agent_code = agent.agent_code
            record.status = "in_progress"
            db.commit()

            # หาห้องปลายทาง "# รับเคสมาแล้ว"
            target_accepted_channel = None
            if DISCORD_ACCEPTED_CHANNEL_ID:
                target_accepted_channel = bot.get_channel(DISCORD_ACCEPTED_CHANNEL_ID)
                if not target_accepted_channel:
                    try:
                        target_accepted_channel = await bot.fetch_channel(DISCORD_ACCEPTED_CHANNEL_ID)
                    except Exception:
                        pass

            # หากไม่ได้ตั้ง ID ใน .env ให้ค้นหาจากชื่อห้องใน Server อัตโนมัติ
            if not target_accepted_channel and interaction.guild:
                target_accepted_channel = discord.utils.get(
                    interaction.guild.text_channels, name="รับเคสมาแล้ว"
                )

            # คัดลอก Embed เดิมมาปรับสถานะ
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

            # สร้างชุดปุ่มสำหรับการ์ดใหม่ในห้อง "รับเคสมาแล้ว"
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

            # 1. ส่งการ์ดใหม่เข้าห้อง "# รับเคสมาแล้ว"
            if target_accepted_channel:
                await target_accepted_channel.send(
                    content=f"📌 **[เคสติดตามงาน] มอบหมายให้: {staff_display} (กำลังดำเนินการ)**",
                    embed=new_embed,
                    view=accepted_view
                )

            # 2. อัปเดตข้อความเดิมในห้อง "# ทั่วไป" ให้รู้ว่าถูกย้ายไปแล้ว
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

            await interaction.response.send_message(
                f"🎉 เคส CLM-2026-{str(actual_record_id).zfill(6)} มอบหมายให้คุณ **{staff_display}** เรียบร้อย และย้ายไปที่ห้อง **#รับเคสมาแล้ว** แล้วครับ",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error assigning agent: {e}")
            await interaction.response.send_message(f"เกิดข้อผิดพลาด: {e}", ephemeral=True)
        finally:
            db.close()


class AgentSelectView(View):
    def __init__(self, record_id: int):
        super().__init__(timeout=120)
        self.add_item(AgentSelectDropdown(record_id=record_id))


# ==========================================
# 🛰️ BOT EVENTS
# ==========================================
@bot.event
async def on_ready():
    logger.info(f"🤖 [Discord Bot] ออนไลน์เรียบร้อยแล้วในชื่อ {bot.user}")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        cid = interaction.data.get("custom_id", "")

        # 🟢 เมื่อกดปุ่ม "รับเคส"
        if cid.startswith("btn_claim_"):
            try:
                record_id = int(cid.replace("btn_claim_", ""))
            except ValueError:
                record_id = 1

            view = AgentSelectView(record_id=record_id)
            await interaction.response.send_message(
                "📋 **กรุณาเลือกพนักงานเพื่อรับผิดชอบเคสนี้:**",
                view=view,
                ephemeral=True
            )

        # 🔴 เมื่อกดปุ่ม "ปิดเคส"
        elif cid.startswith("btn_close_"):
            try:
                record_id = int(cid.replace("btn_close_", ""))
            except ValueError:
                record_id = 1

            db = SessionLocal()
            try:
                record = db.query(CallRecord).filter(CallRecord.id == record_id).first()
                if record:
                    record.status = "done"
                    db.commit()

                if interaction.message and interaction.message.embeds:
                    embed = interaction.message.embeds[0]
                    for i, field in enumerate(embed.fields):
                        if field.name == "สถานะ":
                            embed.set_field_at(i, name="สถานะ", value="✅ ปิดเคสแล้ว", inline=True)
                        elif field.name == "⚙️ การดำเนินการล่าสุด":
                            embed.set_field_at(i, name="⚙️ การดำเนินการล่าสุด", value=f"ปิดเคสโดย {interaction.user.display_name}", inline=False)

                    closed_view = View(timeout=None)
                    closed_view.add_item(
                        Button(label="ปิดเคสแล้ว", style=discord.ButtonStyle.secondary, disabled=True, emoji="🔒")
                    )

                    await interaction.response.edit_message(
                        content=f"🏁 **[เคสติดตามงาน] ปิดเคสเรียบร้อยแล้ว โดย {interaction.user.mention}**",
                        embed=embed,
                        view=closed_view
                    )
                    await interaction.followup.send(f"🔒 ปิดเคส ID: #{record_id} เรียบร้อยแล้ว", ephemeral=False)
            except Exception as e:
                logger.error(f"Close case error: {e}")
                await interaction.response.send_message(f"เกิดข้อผิดพลาด: {e}", ephemeral=True)
            finally:
                db.close()


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
        if numeric_id < 1:
            return False
    except (TypeError, ValueError):
        return False

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
    try:
        target_id_str = str(int(case_id or record_id or kwargs.get("id")))
        if int(target_id_str) < 1:
            return False
    except (TypeError, ValueError):
        return False
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
    active_token = (token or DISCORD_BOT_TOKEN).strip()
    if not active_token:
        return

    def _thread_target():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(bot.start(active_token))
        except Exception as e:
            logger.error(f"❌ [Discord Bot Error]: {e}")
        finally:
            try:
                new_loop.close()
            except Exception:
                pass

    t = threading.Thread(target=_thread_target, daemon=True, name="DiscordBotWorker")
    t.start()
