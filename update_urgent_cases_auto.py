from pathlib import Path

html_path = Path("backend/templates/urgent_cases.html")
if not html_path.exists():
    print("❌ ไม่พบไฟล์ backend/templates/urgent_cases.html")
    exit()

lines = html_path.read_text(encoding="utf-8").splitlines()

# 1. ค้นหาจุดเริ่มต้นของฟังก์ชัน exportAgentPerformanceCsv
start_idx = -1
for idx, line in enumerate(lines):
    if "function exportAgentPerformanceCsv" in line:
        start_idx = idx
        break

if start_idx == -1:
    print("❌ ไม่พบตำแหน่งฟังก์ชัน exportAgentPerformanceCsv ในไฟล์")
    exit()

# 2. ค้นหาจุดสิ้นสุดของฟังก์ชันโดยนับวงเล็บปีกกา { }
brace_count = 0
found_first_brace = False
end_idx = -1

for idx in range(start_idx, len(lines)):
    line = lines[idx]
    for ch in line:
        if ch == "{":
            brace_count += 1
            found_first_brace = True
        elif ch == "}":
            brace_count -= 1
            if found_first_brace and brace_count == 0:
                end_idx = idx
                break
    if found_first_brace and brace_count == 0:
        break

if end_idx == -1:
    print("❌ ไม่สามารถระบุขอบเขตฟังก์ชันเดิมได้")
    exit()

print(f"🔍 พบฟังก์ชันเดิมที่บรรทัด {start_idx + 1} ถึง {end_idx + 1} กำลังแทนที่ด้วยโค้ดแยกกลุ่ม VVIP...")

# 3. โค้ดฟังก์ชันใหม่ที่จะแทนที่ (แยกส่วน 2.1 VVIP และ 2.2 ทั่วไป พร้อมแจกแจงเคส)
replacement_code = """    function exportAgentPerformanceCsv() {
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
      const vvipCases = cases.filter(c => String(c.brand || "").toLowerCase().includes("omazz"));
      const normalCases = cases.filter(c => !String(c.brand || "").toLowerCase().includes("omazz"));
      const adminCareCount = cases.filter(c => Boolean(c.assigned_agent_code || c.handled_by || c.closed_by)).length;

      let topAgentDisplay = "-";
      if (statsList.length > 0) {
        const top = statsList[0];
        const topScore = top.validScoreCount ? (top.sumScore / top.validScoreCount).toFixed(1) : (top.avgScore || "-");
        topAgentDisplay = `${top.name || top.code} (${topScore} คะแนน)`;
      }

      let lines = [];
      // =========================================================
      // ส่วนที่ 1: สรุปภาพรวมแดชบอร์ด
      // =========================================================
      lines.push("=== ส่วนที่ 1: สรุปภาพรวมแดชบอร์ด (Dashboard Overview) ===");
      lines.push("หัวข้อ,จำนวน / รายละเอียด");
      lines.push(`"เคสต้องเข้าดูแลด่วนทั้งหมด","${urgentCount}"`);
      lines.push(`"ลูกค้า VVIP (แบรนด์ Omazz)","${vvipCases.length}"`);
      lines.push(`"ลูกค้าทั่วไป (แบรนด์ Lotus / Dunlopillo)","${normalCases.length}"`);
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

      const generateRows = (agentItems, targetCases, isVVIP) => {
        let rows = [];
        agentItems.forEach((item, idx) => {
          const agentCode = String(item.code || "").trim();
          const avgScore = item.validScoreCount ? (item.sumScore / item.validScoreCount).toFixed(1) : "—";
          const avgSat = item.validSatCount ? Math.round(item.sumSat / item.validSatCount) + "%" : "—";

          const matchedCases = targetCases.filter(c => {
            const cCode = String(c.assigned_agent_code || c.handled_by || c.agent_code || "").trim();
            return cCode === agentCode;
          });

          const closedCases = matchedCases.filter(c => {
            return (c.status === "done" || c.case_stage === "resolved" || Boolean(c.closed_by));
          });

          const closedListStr = closedCases.map(c => {
            const custName = `${c.firstname || ""} ${c.lastname || ""}`.trim() || c.customer_name || "ลูกค้า";
            const phone = c.customer_phone || "-";
            const brand = c.brand || (isVVIP ? "Omazz" : "Lotus");
            return `#${c.id} ${custName} (${phone}) [${brand}]`;
          }).join(" ; ") || "—";

          rows.push([
            idx + 1,
            item.name || "-",
            agentCode || "-",
            matchedCases.length,
            closedCases.length,
            avgScore,
            avgSat,
            closedListStr
          ]);
        });
        return rows;
      };

      const vvipAgents = statsList.filter(item => {
        return vvipCases.some(c => String(c.assigned_agent_code || c.handled_by || "").trim() === String(item.code || "").trim());
      });
      const normalAgents = statsList.filter(item => {
        return normalCases.some(c => String(c.assigned_agent_code || c.handled_by || "").trim() === String(item.code || "").trim());
      });

      // =========================================================
      // ส่วนที่ 2.1: กลุ่มลูกค้า VVIP (Omazz)
      // =========================================================
      lines.push("=== ส่วนที่ 2.1: ข้อมูลผลงานกลุ่มดูแลลูกค้า VVIP (แบรนด์ Omazz) ===");
      lines.push(headers.map(h => `"${h}"`).join(","));
      generateRows(vvipAgents, vvipCases, true).forEach(r => {
        lines.push(r.map(val => `"${String(val).replace(/"/g, '""')}"`).join(","));
      });
      lines.push("");

      // =========================================================
      // ส่วนที่ 2.2: กลุ่มลูกค้าทั่วไป (Lotus / Dunlopillo)
      // =========================================================
      lines.push("=== ส่วนที่ 2.2: ข้อมูลผลงานกลุ่มดูแลลูกค้าทั่วไป (แบรนด์ Lotus / Dunlopillo) ===");
      lines.push(headers.map(h => `"${h}"`).join(","));
      generateRows(normalAgents, normalCases, false).forEach(r => {
        lines.push(r.map(val => `"${String(val).replace(/"/g, '""')}"`).join(","));
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

# ทำการเปลี่ยนเฉพาะช่วงบรรทัดนั้น
new_lines = lines[:start_idx] + [replacement_code] + lines[end_idx + 1:]
html_path.write_text("\n".join(new_lines), encoding="utf-8")

print("🎉 สำเร็จ! แก้ไขและบันทึกลงไฟล์ urgent_cases.html เรียบร้อยแล้ว 100%")
