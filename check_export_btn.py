from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if html_path.exists():
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    # ค้นหาปุ่มส่งออกผลงาน
    matches = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>.*?ส่งออกผลงาน.*?</a>', text, re.DOTALL)
    if not matches:
        matches = re.findall(r'href="([^"]*export[^"]*)"', text)
    print("URL ของปุ่มส่งออกผลงานในหน้าเว็บ:", matches)
