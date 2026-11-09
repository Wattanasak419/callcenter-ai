from pathlib import Path
import re

main_path = Path("backend/main.py")
if not main_path.exists():
    print("ไม่พบไฟล์ backend/main.py")
    exit()

code = main_path.read_text(encoding="utf-8")

# ค้นหาและปรับฟังก์ชัน export_urgent_performance ให้ดึงเคสที่ปิดสำเร็จจาก status = "done" หรือ case_stage = "resolved"
new_export_logic = """@app.get("/api/urgent-cases/export-performance")
def export_urgent_performance(db: Session = Depends(get_db)):
    \"\"\"Export สรุปผลงานรายบุคคล พร้อมรายชื่อลูกค้าที่ปิดเคสสำเร็จ\"\"\"
    import io, csv
    from fastapi.responses import Response

    output = io.StringIO()
    writer = csv.writer(output)

    # เขียน Header 8 คอลัมน์ชัดเจน
    writer.writerow([
        "อันดับ",
        "ชื่อพนักงาน",
        "รหัสพนักงาน",
        "เคสที่ได้รับ",
        "เคสที่ปิดสำเร็จ",
        "คะแนนบริการเฉลี่ย",
        "ความพึงพอใจลูกค้าเฉลี่ย (%)",
        "รายชื่อลูกค้าที่ปิดเคสสำเร็จ"
    ])

    agents = db.query(Agent).filter(Agent.is_active == True).all()
    summary = []

    for agent in agents:
        assigned = db.query(CallRecord).filter(
            CallRecord.assigned_agent_code == agent.agent_code,
            CallRecord.is_active == True
        ).all()

        # เคสที่ปิดสำเร็จ: เช็คทั้ง status = 'done', 'closed' หรือ case_stage = 'resolved' หรือมี closed_by
        closed = [
            r for r in assigned 
            if getattr(r, "status", "") in ["done", "closed", "ปิดเคสสำเร็จ"]
            or getattr(r, "case_stage", "") in ["resolved", "closed"]
            or getattr(r, "closed_by", None) is not None
        ]

        closed_names = []
        for r in closed:
            fn = getattr(r, "firstname", "") or ""
            ln = getattr(r, "lastname", "") or ""
            name = f"{fn} {ln}".strip() or getattr(r, "brand", "") or "ลูกค้า"
            phone = getattr(r, "customer_phone", "") or "-"
            brand = getattr(r, "brand", "") or "ทั่วไป"
            closed_names.append(f"#{r.id} {name} ({phone}) [{brand}]")

        closed_str = " ; ".join(closed_names) if closed_names else "—"

        scores = [float(r.agent_score or 0) for r in assigned if getattr(r, "agent_score", None)]
        sentiments = [float(r.sentiment_score or 0) for r in assigned if getattr(r, "sentiment_score", None)]

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        avg_sentiment = round(sum(sentiments) / len(sentiments)) if sentiments else 0

        summary.append({
            "name": f"{getattr(agent, 'firstname', '') or ''} {getattr(agent, 'lastname', '') or ''}".strip() or agent.agent_code,
            "code": agent.agent_code,
            "assigned": len(assigned),
            "closed": len(closed),
            "score": avg_score,
            "sentiment": avg_sentiment,
            "closed_str": closed_str
        })

    # เรียงลำดับตามเคสที่ปิดสำเร็จและคะแนน
    summary.sort(key=lambda x: (x["closed"], x["score"]), reverse=True)

    for idx, item in enumerate(summary, 1):
        writer.writerow([
            idx,
            item["name"],
            item["code"],
            item["assigned"],
            item["closed"],
            item["score"],
            item["sentiment"],
            item["closed_str"]
        ])

    csv_data = "\ufeff" + output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=agent_performance_closed_cases.csv"}
    )
"""

# ทำการแทนที่ฟังก์ชันเดิม
pattern = r'@app\.get\("/api/urgent-cases/export-performance"\)[\s\S]*?(?=\n@app|\nif __name__|\Z)'
if re.search(pattern, code):
    updated_code = re.sub(pattern, new_export_logic, code)
    main_path.write_text(updated_code, encoding="utf-8")
    print("✅ อัปเดตฟังก์ชัน export_urgent_performance ใน backend/main.py เรียบร้อยแล้ว!")
else:
    print("⚠️ ไม่พบตำแหน่งฟังก์ชันเดิม กรุณาตรวจสอบชื่อ endpoint")
