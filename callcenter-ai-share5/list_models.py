import requests

# ใส่ API Key ของคุณ
api_key = "sk-kxivpnfX8Mjmew8XFGCJESTp0KA3gcoA9taum9Vs77JAk0Yf"

url = "https://api.opentyphoon.ai/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}"
}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json()
        print("--- รายชื่อโมเดลที่คุณใช้ได้ ---")
        for m in models['data']:
            print(f"✅ {m['id']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")