from pathlib import Path
import re

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("❌ ไม่พบไฟล์ backend/templates/urgent_cases.html")
    exit()

content = html_path.read_text(encoding="utf-8")

# ฟังก์ชัน JavaScript ที่คำนวณสรุปแดชบอร์ดส่วนที่ 1 จาก Data ตรงๆ
clean_export_func = """    function exportAgentPerformanceCsv() {
      if (!isManagerOrSupervisor()) {
        alert("ขออภัย: เฉพาะหัวหน้างานหรือผู้จัดการเท่านั้นที่สามารถส่งออกรายงานนี้ได้");
        return;
      }

      const statsList = renderPerformanceTable(currentLoadedCases);
      if (!statsList || statsList.length === 0) {
        alert("ไม่มีข้อมูลสถิติพนักงานสำหรับส่งออก");
        return;
      }

      // --- ส่วนที่ 1: คำนวณสรุปภาพรวมจากข้อมูลจริงในระบบ (Real Data Calculation) ---
      const cases = currentLoadedCases || [];
      
      // 1. เคสต้องเข้าดูแลด่วนทั้งหมด
      const urgentCount = cases.length;

      // 2. ลูกค้า VVIP (Omazz หรือ vvip tier)
      const vvipCount = cases.filter(c => {
        const brand = String(c.brand || "").toLowerCase();
        const tier = String(c.customer_tier || c.tier || "").toLowerCase();
        return brand.includes("omazz") || tier.includes("vvip");
      }).length;

      // 3. กำลังมีแอดมินประกบดูแล (เคสที่ได้รับมอบหมายแล้ว)
      const adminCareCount = cases.filter(c => {
        return Boolean(c.assigned_agent_code || c.handled_by || c.closed_by);
      }).length;

      // 4. ท็อปสกอร์พนักงานประจำรอบ (คนแรกในตารางที่เรียงตามคะแนน)
      let topAgentDisplay = "-";
      if (statsList.length > 0) {
        const top = statsList[0];
        const topScore = top.validScoreCount ? (top.sumScore / top.validScoreCount).toFixed(1) : (top.avgScore || "-");
        topAgentDisplay = `${top.name || top.code} (${topScore} คะแนน)`;
      }

      let lines = [];
      lines.push("=== ส่วนที่ 1: สรุปภาพรวมแดชบอร์ด (Dashboard Overview) ===");
      lines.push("หัวข้อ,จำนวน / รายละเอียด");
      lines.push(`"เคสต้องเข้าดูแลด่วน","${urgentCount}"`);
      lines.push(`"ลูกค้า VVIP","${vvipCount}"`);
      lines.push(`"เคสที่กำลังมีแอดมินประกบดูแล","${adminCareCount}"`);
      lines.push(`"ท็อปสกอร์พนักงานประจำรอบ","${topAgentDisplay}"`);
      lines.push("");

      // --- ส่วนที่ 2: ข้อมูลผลงานพนักงานและการปิดจ็อบรายบุคคล ---
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
        const agentCode = String(item.code || "").trim();
        const avgScore = item.validScoreCount ? (item.sumScore / item.validScoreCount).toFixed(1) : "—";
        const avgSat = item.validSatCount ? Math.round(item.sumSat / item.validSatCount) + "%" : "—";

        // กรองเคสที่ปิดสำเร็จของพนักงานรหัสนี้
        const closedCases = cases.filter(c => {
          const cCode = String(c.assigned_agent_code || c.handled_by || c.agent_code || "").trim();
          const isClosed = (c.status === "done" || c.case_stage === "resolved" || Boolean(c.closed_by));
          return cCode === agentCode && isClosed;
        });

        const closedListStr = closedCases.map(c => {
          const custName = `${c.firstname || ""} ${c.lastname || ""}`.trim() || c.customer_name || "ลูกค้า";
          const phone = c.customer_phone || "-";
          const brand = c.brand || "Lotus";
          return `#${c.id} ${custName} (${phone}) [${brand}]`;
        }).join(" ; ") || "—";

        const row = [
          idx + 1,
          item.name || "-",
          agentCode || "-",
          item.totalAssigned || 0,
          item.closedCases || closedCases.length || 0,
          avgScore,
          avgSat,
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
    }"""

pattern = r'function\s+exportAgentPerformanceCsv\s*\(\)\s*\{[\s\S]*?URL\.revokeObjectURL\([^\)]*\);\s*\}'
if re.search(pattern, content):
    content = re.sub(pattern, lambda m: clean_export_func, content, count=1)
    html_path.write_text(content, encoding="utf-8")
    print("✅ ปรับแก้ให้คำนวณยอด VVIP และสถิติ Dashboard โดยตรงเรียบร้อยแล้ว!")
else:
    print("⚠️ ไม่พบตำแหน่งฟังก์ชัน")
