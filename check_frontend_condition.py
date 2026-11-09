import os, re
from pathlib import Path

# ค้นหาคำว่า "กำลังดำเนินการ" หรือ "ปิดเคสสำเร็จ" ในโฟลเดอร์โปรเจกต์
keywords = ["กำลังดำเนินการ", "ปิดเคสสำเร็จ", "ปิดเคสสำเร็จแล้ว", "closed", "resolved"]
found_files = []

for ext in ["*.html", "*.js", "*.py"]:
    for p in Path(".").rglob(ext):
        if "venv" in str(p) or ".git" in str(p):
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            for kw in ["กำลังดำเนินการ", "ปิดเคสสำเร็จแล้ว"]:
                if kw in content:
                    found_files.append((p, kw))
        except Exception:
            pass

print("=== ตำแหน่งที่พบการแสดงผลสถานะในโค้ด ===")
for path, kw in set(found_files):
    print(f"ไฟล์: {path} (พบคำว่า: {kw})")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines):
        if kw in line:
            start = max(0, idx - 4)
            end = min(len(lines), idx + 5)
            print(f"--- บรรทัดที่ {idx+1} ---")
            print("\n".join(lines[start:end]))
            print("-" * 40)
