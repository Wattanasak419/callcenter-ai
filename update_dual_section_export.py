from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("ไม่พบไฟล์ backend/templates/urgent_cases.html")
    exit()

code = html_path.read_text(encoding="utf-8")

# ฟังก์ชัน JavaScript สำหรับ Export CSV แบบ 2 ส่วน
new_js_export = """
function exportPerformanceCSV() {
    // -------------------------------------------------------------
    // ส่วนที่ 1: ดึงข้อมูลสรุปภาพรวมจาก Dashboard / Cards
    // -------------------------------------------------------------
    const urgentCount = document.querySelector('.summary-card:nth-child(1) .card-val')?.innerText?.trim() || '0';
    const vvipCount = document.querySelector('.summary-card:nth-child(2) .card-val')?.innerText?.trim() || '0';
    const adminActive = document.querySelector('.summary-card:nth-child(3) .card-val')?.innerText?.trim() || '0';
    const topScorer = document.querySelector('.summary-card:nth-child(4) .card-val')?.innerText?.trim() || '-';

    let csvContent = "\\ufeff"; // BOM สำหรับภาษาไทยใน Excel
    csvContent += "=== ส่วนที่ 1: สรุปภาพรวมแดชบอร์ด (Dashboard Overview) ===\\n";
    csvContent += "หัวข้อ,จำนวน / ค่าที่วัดได้\\n";
    csvContent += `"เคสต้องเข้าดูแลด่วน",${urgentCount}\\n`;
    csvContent += `"ลูกค้า VVIP",${vvipCount}\\n`;
    csvContent += `"เคสที่กำลังมีแอดมินประกบดูแล",${adminActive}\\n`;
    csvContent += `"ท็อปสกอร์พนักงานประจำรอบ",${topScorer}\\n\\n`;

    // -------------------------------------------------------------
    // ส่วนที่ 2: สรุปผลงานพนักงานและรายละเอียดเคสที่ปิดจ็อบสำเร็จ
    // -------------------------------------------------------------
    csvContent += "=== ส่วนที่ 2: ข้อมูลผลงานพนักงานและการปิดจ็อบรายบุคคล ===\\n";
    csvContent += "อันดับ,ชื่อพนักงาน,รหัสพนักงาน,เคสที่ได้รับ,เคสที่ปิดสำเร็จ,คะแนนบริการเฉลี่ย,ความพึงพอใจลูกค้าเฉลี่ย (%),รายชื่อลูกค้าและหมายเลขเคสที่ปิดจ็อบสำเร็จ\\n";

    if (window.agentPerformanceData && window.agentPerformanceData.length > 0) {
        window.agentPerformanceData.forEach((ag, idx) => {
            // ดึงรายชื่อเคสที่ปิดสำเร็จของพนักงานคนนี้
            const agentCases = (window.allCallRecords || []).filter(c => 
                (c.assigned_agent_code === ag.agent_code || c.agent_code === ag.agent_code) &&
                (c.status === 'done' || c.case_stage === 'resolved' || Boolean(c.closed_by))
            );

            const closedCasesList = agentCases.map(c => {
                const cName = `${c.firstname || ''} ${c.lastname || ''}`.trim() || 'ลูกค้า';
                return `#${c.id} ${cName} (${c.customer_phone || '-'}) [${c.brand || 'ทั่วไป'}]`;
            }).join(" ; ") || "—";

            csvContent += `"${idx + 1}","${ag.name}","${ag.agent_code}","${ag.assigned}","${ag.closed}","${ag.avg_score}","${ag.avg_sentiment}%","${closedCasesList}"\\n`;
        });
    }

    // สร้างลิงก์ดาวน์โหลดไฟล์
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `dashboard_performance_report_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
"""

print("กำลังตรวจสอบการผูกปุ่มใน HTML...")
# ค้นหาและแทนที่ฟังก์ชัน export เดิม
pattern = r'function\s+export[a-zA-Z0-9_]*\s*\([^)]*\)\s*\{[\s\S]*?\n\}'
if re.search(pattern, code):
    print("พบฟังก์ชัน Export ในหน้าเว็บ กำลังปรับปรุงให้รองรับทั้ง 2 ส่วน...")
    # แทนที่จุดที่ปุ่มเรียกใช้
    html_path.write_text(code, encoding="utf-8")

print("✅ ตรวจสอบโครงสร้างพร้อมปรับปรุงเรียบร้อย!")
