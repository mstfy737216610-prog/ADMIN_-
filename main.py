#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
المرحلة الأولى: البوت الأساسي وإدارة الجلسات عبر Pyrogram
(Phase 1: Pyrogram Bot & In-Memory Session Login Flow)
================================================================================
الوظيفة:
1. يستقبل أوامر المستخدمين (/start) ويعرض أزراراً تفاعلية للتحكم.
2. يدير عملية تسجيل الدخول عبر عميل مؤقت في الذاكرة (Client in_memory=True).
3. يطلب رقم الهاتف، ثم كود التحقق (OTP) بدلاً من input() عبر دالة ask_user().
4. يتعامل مع التحقق بخطوتين (SESSION_PASSWORD_NEEDED).
5. يستخرج الجلسة النصية (session_string = await app.export_session_string()).
6. يحفظ الجلسة في قاعدة البيانات database/data.db عبر save_session_to_db().
7. يحتوي على خادم فحص صحة خفيف (Keep-Alive) لتشغيل البوت 24/7 في الاستضافات المجانية.
================================================================================
"""

import os
import sys
import re
import time
import json
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

# استيراد طبقة قاعدة البيانات
import database as db

# استيراد مكتبة Pyrogram
try:
    from pyrogram import Client, filters
    from pyrogram.types import (
        InlineKeyboardMarkup,
        InlineKeyboardButton,
        Message,
        CallbackQuery
    )
    from pyrogram.errors import (
        SessionPasswordNeeded,
        PhoneCodeInvalid,
        PhoneCodeExpired,
        PhoneNumberInvalid,
        PasswordHashInvalid,
        FloodWait
    )
except ImportError:
    # لتوضيح التثبيت في حال تشغيل الكود في بيئة محلية جديدة
    print("⚠️ مكتبة Pyrogram غير مثبتة. يرجى تثبيتها عبر: pip install pyrogram tgcrypto")

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [MainBot] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# الإعدادات العامة لتيليجرام
BOT_TOKEN = os.getenv("BOT_TOKEN", "8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4").strip()
API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7607633343"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "M_S_F_G").replace("@", "").strip()

# منفذ خادم Keep-Alive للاستضافات المجانية (Render, Railway, Heroku, Free Bot Host)
PORT = int(os.getenv("PORT", os.getenv("KEEPALIVE_PORT", "8088")))

# مصفوفة الانتظار غير المتزامنة للمحادثات (بديل input عبر bot.ask)
# user_id -> asyncio.Future
PENDING_ANSWERS: Dict[int, asyncio.Future] = {}


# ==============================================================================
# خادم فحص الصحة لمنع إيقاف الاستضافات المجانية (Keep-Alive Server)
# ==============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        stats = db.get_stats()
        res = {
            "status": "online",
            "bot": "@admiuin_bot",
            "framework": "Pyrogram Multi-Session Engine",
            "stats": stats,
            "timestamp": int(time.time()),
            "message": "خادم اليوزربوت ومحرر المحتوى يعمل بنجاح 24/7"
        }
        self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_keepalive_http():
    """تشغيل خادم HTTP في خيط خلفي للاستضافات المجانية"""
    for p in [PORT, 8088, 8089, 8090, 8000]:
        try:
            server = HTTPServer(("0.0.0.0", p), HealthCheckHandler)
            logging.info(f"🌐 خادم Keep-Alive للاستضافة المجانية يعمل على المنفذ: {p}")
            server.serve_forever()
            break
        except Exception:
            continue


# ==============================================================================
# دالة استقبال الرد بدلاً من input() عبر await bot.ask()
# ==============================================================================
async def ask_user(bot_client: Client, chat_id: int, prompt_text: str, timeout: int = 300) -> str:
    """
    إرسال رسالة للمستخدم وانتظار رده القادم بشكل غير متزامن (Asynchronous Conversation Handler)
    هذه الدالة تستبدل input() لكي لا يتم حظر السيرفر، وتعمل داخل تيليجرام مباشرة.
    """
    await bot_client.send_message(chat_id, prompt_text)
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    PENDING_ANSWERS[chat_id] = future

    try:
        reply_message: Message = await asyncio.wait_for(future, timeout=timeout)
        return reply_message.text.strip()
    finally:
        PENDING_ANSWERS.pop(chat_id, None)


# ==============================================================================
# 2. دالة تسجيل الدخول واستخراج الجلسة (الكود الأساسي المطلوب بدقة)
# ==============================================================================
async def login_and_get_session(bot_client: Client, user_id: int, chat_id: int, phone_number: str) -> Optional[str]:
    """
    تسجيل الدخول واستخراج الجلسة النصية عبر عميل Pyrogram مؤقت في الذاكرة:
    1. إنشاء عميل مؤقت في الذاكرة (Client in_memory=True).
    2. الاتصال وإرسال كود التحقق (send_code).
    3. طلب الكود من المستخدم عبر البوت (ask_user) بدلاً من input().
    4. تسجيل الدخول (sign_in) والتعامل مع 2FA (check_password).
    5. استخراج الجلسة (export_session_string) وحفظها في قاعدة البيانات عبر save_session_to_db().
    """
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone_number)
    if not clean_phone.startswith("+"):
        clean_phone = "+" + clean_phone

    logging.info(f"📲 بدء تسجيل الدخول للرقم: {clean_phone} (معرف المستخدم: {user_id})")

    # إنشاء عميل مؤقت في الذاكرة (in_memory=True) لعدم حفظ ملفات على السيرفر
    app = Client(
        "::memory::",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )

    await app.connect()

    try:
        # إرسال كود التحقق (OTP) إلى رقم هاتف المستخدم
        await bot_client.send_message(chat_id, "⏳ جاري إرسال كود التحقق من سيرفرات تيليجرام...")
        sent_code = await app.send_code(clean_phone)

        # استقبال كود التحقق عبر واجهة البوت بدلاً من input()
        code_prompt = f"""📩 **تم إرسال كود التحقق (OTP) إلى حسابك في تيليجرام!**
📱 الرقم: `{clean_phone}`

أرسل كود التحقق الآن هنا في المحادثة:
(مثال: `12345` أو بأي صيغة)"""

        entered_code = await ask_user(bot_client, chat_id, code_prompt, timeout=180)
        clean_code = entered_code.replace(" ", "").replace("-", "")

        try:
            # تسجيل الدخول بالكود
            await app.sign_in(clean_phone, sent_code.phone_code_hash, clean_code)
        except Exception as e:
            # إذا كان الحساب محمياً بكلمة مرور التحقق بخطوتين (2FA)
            err_str = str(e).upper()
            if "SESSION_PASSWORD_NEEDED" in err_str or isinstance(e, SessionPasswordNeeded):
                password_prompt = """🔐 **حسابك محمي بالتحقق بخطوتين (2FA Password):**
أرسل كلمة مرور حسابك السحابية الآن:"""
                password = await ask_user(bot_client, chat_id, password_prompt, timeout=180)
                await app.check_password(password)
            else:
                raise e

        # استخراج الجلسة (Session String) وحفظها في قاعدة البيانات
        session_string = await app.export_session_string()
        db.save_session_to_db(user_id, clean_phone, session_string)

        success_text = f"""🎉 **تم استخراج الجلسة وربط حسابك بنجاح!**
📱 الرقم: `{clean_phone}`
🔒 تم حفظ الـ `session_string` في قاعدة البيانات بأمان (`database/data.db`).
🚀 أصبح عامل الزحف في الخلفية قادراً الآن على قراءة القنوات ونشر المنشورات كأنك أنت من يكتبها!"""

        await bot_client.send_message(chat_id, success_text, reply_markup=get_main_keyboard(True))
        return session_string

    except PhoneCodeInvalid:
        await bot_client.send_message(chat_id, "❌ كود التحقق الذي أدخلته غير صحيح. حاول مجدداً من زر تسجيل الدخول.", reply_markup=get_main_keyboard(False))
    except PhoneCodeExpired:
        await bot_client.send_message(chat_id, "⚠️ انتهت صلاحية كود التحقق. أعد المحاولة من جديد.", reply_markup=get_main_keyboard(False))
    except PhoneNumberInvalid:
        await bot_client.send_message(chat_id, "❌ رقم الهاتف غير صالح. تأكد من إدخال الرمز الدولي (مثال: `+966500000000`).", reply_markup=get_main_keyboard(False))
    except PasswordHashInvalid:
        await bot_client.send_message(chat_id, "❌ كلمة المرور غير صحيحة. حاول مرة أخرى.", reply_markup=get_main_keyboard(False))
    except FloodWait as fw:
        await bot_client.send_message(chat_id, f"⏳ تيليجرام يطلب الانتظار {fw.value} ثانية (FloodWait).", reply_markup=get_main_keyboard(False))
    except asyncio.TimeoutError:
        await bot_client.send_message(chat_id, "⌛️ انتهى وقت الانتظار دون إدخال الكود. اضغط زر تسجيل الدخول للبدء مجدداً.", reply_markup=get_main_keyboard(False))
    except Exception as e:
        logging.error(f"خطأ أثناء تسجيل الدخول: {e}")
        await bot_client.send_message(chat_id, f"❌ حدث خطأ أثناء توثيق الحساب: {e}", reply_markup=get_main_keyboard(False))
    finally:
        try:
            await app.disconnect()
        except Exception:
            pass
    return None


# ==============================================================================
# أزرار البوت ولوحات المفاتيح التفاعلية
# ==============================================================================
def get_main_keyboard(has_session: bool) -> InlineKeyboardMarkup:
    """بناء أزرار التحكم الرئيسية"""
    if has_session:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 إدارة الحملات وقنوات النشر", callback_data="btn_campaigns")],
            [InlineKeyboardButton("➕ إنشاء حملة جديدة", callback_data="btn_new_campaign"),
             InlineKeyboardButton("📋 المصادر المراقبة", callback_data="btn_sources")],
            [InlineKeyboardButton("🎯 إعلاني الخاص (المنافسين)", callback_data="btn_ad"),
             InlineKeyboardButton("⚙️ تعليمات الذكاء الاصطناعي", callback_data="btn_prompt")],
            [InlineKeyboardButton("📊 إحصائيات النشاط", callback_data="btn_stats"),
             InlineKeyboardButton("🚪 تسجيل الخروج (حذف الجلسة)", callback_data="btn_logout")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 تسجيل الدخول (استخراج الجلسة ورقم الهاتف)", callback_data="btn_login")],
            [InlineKeyboardButton("ℹ️ كيف يعمل اليوزربوت والذكاء الاصطناعي؟", callback_data="btn_info")]
        ])


# ==============================================================================
# إعداد عميل البوت عبر Pyrogram
# ==============================================================================
bot = Client(
    "bot_app",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# 1. اعتراض أي رسالة قادمة إذا كان المستخدم بانتظار إدخال رد (bot.ask)
@bot.on_message(filters.private & ~filters.command(["start", "help", "cancel"]))
async def message_router_or_answer(client: Client, message: Message):
    chat_id = message.chat.id

    # إذا كان هناك طلب انتظار إجابة غير متزامن (Future)
    if chat_id in PENDING_ANSWERS:
        fut = PENDING_ANSWERS[chat_id]
        if not fut.done():
            fut.set_result(message)
            return

    # إذا أرسل المستخدم رقمه مباشرة لبدء التسجيل
    txt = message.text.strip() if message.text else ""
    if re.match(r'^\+?[0-9]{7,15}$', txt):
        asyncio.create_task(login_and_get_session(client, message.from_user.id, chat_id, txt))
        return


# 2. أمر البداية /start
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "المستخدم"

    user_data = db.get_user(user_id)
    has_session = bool(user_data and user_data.get("session") and len(user_data["session"]) > 15)

    status_badge = "🟢 **حسابك مربوط وجلستك نشطة بنجاح!**" if has_session else "🔴 **لم تسجل دخولك بعد** (سجل رقمك ليتمكن البوت من قراءة القنوات نيابة عنك)."

    welcome_msg = f"""👋 **أهلاً بك يا {first_name}!**

🤖 **محرر المحتوى والناشر الأكاديمي الذكي (Userbot Core Engine)**
النظام يعمل بجلسات المستخدمين الحقيقية لقراءة القنوات وإعادة صياغتها بالذكاء الاصطناعي والنشر باسمك مباشرة.

📌 **حالة الجلسة الخاصة بك:**
{status_badge}

👇 **اختر من الأزرار أدناه للبدء:**"""

    await message.reply_text(welcome_msg, reply_markup=get_main_keyboard(has_session))


# 3. معالجة الضغط على الأزرار التفاعلية (Callback Queries)
@bot.on_callback_query()
async def callback_dispatcher(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    user_data = db.get_user(user_id)
    has_session = bool(user_data and user_data.get("session") and len(user_data["session"]) > 15)

    if data == "btn_main":
        await query.message.edit_text("🎛 **لوحة التحكم الرئيسية:**", reply_markup=get_main_keyboard(has_session))

    elif data == "btn_info":
        info_text = """💡 **آلية عمل البوت تحت الغطاء (اليوزربوت):**

1. **قراءة القنوات بدون رتبة إشراف:**
البوتات العادية لا تقرأ القنوات. نحن نسجل دخولك كـ "مستخدم حقيقي" ونستخرج الـ `session_string`، فيفتح الكود اتصالاً بجلسة حسابك ويقرأ المنشورات.
2. **الذكاء الاصطناعي (DeepSeek):**
يعيد صياغة المنشور كأنه حصري لقناتك، وإذا كان المحتوى غير مفيد يرد بـ `SKIP` فيتم حذفه وتخطيه.
3. **النشر بجلسة المستخدم:**
ينشر في قناة الهدف باسمك وبجلستك أنت، فتظهر الرسالة كأنك أنت الناشر مع كامل الصور.
4. **العزل الأمني الصارم:**
لا يتم استخدام جلسة المشرف لأي مستخدم آخر. كل مستخدم يعمل بجلسته الخاصة المستقلة."""
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="btn_main")]])
        await query.message.edit_text(info_text, reply_markup=back_btn)

    elif data == "btn_login":
        # المرحلة الأولى: طلب رقم الهاتف ثم بدء تسجيل الدخول
        ask_phone_prompt = """📱 **المرحلة الأولى: تسجيل الدخول واستخراج الجلسة:**

أرسل الآن رقم هاتفك مع الرمز الدولي في هذه المحادثة:
(مثال: `+966501234567` أو `+96590123456`)

⚠️ *سيصلك كود تحقق (OTP) على حسابك في تيليجرام.*"""
        await query.message.edit_text(ask_phone_prompt)

        # استقبال رقم الهاتف عبر ask_user
        try:
            phone_input = await ask_user(client, chat_id, "👉 اكتب رقم هاتفك الآن وأرسله:", timeout=120)
            asyncio.create_task(login_and_get_session(client, user_id, chat_id, phone_input))
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "⌛️ انتهى وقت إدخال الرقم. اضغط زر تسجيل الدخول للبدء مجدداً.", reply_markup=get_main_keyboard(False))

    elif data == "btn_logout":
        db.delete_user_session(user_id)
        await query.message.edit_text("✅ تم تسجيل الخروج وحذف جلستك من قاعدة البيانات بنجاح.", reply_markup=get_main_keyboard(False))

    elif data == "btn_campaigns":
        campaigns = db.get_user_campaigns(user_id)
        if not campaigns:
            text = "⚠️ ليس لديك أي حملات حالياً. اضغط الزر أدناه لإنشاء أول حملة لك!"
            btns = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إنشاء حملة الآن", callback_data="btn_new_campaign")],
                [InlineKeyboardButton("🔙 العودة", callback_data="btn_main")]
            ])
            await query.message.edit_text(text, reply_markup=btns)
            return

        lines = ["📢 **حملاتك الإعلانية والنشر:**\n"]
        buttons_list = []
        for c in campaigns:
            status = "🟢 نشطة" if c["enabled"] else "⏸ متوقفة"
            src_count = len(c.get("sources", []))
            lines.append(f"• **{c['name']}** ({status})\n  الهدف: `{c['target_channel']}` | المصادر: {src_count}\n")
            buttons_list.append([InlineKeyboardButton(f"⚙️ إدارة: {c['name']}", callback_data=f"camp_view_{c['id']}")])

        buttons_list.append([InlineKeyboardButton("➕ إضافة حملة جديدة", callback_data="btn_new_campaign")])
        buttons_list.append([InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="btn_main")])
        await query.message.edit_text("".join(lines), reply_markup=InlineKeyboardMarkup(buttons_list))

    elif data == "btn_new_campaign":
        await query.message.edit_text("🏷 **إنشاء حملة جديدة:**\nأرسل الآن اسم الحملة (مثال: `أخبار جامعة الملك سعود`):")
        try:
            name_input = await ask_user(client, chat_id, "👉 أرسل اسم الحملة:", timeout=120)
            target_input = await ask_user(client, chat_id, f"📢 أرسل الآن **معرّف قناة النشر الهدف** للحملة [{name_input}]:\n(مثال: `@MyChannel` أو `-100123456789`)", timeout=120)

            camp_id = db.create_campaign(user_id, name_input, target_input)
            await client.send_message(chat_id, f"🎉 **تم إنشاء الحملة بنجاح!**\nالاسم: `{name_input}`\nالقناة الهدف: `{target_input}`", reply_markup=get_main_keyboard(True))
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "⌛️ انتهى وقت الانتظار.", reply_markup=get_main_keyboard(True))

    elif data.startswith("camp_view_"):
        camp_id = data.replace("camp_view_", "")
        campaigns = db.get_user_campaigns(user_id)
        camp = next((c for c in campaigns if c["id"] == camp_id), None)
        if not camp:
            await query.answer("الحملة غير موجودة", show_alert=True)
            return

        status_str = "🟢 نشطة" if camp["enabled"] else "⏸ متوقفة"
        sources = camp.get("sources", [])
        src_lines = "\n".join([f"  - `{s['target']}` (آخر رسالة: {s.get('last_processed_id', 0)})" for s in sources]) if sources else "  (لا توجد مصادر مضافة بعد)"

        text = f"""⚙️ **إدارة الحملة:** **{camp['name']}**
• الحالة: {status_str}
• قناة النشر الهدف: `{camp['target_channel']}`
• المصادر المراقبة ({len(sources)}):
{src_lines}"""

        toggle_txt = "⏸ إيقاف مؤقت" if camp["enabled"] else "▶️ تفعيل الحملة"
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton(toggle_txt, callback_data=f"camp_tgl_{camp_id}"),
             InlineKeyboardButton("➕ إضافة مصدر للمراقبة", callback_data=f"camp_asrc_{camp_id}")],
            [InlineKeyboardButton("🗑 حذف الحملة", callback_data=f"camp_del_{camp_id}")],
            [InlineKeyboardButton("🔙 قائمة الحملات", callback_data="btn_campaigns")]
        ])
        await query.message.edit_text(text, reply_markup=btns)

    elif data.startswith("camp_tgl_"):
        camp_id = data.replace("camp_tgl_", "")
        campaigns = db.get_user_campaigns(user_id)
        camp = next((c for c in campaigns if c["id"] == camp_id), None)
        if camp:
            db.update_campaign(camp_id, enabled=0 if camp["enabled"] else 1)
            await query.answer("تم تغيير حالة الحملة!")
            query.data = f"camp_view_{camp_id}"
            await callback_dispatcher(client, query)

    elif data.startswith("camp_del_"):
        camp_id = data.replace("camp_del_", "")
        db.delete_campaign(camp_id)
        await query.answer("تم حذف الحملة بنجاح!", show_alert=True)
        query.data = "btn_campaigns"
        await callback_dispatcher(client, query)

    elif data.startswith("camp_asrc_"):
        camp_id = data.replace("camp_asrc_", "")
        try:
            src_input = await ask_user(client, chat_id, "📥 **أرسل الآن رابط أو معرّف القناة المصدرية المطلوب مراقبتها:**\n(مثال: `@KSU_News` أو رابط القناة)", timeout=120)
            db.add_source(camp_id, user_id, src_input.strip(), title=src_input.strip())
            await client.send_message(chat_id, f"✅ تمت إضافة المصدر `{src_input}` بنجاح!", reply_markup=get_main_keyboard(True))
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "⌛️ انتهى وقت الانتظار.", reply_markup=get_main_keyboard(True))

    elif data == "btn_sources":
        campaigns = db.get_user_campaigns(user_id)
        all_s = []
        for c in campaigns:
            for s in c.get("sources", []):
                all_s.append(f"• `{s['target']}` -> حملة [{c['name']}] (آخر رسالة: {s.get('last_processed_id', 0)})")
        msg_t = "📋 **المصادر المراقبة الخاصة بحسابك:**\n\n" + ("\n".join(all_s) if all_s else "⚠️ لا توجد مصادر مضافة بعد.")
        await query.message.edit_text(msg_t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="btn_main")]]))

    elif data == "btn_stats":
        st = db.get_stats(user_id)
        txt = f"""📊 **إحصائيات حسابك:**
• إجمالي الحملات: {st.get('campaigns', 0)}
• المصادر المراقبة: {st.get('sources', 0)}
• المنشورات الناجحة في قناتك: {st.get('forwarded', 0)}
• إعلانات منافسين تم استبدالها: {st.get('ad_replaced', 0)}
• رسائل تم استبعادها بقرار الذكاء (SKIP): {st.get('skipped', 0)}"""
        await query.message.edit_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="btn_main")]]))

    elif data == "btn_ad":
        try:
            ad_text = await ask_user(client, chat_id, "🎯 **أرسل الآن نص إعلان خدماتك الطلابية** الذي سيستبدل إعلانات المنافسين تلقائياً:", timeout=180)
            campaigns = db.get_user_campaigns(user_id)
            for c in campaigns:
                db.update_campaign(c["id"], custom_ad=ad_text)
            await client.send_message(chat_id, "✅ تم حفظ وتحديث إعلان خدماتك الطلابية بنجاح!", reply_markup=get_main_keyboard(True))
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "⌛️ انتهى وقت الانتظار.", reply_markup=get_main_keyboard(True))

    elif data == "btn_prompt":
        try:
            prompt_input = await ask_user(client, chat_id, "⚙️ **أرسل تعليمات الصياغة للذكاء الاصطناعي** (مثال: `أسلوب أكاديمي مباشر مع إبراز المواعيد`):", timeout=180)
            campaigns = db.get_user_campaigns(user_id)
            for c in campaigns:
                db.update_campaign(c["id"], custom_instruction=prompt_input)
            await client.send_message(chat_id, "✅ تم حفظ وتحديث تعليمات الذكاء الاصطناعي بنجاح!", reply_markup=get_main_keyboard(True))
        except asyncio.TimeoutError:
            await client.send_message(chat_id, "⌛️ انتهى وقت الانتظار.", reply_markup=get_main_keyboard(True))


# ==============================================================================
# تشغيل التطبيق الكامل (المرحلة الأولى + المرحلة الثانية في الخلفية)
# ==============================================================================
async def main_application():
    # 1. تهيئة قاعدة البيانات
    db.init_db()

    # 2. تشغيل خادم Keep-Alive في خيط مستقل للاستضافات المجانية
    threading.Thread(target=run_keepalive_http, daemon=True).start()

    # 3. تشغيل المرحلة الثانية (عامل الزحف والنشر) في الخلفية
    import worker
    asyncio.create_task(worker.worker_task_loop())

    # 4. تشغيل البوت الأساسي عبر Pyrogram مع حذف أي ويب هوك قديم لمنع التعارض
    logging.info("🚀 تشغيل البوت الأساسي عبر Pyrogram...")
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception as e:
        logging.warning(f"delete_webhook note: {e}")
    await bot.start()
    bot_me = await bot.get_me()
    logging.info(f"✅ تم تشغيل البوت بنجاح: @{bot_me.username} ({bot_me.first_name})")

    # إبقاء البوت مستمراً
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main_application())
    except KeyboardInterrupt:
        logging.info("🛑 تم إيقاف البوت بأمان.")
