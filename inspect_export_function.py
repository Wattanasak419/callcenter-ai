from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("ไม่พบไฟล์ urgent_cases.html")
    exit()

text = html_path.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()

print("=== ค้นหาโค้ดส่วน Export CSV ใน urgent_cases.html ===")
for idx, line in enumerate(lines):
    if "export" in line.lower() and ("csv" in line.lower() or "function" in line.lower()):
        start = max(0, idx - 2)
        end = min(len(lines), idx + 40)
        print(f"\n--- พบบริเวณบรรทัดที่ {idx+1} ---")
        print("\n".join(lines[start:end]))
        print("=" * 60)
