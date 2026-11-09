from pathlib import Path

# 1. ดูบรรทัดที่ 900-925 ใน urgent_cases.html
html_path = Path("backend/templates/urgent_cases.html")
if html_path.exists():
    lines = html_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    print("=== backend/templates/urgent_cases.html (บรรทัด 900-925) ===")
    for i in range(max(0, 900-1), min(len(lines), 925)):
        print(f"{i+1}: {lines[i]}")

# 2. ดูบรรทัดที่ 1600-1645 ใน backend/main.py
py_path = Path("backend/main.py")
if py_path.exists():
    lines = py_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    print("\n=== backend/main.py (บรรทัด 1600-1645) ===")
    for i in range(max(0, 1600-1), min(len(lines), 1645)):
        print(f"{i+1}: {lines[i]}")
