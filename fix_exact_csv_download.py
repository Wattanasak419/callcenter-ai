from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("ไม่พบไฟล์ backend/templates/urgent_cases.html")
    exit()

content = html_path.read_text(encoding="utf-8")

# ค้นหาตำแหน่งฟังก์ชันที่สร้างชื่อไฟล์ agent_performance_summary
pattern = r'agent_performance_summary'
matches = [m.start() for m in re.finditer(pattern, content)]

if not matches:
    print("ไม่พบคำว่า agent_performance_summary ใน urgent_cases.html")
    # ลองค้นหาในไฟล์ js ทั้งหมด
    for p in Path(".").rglob("*.js"):
        if "venv" in str(p): continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "agent_performance_summary" in txt:
            print(f"พบในไฟล์: {p}")
    exit()

print(f"พบจุดที่สร้างไฟล์ CSV ใน urgent_cases.html ทั้งหมด {len(matches)} จุด")

# สแกนหาฟังก์ชันที่ครอบจุดนี้อยู่
lines = content.splitlines()
func_start = -1
func_end = -1

for idx, line in enumerate(lines):
    if "agent_performance_summary" in line:
        # ย้อนหาจุดเริ่มต้น function
        for i in range(idx, max(0, idx - 80), -1):
            if "function" in lines[i]:
                func_start = i
                break
        # หาจุดสิ้นสุด function (ปีกกาปิด)
        for j in range(idx, min(len(lines), idx + 60)):
            if lines[j].strip() == "}":
                func_end = j
                break
        break

if func_start != -1 and func_end != -1:
    print(f"ขอบเขตฟังก์ชันเดิม: บรรทัด {func_start + 1} ถึง {func_end + 1}")
    print("\n--- โค้ดเดิมบางส่วน ---")
    print("\n".join(lines[func_start:func_start+15]))
    print("...")
    print("\n".join(lines[func_end-5:func_end+1]))

