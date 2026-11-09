from pathlib import Path

py_path = Path("backend/main.py")
if py_path.exists():
    lines = py_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    print("=== backend/main.py (บรรทัด 1645-1670) ===")
    for i in range(1644, min(len(lines), 1670)):
        print(f"{i+1}: {lines[i]}")
