import os
from dotenv import load_dotenv

# تحميل القيم من ملف .env إذا كان موجوداً (للتجربة المحلية)
load_dotenv()

# قراءة المتغيرات
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MOBILE_KEY = os.getenv("MOBILE_KEY")
API_URL = os.getenv("API_URL")

# تجميع بيانات المحافظ في قاموس لسهولة الاستخدام في البوت
WALLETS_CREDENTIALS = {
    "المحفظة الأولى 🥇": {
        "email": os.getenv("WALLET1_EMAIL"),
        "password": os.getenv("WALLET1_PASS")
    },
    "المحفظة الثانية 🥈": {
        "email": os.getenv("WALLET2_EMAIL"),
        "password": os.getenv("WALLET2_PASS")
    },
     "المحفظة الثالثة 🥉": {
        "email": os.getenv("WALLET3_EMAIL"),
        "password": os.getenv("WALLET3_PASS")
    }
}
