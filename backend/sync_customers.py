import os
import sys
import random
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# กำหนดพาธให้ชี้ไปที่ callcenter.db ในโฟลเดอร์หลัก
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "callcenter.db"

if not DB_PATH.exists():
    DB_PATH = Path(__file__).resolve().parent / "callcenter.db"

FIRSTNAMES = [
    'กิตติศักดิ์', 'วิภาดา', 'ธนพล', 'นภัสสร', 'ศิริพร',
    'ชลธิชา', 'ปิยะพงษ์', 'อัญชลี', 'วรวุฒิ', 'กานดา',
    'ณัฐวุฒิ', 'พัชราภา', 'สุทธิพงษ์', 'รัตนพร', 'ธีรภัทร',
    'มณีรัตน์', 'ชยานันต์', 'เบญจมาศ', 'ภานุพงศ์', 'อรวรรณ'
]

LASTNAMES = [
    'สมโลก', 'รัตนโชติ', 'เจริญสุข', 'วงศ์สวัสดิ์', 'สุขเจริญ',
    'ศรีสุข', 'บูรณพงศ์', 'พิทักษ์ธรรม', 'จันทรา', 'ตั้งเจริญ',
    'วัฒนพานิช', 'รุ่งเรือง', 'ประสิทธิ์โชค', 'มงคลสวัสดิ์', 'เลิศวิจิตร',
    'สุวรรณโรจน์', 'เกียรติไพบูลย์', 'ทรัพย์เจริญ', 'ทวีวัฒนา', 'ชินบุตร'
]

# 🗺️ รายการที่อยู่ต่างจังหวัดครอบคลุมทุกภาค
ADDRESSES = [
    # ภาคเหนือ
    "124/5 หมู่ 2 ถนนห้วยแก้ว ตำบลสุเทพ อำเภอเมืองเชียงใหม่ เชียงใหม่ 50200",
    "88/3 หมู่ 7 ถนนพหลโยธิน ตำบลเวียงพางคำ อำเภอแม่สาย เชียงราย 57130",
    "45/1 ถนนสิงหวัฒน์ ตำบลในเมือง อำเภอเมืองพิษณุโลก พิษณุโลก 65000",
    "9/12 หมู่ 4 ถนนลำปาง-เชียงใหม่ ตำบลปงแสนทอง อำเภอเมืองลำปาง ลำปาง 52100",
    "201/8 หมู่ 3 ตำบลในเวียง อำเภอเมืองน่าน น่าน 55000",

    # ภาคตะวันออกเฉียงเหนือ
    "77/2 หมู่ 6 ถนนมิตรภาพ ตำบลในเมือง อำเภอเมืองขอนแก่น ขอนแก่น 40000",
    "512/10 ถนนสุรนารายณ์ ตำบลในเมือง อำเภอเมืองนครราชสีมา นครราชสีมา 30000",
    "33/4 หมู่ 1 ถนนชยางกูร ตำบลในเมือง อำเภอเมืองอุบลราชธานี อุบลราชธานี 34000",
    "168/9 ถนนนิตโย ตำบลหมากแข้ง อำเภอเมืองอุดรธานี อุดรธานี 41000",
    "85/11 หมู่ 8 ถนนบุรีรัมย์-นางรอง ตำบลอิสาณ อำเภอเมืองบุรีรัมย์ บุรีรัมย์ 31000",

    # ภาคใต้
    "99/4 หมู่ 5 ถนนกาญจนวณิชย์ ตำบลคอหงส์ อำเภอหาดใหญ่ สงขลา 90110",
    "14/2 ถนนเทพกระษัตรี ตำบลตลาดใหญ่ อำเภอเมืองภูเก็ต ภูเก็ต 83000",
    "205/6 หมู่ 2 ถนนศรีวิชัย ตำบลมะขามเตี้ย อำเภอเมืองสุราษฎร์ธานี สุราษฎร์ธานี 84000",
    "42/8 ถนนเพชรเกษม ตำบลปากน้ำ อำเภอเมืองกระบี่ กระบี่ 81000",
    "119/3 หมู่ 1 ถนนราชดำเนิน ตำบลท่าวัง อำเภอเมืองนครศรีธรรมราช นครศรีธรรมราช 80000",

    # ภาคตะวันออก & ตะวันตก & กลาง
    "89/15 หมู่ 9 ถนนสุขุมวิท ตำบลหนองปรือ อำเภอบางละมุง ชลบุรี 20150",
    "314/2 หมู่ 2 ถนนสุขุมวิท ตำบลเนินพระ อำเภอเมืองระยอง ระยอง 21000",
    "56/7 ถนนท่าหลวง ตำบลวัดใหม่ อำเภอเมืองจันทบุรี จันทบุรี 22000",
    "67/2 หมู่ 3 ถนนแสงชูโต ตำบลท่าล้อ อำเภอท่าม่วง กาญจนบุรี 71110",
    "150/4 ถนนเพชรเกษม ตำบลหัวหิน อำเภอหัวหิน ประจวบคีรีขันธ์ 77110",
    "112/8 หมู่ 3 ถนนโรจนะ ตำบลคลองสวนพลู อำเภอพระนครศรีอยุธยา พระนครศรีอยุธยา 13000"
]

BRANDS = ['Omazz', 'Lotus', 'Dunlopillo']
PREFIXES = ['081', '089', '094', '086', '093', '063', '064', '096', '082', '095', '098']

def random_phone():
    return f"{random.choice(PREFIXES)}{random.randint(1000000, 9999999)}"

def random_warranty_dates():
    days_back = random.randint(180, 1100)
    start_dt = datetime.now() - timedelta(days=days_back)
    end_dt = start_dt + timedelta(days=365 * 10)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

def run_sync():
    print(f"🔄 กำลังเชื่อมต่อไปยังฐานข้อมูล: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # อ่านรายชื่อคอลัมน์ทั้งหมดที่มีจริงใน call_records
        cursor.execute("PRAGMA table_info(call_records);")
        columns = [row[1] for row in cursor.fetchall()]

        # ดึงรายชื่อ agent_code ที่มีในตาราง agents
        agent_codes = ['EMP001']
        try:
            cursor.execute("SELECT agent_code FROM agents;")
            agents = [r[0] for r in cursor.fetchall() if r[0]]
            if agents:
                agent_codes = agents
        except Exception:
            pass

        # ดึงข้อมูลทุกเคส
        cursor.execute("SELECT id, customer_phone, firstname, lastname, brand FROM call_records ORDER BY id ASC;")
        records = cursor.fetchall()

        phone_customer_map = {}

        for rec in records:
            r_id, phone, fn, ln, brand = rec
            phone = (phone or '').strip()
            if not phone or phone in ['-', '—', 'None']:
                if phone_customer_map and random.random() < 0.3:
                    phone = random.choice(list(phone_customer_map.keys()))
                else:
                    phone = random_phone()

            if phone in phone_customer_map:
                cust_info = phone_customer_map[phone]
            else:
                s_date, e_date = random_warranty_dates()
                cust_info = {
                    'firstname': random.choice(FIRSTNAMES),
                    'lastname': random.choice(LASTNAMES),
                    'brand': brand if brand and brand != 'Unknown' else random.choice(BRANDS),
                    'address': random.choice(ADDRESSES),
                    'start_date': s_date,
                    'end_date': e_date
                }
                phone_customer_map[phone] = cust_info

            assigned = random.choice(agent_codes)
            resolved = 'resolved' if random.random() < 0.8 else 'in_progress'

            # สร้างคำสั่ง SQL เฉพาะคอลัมน์ที่มีอยู่จริงในฐานข้อมูล
            update_clauses = []
            params = []

            def add_field(field_name, value):
                if field_name in columns:
                    update_clauses.append(f"{field_name} = ?")
                    params.append(value)

            add_field("customer_phone", phone)
            add_field("firstname", cust_info['firstname'])
            add_field("lastname", cust_info['lastname'])
            add_field("brand", cust_info['brand'])
            add_field("status", "done")
            add_field("case_stage", resolved)
            add_field("assigned_agent_code", assigned)
            add_field("handled_by", assigned)
            add_field("address", cust_info['address'])
            add_field("start_date", cust_info['start_date'])
            add_field("end_date", cust_info['end_date'])

            if update_clauses:
                params.append(r_id)
                query = f"UPDATE call_records SET {', '.join(update_clauses)} WHERE id = ?;"
                cursor.execute(query, params)

        conn.commit()
        print(f"✅ สำเร็จ! อัปเดตข้อมูลลูกค้า {len(phone_customer_map)} ราย และบันทึก {len(records)} เคสเรียบร้อย")
        print(f"🏠 ที่อยู่ต่างจังหวัดทั่วประเทศและวันรับประกัน 10 ปี ถูกอัปเดตลง callcenter.db ครบถ้วนแล้ว")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_sync()