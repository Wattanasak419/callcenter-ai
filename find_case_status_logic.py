import os
from pathlib import Path

target_terms = ["ประวัติเคสที่ดูแล", "ปิดเคสสำเร็จ", "กำลังดำเนินการ"]

for p in Path(".").rglob("*"):
    if p.name.startswith("find_") or p.name.startswith("check_") or "venv" in str(p) or ".git" in str(p):
        continue
    if p.suffix in [".html", ".py", ".js"]:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for term in target_terms:
                if term in txt:
                    print(f"\n>>> พบคำว่า '{term}' ในไฟล์: {p}")
                    for idx, line in enumerate(txt.splitlines()):
                        if term in line:
                            print(f"Line {idx+1}: {line.strip()}")
        except Exception:
            pass
