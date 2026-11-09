# backend/recalc_scores.py
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ชี้ไปที่ callcenter.db (ไฟล์ฐานข้อมูลจริงของระบบ)
DATABASE_PATH = os.path.join(BASE_DIR, "callcenter.db")

def update_scores_to_100():
    if not os.path.exists(DATABASE_PATH):
        # เผื่อไฟล์อยู่ที่ root folder
        alt_path = os.path.join(os.path.dirname(BASE_DIR), "callcenter.db")
        if os.path.exists(alt_path):
            target_db = alt_path
        else:
            print(f"ไม่พบไฟล์ฐานข้อมูล callcenter.db")
            return
    else:
        target_db = DATABASE_PATH

    print(f"กำลังเชื่อมต่อฐานข้อมูล: {target_db}")
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        target_table = None
        for candidate in ["call_records", "calls", "call_analyses", "records"]:
            if candidate in tables:
                target_table = candidate
                break

        if not target_table:
            user_tables = [t for t in tables if not t.startswith("sqlite_")]
            if user_tables:
                target_table = user_tables[0]
            else:
                print("ไม่พบตารางข้อมูลในระบบ")
                return

        cursor.execute(f"PRAGMA table_info({target_table});")
        columns = [col[1] for col in cursor.fetchall()]

        score_col = None
        for candidate_col in ["sentiment_score", "satisfaction_score", "satisfaction", "score"]:
            if candidate_col in columns:
                score_col = candidate_col
                break

        if not score_col:
            print(f"ไม่พบคอลัมน์คะแนนในตาราง {target_table} (คอลัมน์ที่มี: {columns})")
            return

        query = f"""
            UPDATE {target_table}
            SET {score_col} = {score_col} * 20
            WHERE {score_col} IS NOT NULL
              AND {score_col} > 0
              AND {score_col} <= 5
        """
        cursor.execute(query)
        updated_rows = cursor.rowcount
        conn.commit()

        print(f"อัปเดตตาราง '{target_table}' คอลัมน์ '{score_col}' สำเร็จทั้งหมด {updated_rows} รายการ เป็นคะแนนเต็ม 100 แล้ว")

    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_scores_to_100()