from pathlib import Path

html_path = Path("backend/templates/urgent_cases.html")
if html_path.exists():
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if any(kw in line for kw in ["ลูกค้า VVIP", "เคสต้องเข้าดูแลด่วน", "กำลังมีแอดมินประกบ", "ท็อปสกอร์พนักงาน"]):
            start = max(0, idx - 3)
            end = min(len(lines), idx + 8)
            print(f"=== พบบริเวณบรรทัดที่ {idx+1} ===")
            print("\n".join(lines[start:end]))
            print("-" * 50)
