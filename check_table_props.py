from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("ไม่พบไฟล์ urgent_cases.html")
    exit()

text = html_path.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()

print("=== โครงสร้างของฟังก์ชัน renderPerformanceTable ===")
for idx, line in enumerate(lines):
    if "function renderPerformanceTable" in line:
        start = max(0, idx)
        end = min(len(lines), idx + 65)
        print("\n".join(lines[start:end]))
        break
