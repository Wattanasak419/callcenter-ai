import asyncio
from backend.discord_bot_service import bot, send_interactive_case_alert, DISCORD_BOT_TOKEN

async def main():
    async with bot:
        await bot.login(DISCORD_BOT_TOKEN)
        
        # ส่งข้อความทดสอบที่มีปุ่ม
        await send_interactive_case_alert(
            record_id=1, 
            brand="Dunlopillo",
            customer_phone="0922743437",
            score="91/100",
            issue="ลูกค้าสอบถามสถานะสินค้า",
            summary="ลูกค้าโทรมาสอบถามความคืบหน้าเรื่องการจัดส่งที่นอน"
        )
        print("✅ ส่งการ์ดพร้อมปุ่มเข้า Discord สำเร็จแล้ว!")

if __name__ == "__main__":
    asyncio.run(main())