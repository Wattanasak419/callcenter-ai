from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("❌ ไม่พบไฟล์ backend/templates/urgent_cases.html")
    exit()

content = html_path.read_text(encoding="utf-8")

# ฟังก์ชัน JavaScript ที่เขียนแบบ Clean Syntax ปราศจากเครื่องหมายหลุด
clean_export_func = '''    function exportAgentPerformanceCsv() {
      if (!isManagerOrSupervisor()) {
        alert("ขออภัย: เฉพาะหัวหน้างานหรือผู้จัดการเท่านั้นที่สามารถส่งออกรายงานนี้ได้");
        return;
      }

      const statsList = renderPerformanceTable(currentLoadedCases);
      if (!statsList || statsList.length === 0) {
        alert("ไม่มีข้อมูลสถิติพนักงานสำหรับส่งออก");
        return;
      }

      // 1. ดึงสรุปภาพรวมจาก Dashboard Cards
      const urgentVal = document.getElementById("urgentCasesCount")?.innerText?.trim() 
                     || document.querySelector(".summary-card:nth-child(1) .card-val")?.innerText?.trim() || "0";
      const vvipVal = document.getElementById("vvipCount")?.innerText?.trim() 
                   || document.querySelector(".summary-card:nth-child(2) .card-val")?.innerText?.trim() || "0";
      const adminVal = document.getElementById("adminCareCount")?.innerText?.trim() 
                    || document.querySelector(".summary-card:nth-child(3) .card-val")?.innerText?.trim() || "0";
      const topAgentVal = document.getElementById("topAgentName")?.innerText?.trim() 
                       || document.querySelector(".summary-card:nth-child(4) .card-val")?.innerText?.trim() || "-";

      let lines = [];
      lines.push("=== ส่วนที่ 1: สรุปภาพรวมแดชบอร์ด (Dashboard Overview) ===");
      lines.push("หัวข้อ,จำนวน / รายละเอียด");
      lines.push(`"เคสต้องเข้าดูแลด่วน","${urgentVal}"`);
      lines.push(`"ลูกค้า VVIP","${vvipVal}"`);
      lines.push(`"เคสที่กำลังมีแอดมินประกบดูแล","${adminVal}"`);
      lines.push(`"ท็อปสกอร์พนักงานประจำรอบ","${topAgentVal}"`);
      lines.push("");

      // 2. สรุปผลงานพนักงานและเคสที่ปิดสำเร็จ
      lines.push("=== ส่วนที่ 2: ข้อมูลผลงานพนักงานและการปิดจ็อบรายบุคคล ===");
      const headers = [
        "อันดับ",
        "ชื่อพนักงาน",
        "รหัสพนักงาน",
        "เคสที่ได้รับมอบหมาย",
        "เคสที่ปิดสำเร็จ",
        "คะแนนบริการเฉลี่ย (เต็ม 100)",
        "ความพึงพอใจลูกค้าเฉลี่ย (%)",
        "รายชื่อลูกค้าและหมายเลขเคสที่ปิดสำเร็จ"
      ];
      lines.push(headers.map(h => `"${h}"`).join(","));

      statsList.forEach((item, idx) => {
        const avgScore = item.validScoreCount ? (item.sumScore / item.validScoreCount).toFixed(1) : "0";
        const avgSat = item.validSatCount ? Math.round(item.sumSat / item.validSatCount) : "0";

        // กรองเคสที่ปิดสำเร็จของพนักงานแต่ละคน
        const closedCases = (currentLoadedCases || []).filter(c => {
          const isAgentMatch = (c.assigned_agent_code === item.agent_code || c.agent_code === item.agent_code || c.handled_by === item.agent_code);
          const isClosed = (c.status === "done" || c.case_stage === "resolved" || Boolean(c.closed_by));
          return isAgentMatch && isClosed;
        });

        const closedListStr = closedCases.map(c => {
          const cName = `${c.firstname || ""} ${c.lastname || ""}`.trim() || c.customer_name || "ลูกค้า";
          const phone = c.customer_phone || "-";
          const brand = c.brand || "Lotus";
          return `#${c.id} ${cName} (${phone}) [${brand}]`;
        }).join(" ; ") || "—";

        const row = [
          idx + 1,
          item.name || "-",
          item.agent_code || "-",
          item.totalCases || 0,
          item.resolvedCases || closedCases.length || 0,
          avgScore,
          `${avgSat}%`,
          closedListStr
        ];
        lines.push(row.map(val => `"${String(val).replace(/"/g, '""')}"`).join(","));
      });

      const csvData = "\\ufeff" + lines.join("\\r\\n");
      const blob = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
      const dlUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = dlUrl;
      a.download = `agent_performance_summary_${new Date().toISOString().slice(0,10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(dlUrl);
    }'''

# แทนที่ฟังก์ชัน exportAgentPerformanceCsv เดิมแบบสะอาด
pattern = r'function\s+exportAgentPerformanceCsv\s*\(\)\s*\{[\s\S]*?URL\.revokeObjectURL\([^\)]*\);\s*\}'
if re.search(pattern, content):
    content = re.sub(pattern, lambda m: clean_export_func, content, count=1)
    html_path.write_text(content, encoding="utf-8")
    print("✅ กู้คืนและแก้ไขโค้ด JavaScript ใน urgent_cases.html ให้สะอาดสมบูรณ์เรียบร้อยแล้ว!")
else:
    print("⚠️ ไม่พบตำแหน่งฟังก์ชัน")
