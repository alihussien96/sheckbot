import logging
import requests
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# 🔄 استيراد الإعدادات من ملف config
from config import TELEGRAM_TOKEN, MOBILE_KEY, API_URL, WALLETS_CREDENTIALS
from datetime import datetime, timedelta
# ------------------- إعدادات الأمان -------------------
TELEGRAM_TOKEN = "ضع_توكن_البوت_هنا" # 🔴 استبدله بتوكنك
MOBILE_KEY = "fe9b67be-593c-11ee-8c99-0242ac120002"
API_URL = "https://agents.ichancy.com/global/api"

# 🔴 ضع بيانات محافظك الحقيقية هنا
WALLETS_CREDENTIALS = {
    "المحفظة 1 🥇": {"email": "email1@com", "password": "pass1"},
    "المحفظة 2 🥈": {"email": "email2@com", "password": "pass2"},
}

# ------------------- دوال الاتصال (Backend) -------------------
def api_login(email, password):
    """تسجيل الدخول وجلب الجلسة"""
    session = requests.Session()
    headers = {
        "User-Agent": "okhttp/4.9.0",
        "Partner-Mobile-Key": MOBILE_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "username": email,
        "password": password,
        "device_id": "bot_report_v1",
        "partner_key": MOBILE_KEY
    }
    try:
        resp = session.post(f"{API_URL}/User/signin", json=payload, headers=headers)
        if resp.status_code == 200 and resp.json().get("status"):
            return session
        return None
    except:
        return None

def api_get_player_report(session, player_username, days=30):
    """جلب تقرير العمليات وحساب المجاميع"""
    headers = {"Partner-Mobile-Key": MOBILE_KEY}
    
    # تحديد المدة الزمنية (من اليوم إلى X يوم سابق)
    to_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    payload = {
        "fromDate": from_date,
        "toDate": to_date,
        "playerUsername": player_username, # اسم اللاعب
        "type": -1, # -1 تعني جلب الكل (إيداع وسحب)
        "status": 1 # العمليات الناجحة فقط
    }
    
    try:
        # هذا هو الرابط المسؤول عن "التقارير -> التحويلات"
        response = session.post(f"{API_URL}/Report/getTransferReport", json=payload, headers=headers)
        data = response.json()
        
        if data.get("status") and "result" in data:
            transactions = data["result"] # قد تكون result['list'] حسب رد السيرفر
            
            total_deposit = 0.0
            total_withdraw = 0.0
            details_text = ""
            
            # تحليل البيانات وحساب المجموع
            # ملاحظة: أسماء الحقول (amount, type) قد تحتاج تعديل بسيط بعد أول تجربة
            for tx in transactions:
                amount = float(tx.get('amount', 0))
                # تحديد نوع العملية (إيداع أم سحب)
                # القيم هنا تعتمد على رد الموقع، عادة 1=إيداع، 2=سحب
                # أو قد يأتي النص صريحاً "Deposit"
                op_type = str(tx.get('type', '')).lower()
                comment = tx.get('comment', '')
                
                # منطق الجمع (يحتاج تدقيق حسب استجابة الموقع الفعلية)
                if 'deposit' in op_type or 'deposit' in comment.lower() or tx.get('type') == 1:
                    total_deposit += amount
                    icon = "📥"
                elif 'withdraw' in op_type or 'withdraw' in comment.lower() or tx.get('type') == 2:
                    total_withdraw += amount
                    icon = "📤"
                else:
                    icon = "🔄"
                
                date = tx.get('date', 'N/A')
                details_text += f"{icon} {amount} | {date}\n"

            return {
                "success": True,
                "deposit": total_deposit,
                "withdraw": total_withdraw,
                "details": details_text,
                "net": total_deposit - total_withdraw # الصافي
            }
        else:
            return {"success": False, "msg": "لا توجد بيانات أو خطأ في الاتصال"}
            
    except Exception as e:
        return {"success": False, "msg": str(e)}

# ------------------- منطق البوت -------------------
CHOOSING_WALLET, ACTION_MENU, INPUT_REPORT_USER = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الخطوة 1: اختيار المحفظة"""
    buttons = [[KeyboardButton(w)] for w in WALLETS_CREDENTIALS.keys()]
    await update.message.reply_text(
        "مرحباً بك في نظام التقارير الآلي 📊\nاختر المحفظة:", 
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    )
    return CHOOSING_WALLET

async def choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text
    if wallet not in WALLETS_CREDENTIALS:
        await update.message.reply_text("❌ محفظة غير صحيحة.")
        return CHOOSING_WALLET
    
    context.user_data['wallet'] = wallet
    
    # القائمة الرئيسية
    keyboard = [
        [KeyboardButton("📄 تقرير لاعب (إيداع/سحب)")],
        [KeyboardButton("🔙 رجوع")]
    ]
    await update.message.reply_text(f"تم تفعيل: {wallet} ✅", reply_markup=ReplyKeyboardMarkup(keyboard))
    return ACTION_MENU

async def ask_player_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب اسم المستخدم للتقرير"""
    await update.message.reply_text("🔎 أرسل **اسم المستخدم (Username)** الخاص باللاعب لجلب التقرير:")
    return INPUT_REPORT_USER

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ التقرير وعرض النتيجة"""
    player_username = update.message.text
    wallet_name = context.user_data['wallet']
    creds = WALLETS_CREDENTIALS[wallet_name]
    
    await update.message.reply_text("⏳ جاري سحب البيانات من السيرفر وتحليلها...")
    
    # 1. تسجيل الدخول
    session = api_login(creds['email'], creds['password'])
    
    if session:
        # 2. جلب التقرير (آخر 30 يوم افتراضياً)
        report = api_get_player_report(session, player_username, days=30)
        
        if report["success"]:
            msg = f"📊 **تقرير اللاعب:** `{player_username}`\n"
            msg += f"📅 المدة: آخر 30 يوم\n\n"
            msg += f"📥 **مجموع الإيداع:** {report['deposit']}\n"
            msg += f"📤 **مجموع السحب:** {report['withdraw']}\n"
            msg += f"📈 **الصافي (ربح الوكيل):** {report['net']}\n"
            msg += "----------------------------\n"
            msg += "**📝 تفاصيل العمليات:**\n"
            msg += report['details'] if report['details'] else "لا توجد عمليات."
            
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"⚠️ خطأ: {report['msg']}")
    else:
        await update.message.reply_text("❌ فشل تسجيل الدخول.")
        
    return ACTION_MENU

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_WALLET: [MessageHandler(filters.TEXT, choose_wallet)],
            ACTION_MENU: [
                MessageHandler(filters.Regex("^📄 تقرير لاعب"), ask_player_report),
                MessageHandler(filters.Regex("^🔙 رجوع"), back_to_start)
            ],
            INPUT_REPORT_USER: [MessageHandler(filters.TEXT, generate_report)]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    app.add_handler(conv)
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
