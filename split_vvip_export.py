from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("❌ ไม่พบไฟล์ backend/templates/urgent_cases.html")
    exit()

content = html_path.read_text(encoding="utf-8")

new_func = """    function exportAgentPerformanceCsv() {
      if (!isManagerOrSupervisor()) {
        alert("ขออภัย: เฉพาะหัวหน้างานหรือผู้จัดการเท่านั้นที่สามารถส่งออกรายงานนี้ได้");
        return;
      }

      const statsList = renderPerformanceTable(currentLoadedCases);
      if (!statsList || statsList.length === 0) {
        alert("ไม่มีข้อมูลสถิติพนักงานสำหรับส่งออก");
        return;
      }

      const cases = currentLoadedCases || [];
      const urgentCount = cases.length;
      const vvipCount = cases.filter(c => String(c.brand || "").toLowerCase().includes("omazz")).length;
      const adminCareCount = cases.filter(c => Boolean(c.assigned_agent_code || c.handled_by || c.closed_by)).length;

      let topAgentDisplay = "-";
      if (statsList.length > 0) {
        const top = statsList[0];
        const topScore = top.validScoreCount ? (top.sumScore / top.validScoreCount).toFixed(1) : (top.avgScore || "-");
        topAgentDisplay = `${top.name || top.code} (${topScore} คะแนน)`;
      }

      let lines = [];
      lines.push("=== ส่วนที่ 1: สรุปภาพรวมแดชบอร์ด (Dashboard Overview) ===");
      lines.push("หัวข้อ,จำนวน / รายละเอียด");
      lines.push(`"เคสต้องเข้าดูแลด่วนทั้งหมด","${urgentCount}"`);
      lines.push(`"ลูกค้า VVIP (Omazz)","${vvipCount}"`);
      lines.push(`"ลูกค้าทั่วไป (Lotus / Dunlopillo)","${urgentCount - vvipCount}"`);
      lines.push(`"เคสที่กำลังมีแอดมินประกบดูแล","${adminCareCount}"`);
      lines.push(`"ท็อปสกอร์พนักงานประจำรอบ","${topAgentDisplay}"`);
      lines.push("");

      const headers = [
        "อันดับ",
        "ชื่อพนักงาน",
        "รหัสพนักงาน",
        "เคสที่ได้รับมอบหมาย",
        "เคสที่ปิดสำเร็จ",
        "คะแนนบริการเฉลี่ย",
        "ความพึงพอใจลูกค้าเฉลี่ย",
        "รายชื่อลูกค้าและหมายเลขเคสที่ปิดสำเร็จ"
      ];

      // ฟังก์ชันช่วยจัดรูปแบบข้อมูลแต่ละแถว
      const buildRows = (agentsSubset, isVVIPGroup) => {
        let rows = [];
        agentsSubset.forEach((item, idx) => {
          const agentCode = String(item.code || "").trim();
          const avgScore = item.validScoreCount ? (item.sumScore / item.validScoreCount).toFixed(1) : "—";
          const avgSat = item.validSatCount ? Math.round(item.sumSat / item.validSatCount) + "%" : "—";

          // กรองเคสตามกลุ่ม VVIP หรือ ลูกค้าทั่วไป
          const closedCases = cases.filter(c => {
            const cCode = String(c.assigned_agent_code || c.handled_by || c.agent_code || "").trim();
            const isOmazz = String(c.brand || "").toLowerCase().includes("omazz");
            const groupMatch = isVVIPGroup ? isOmazz : !isOmazz;
            const isClosed = (c.status === "done" || c.case_stage === "resolved" || Boolean(c.closed_by));
            return cCode === agentCode && groupMatch && isClosed;
          });

          const closedListStr = closedCases.map(c => {
            const custName = `${c.firstname || ""} ${c.lastname || ""}`.trim() || c.customer_name || "ลูกค้า";
            const phone = c.customer_phone || "-";
            const brand = c.brand || (isVVIPGroup ? "Omazz" : "Lotus");
            return `#${c.id} ${custName} (${phone}) [${brand}]`;
          }).join(" ; ") || "—";

          rows.push([
            idx + 1,
            item.name || "-",
            agentCode || "-",
            item.totalAssigned || 0,
            item.closedCases || closedCases.length || 0,
            avgScore,
            avgSat,
            closedListStr
          ]);
        });
        return rows;
      };

      // แยกพนักงานออกเป็น 2 กลุ่ม (VVIP ดูแล Omazz / ทั่วไป ดูแล Lotus & Dunlopillo)
      const vvipAgents = statsList.filter(item => {
        const agentCases = cases.filter(c => String(c.assigned_agent_code || c.handled_by || "").trim() === String(item.code || "").trim());
        return agentCases.some(c => String(c.brand || "").toLowerCase().includes("omazz"));
      });

      const normalAgents = statsList.filter(item => !vvipAgents.includes(item));

      // ------------------------------------------------------------------
      // ส่วนที่ 2.1: กลุ่มดูแลลูกค้า VVIP (Omazz)
      // ------------------------------------------------------------------
      lines.push("=== ส่วนที่ 2.1: ข้อมูลผลงานกลุ่มดูแลลูกค้า VVIP (แบรนด์ Omazz) ===");
      lines.push(headers.map(h => `"${h}"`).join(","));
      const vvipRows = buildRows(vvipAgents, true);
      vvipRows.forEach(r => lines.push(r.map(val => `"${String(val).replace(/"/g, '""')}"`).join(",")));
      lines.push("");

      // ------------------------------------------------------------------
      // ส่วนที่ 2.2: กลุ่มดูแลลูกค้าทั่วไป (Lotus / Dunlopillo)
      // ------------------------------------------------------------------
      lines.push("=== ส่วนที่ 2.2: ข้อมูลผลงานกลุ่มดูแลลูกค้าทั่วไป (แบรนด์ Lotus / Dunlopillo) ===");
      lines.push(headers.map(h => `"${h}"`).join(","));
      const normalRows = buildRows(normalAgents, false);
      normalRows.forEach(r => lines.push(r.map(val => `"${String(val).replace(/"/g, '""')}"`).join(",")));

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
    }"""

pattern = r'function\s+exportAgentPerformanceCsv\s*\(\)\s*\{[\s\S]*?URL\.revokeObjectURL\([^\)]*\);\s*\}'
if re.search(pattern, content):
    content = re.sub(pattern, lambda m: new_func, content, count=1)
    html_path.write_text(content, encoding="utf-8")
    print("✅ อัปเดตฟังก์ชันแยกกลุ่ม VVIP และ ลูกค้าทั่วไปใน urgent_cases.html สำเร็จแล้ว!")
else:
    print("⚠️ ไม่พบตำแหน่งฟังก์ชัน")
