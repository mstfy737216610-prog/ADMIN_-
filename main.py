#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
البوت الأساسي لإدارة الجلسات والحملات (Main Telegram Bot & Session Manager)
================================================================================
متوافق مع:
- استضافة البوتات المجانية (Free Bot Hosts: Render, Koyeb, Heroku, Railway, Termux, VPS)
- تيليجرام بوت للأعمال (Telegram Business & Bot API)
- إدارة الجلسات المستقلة لكل مستخدم (Multi-User Telethon StringSession)
================================================================================
"""

import os
import sys
import re
import time
import json
import asyncio
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Dict, Any, Optional

# استيراد طبقة قاعدة البيانات
import database as db

# استيراد حزمة Telethon
try:
    from telethon import TelegramClient, events, Button
    from telethon.sessions import StringSession
    from telethon.errors import (
        SessionPasswordNeededError,
        PhoneCodeInvalidError,
        PhoneCodeExpiredError,
        PhoneNumberInvalidError,
        PasswordHashInvalidError
    )
except ImportError:
    print("❌ مكتبة Telethon غير مثبتة! يرجى تثبيتها عبر: pip install telethon aiohttp")
    sys.exit(1)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [MainBot] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# الإعدادات ومفاتيح تيليجرام
BOT_TOKEN = os.getenv("BOT_TOKEN", "8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4").strip()
API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7607633343"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "M_S_F_G").replace("@", "").strip()

# منفذ خادم Keep-Alive للاستضافات المجانية (Render, Railway, Heroku)
PORT = int(os.getenv("PORT", os.getenv("KEEPALIVE_PORT", "8088")))

# حالة تسجيل دخول المستخدمين المؤقتة في الذاكرة
# user_id -> {"step": str, "phone": str, "client": TelegramClient, "phone_code_hash": str}
AUTH_STATES: Dict[int, Dict[str, Any]] = {}

# حالات انتظار المدخلات الأخرى (مثل إدخال اسم الحملة، قناة الهدف، المصدر، الإعلان)
INPUT_STATES: Dict[int, Dict[str, Any]] = {}


# ==============================================================================
# خادم فحص الصحة للحفاظ على تشغيل البوت في الاستضافات المجانية (Keep-Alive Server)
# ==============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        stats = db.get_stats()
        response_data = {
            "status": "online",
            "bot": "@admiuin_bot",
            "admin": f"@{ADMIN_USERNAME}",
            "stats": stats,
            "timestamp": int(time.time()),
            "message": "خادم محرر المحتوى التعليمي واليوزربوت يعمل بنجاح 24/7"
        }
        self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_keepalive_http():
    """تشغيل خادم HTTP في خيط منفصل للاستضافات المجانية لتجنب السكون"""
    for p in [PORT, 8088, 8089, 8090, 8000]:
        try:
            server = HTTPServer(("0.0.0.0", p), HealthCheckHandler)
            logging.info(f"🌐 خادم Keep-Alive للاستضافة المجانية يعمل على المنفذ: {p}")
            server.serve_forever()
            break
        except Exception:
            continue


# ==============================================================================
# إنشاء عميل البوت عبر Telethon
# ==============================================================================
bot = TelegramClient('bot_session', API_ID, API_HASH)


# ==============================================================================
# لوحات المفاتيح والأزرار التفاعلية
# ==============================================================================
def get_main_keyboard(has_session: bool):
    """لوحة التحكم الرئيسية"""
    if has_session:
        return [
            [Button.inline("📢 إدارة الحملات وقنوات النشر", b"menu_campaigns")],
            [Button.inline("➕ إنشاء حملة جديدة", b"menu_new_campaign"), Button.inline("📋 المصادر المراقبة", b"menu_sources")],
            [Button.inline("🎯 إعلاني الخاص (المنافسين)", b"menu_ad"), Button.inline("⚙️ تعليمات الذكاء الاصطناعي", b"menu_prompt")],
            [Button.inline("📊 إحصائيات النشاط", b"menu_stats"), Button.inline("🚪 تسجيل الخروج (حذف الجلسة)", b"menu_logout")]
        ]
    else:
        return [
            [Button.inline("📱 تسجيل الدخول (ربط الحساب باليوزربوت)", b"menu_login")],
            [Button.inline("🔑 إدخال كود الجلسة مباشرة (StringSession)", b"menu_manual_session")],
            [Button.inline("ℹ️ كيف يعمل النظام؟", b"menu_info")]
        ]


# ==============================================================================
# معالجة أوامر الرسائل النصية
# ==============================================================================
@bot.on(events.NewMessage(pattern=r"^/start"))
async def start_handler(event):
    user = await event.get_sender()
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or "المستخدم"

    # تسجيل المستخدم في قاعدة البيانات
    user_record = db.add_or_update_user(user_id, username=username, first_name=first_name)
    has_session = bool(user_record and user_record.get("session_string") and len(user_record["session_string"]) > 15)

    session_status = "🟢 حسابك مربوط وجلستك نشطة بنجاح!" if has_session else "🔴 لم تقم بربط حسابك بعد (سجل دخولك ليتمكن البوت من قراءة القنوات)."

    welcome_text = f"""👋 **أهلاً بك يا {first_name}!**

🤖 **محرر المحتوى التعليمي والجامعي الذكي (Multi-User Engine)**
نظام النشر الآلي وإعادة الصياغة بالذكاء الاصطناعي عبر حسابك الخاص (Userbot).

📌 **حالة حسابك:**
{session_status}

👇 **اختر من الأزرار أدناه للبدء:**"""

    await event.respond(welcome_text, buttons=get_main_keyboard(has_session))


@bot.on(events.NewMessage(pattern=r"^/help"))
async def help_handler(event):
    help_text = """📖 **دليل الاستخدام السريع:**

1. **تسجيل الدخول:** اضغط على زر `📱 تسجيل الدخول`، وأرسل رقم هاتفك مع الرمز الدولي (مثال: `+966500000000`).
2. **رمز التحقق:** سيصلك كود من تيليجرام، أرسله هنا ليتم استخراج جلستك الخاصة وحفظها بأمان.
3. **إنشاء حملة:** حدد اسم الحملة وقناة النشر الهدف (مثال: `@MyChannel`).
4. **إضافة مصادر:** أضف القنوات التي تريد مراقبتها (مثال: `@KSU_News`).
5. **العمل التلقائي:** سيتولى عامل الزحف في الخلفية قراءة المنشورات، صياغتها بالذكاء الاصطناعي، ونشرها في قناتك باسمك!"""
    await event.respond(help_text)


@bot.on(events.NewMessage(pattern=r"^/stats"))
async def stats_handler(event):
    user_id = event.sender_id
    stats = db.get_stats(user_id)
    text = f"""📊 **إحصائيات حسابك:**
• عدد الحملات: {stats.get('total_campaigns', 0)}
• المصادر المراقبة: {stats.get('total_sources', 0)}
• المنشورات المعالجة: {stats.get('total_processed', 0)}
• المنشورات المنشورة: {stats.get('total_forwarded', 0)}
• إعلانات تم استبدالها بإعلانك: {stats.get('total_ad_replaced', 0)}
• رسائل تم تخطيها (SKIP): {stats.get('total_skipped', 0)}"""
    await event.respond(text)


# ==============================================================================
# معالجة الأحداث التفاعلية (Inline Callbacks)
# ==============================================================================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data
    user_id = event.sender_id
    user_record = db.get_user(user_id)
    has_session = bool(user_record and user_record.get("session_string") and len(user_record["session_string"]) > 15)

    if data == b"menu_main":
        await event.edit("🎛 **لوحة التحكم الرئيسية:**", buttons=get_main_keyboard(has_session))

    elif data == b"menu_info":
        info_text = """💡 **كيف يعمل البوت تحت الغطاء؟**

1. **قراءة القنوات بدون رتبة إشراف:**
البوتات العادية لا يمكنها قراءة قنوات الآخرين. نحن نستخدم جلستك (Session String) ليتصرف الكود كأنك أنت من يقرأ القناة.
2. **الذكاء الاصطناعي:**
يقوم الكود بإعادة صياغة المنشور كأنه منشور حصري لقناتك، دون أي ذكر للمصادر السابقة.
3. **استبدال الإعلانات:**
في حال نشر المصدر إعلاناً لمنافسين (حل واجبات، بحوث)، يستبدله الكود تلقائياً بإعلان خدماتك الطلابية!
4. **الأمان الكامل:**
لا يتم مشاركة جلستك مع أي مستخدم آخر. كل مستخدم يملك خيط زحف خاص به تماماً."""
        back_btn = [[Button.inline("🔙 العودة للرئيسية", b"menu_main")]]
        await event.edit(info_text, buttons=back_btn)

    elif data == b"menu_login":
        INPUT_STATES[user_id] = {"action": "waiting_phone"}
        prompt_text = """📱 **تسجيل الدخول واستخراج الجلسة:**

يرجى إرسال رقم هاتفك مع الرمز الدولي الآن.
مثال:
`+966501234567` أو `+96590123456`

⚠️ *ملاحظة أمنية: يتم حفظ الجلسة محلياً في قاعدة البيانات المشفرة ولا يتم مشاركتها أبداً.*"""
        back_btn = [[Button.inline("❌ إلغاء", b"menu_main")]]
        await event.edit(prompt_text, buttons=back_btn)

    elif data == b"menu_manual_session":
        INPUT_STATES[user_id] = {"action": "waiting_manual_session"}
        prompt_text = """🔑 **إدخال كود الجلسة الجاهز (Telethon StringSession):**

إذا كان لديك بالفعل كود جلسة مستخرج مسبقاً، يمكنك لصقه هنا الآن:"""
        back_btn = [[Button.inline("❌ إلغاء", b"menu_main")]]
        await event.edit(prompt_text, buttons=back_btn)

    elif data == b"menu_logout":
        db.delete_user_session(user_id)
        await event.edit("✅ تم تسجيل الخروج وحذف جلستك من قاعدة البيانات بنجاح.", buttons=get_main_keyboard(False))

    elif data == b"menu_campaigns":
        campaigns = db.get_user_campaigns(user_id)
        if not campaigns:
            text = "⚠️ ليس لديك أي حملات حالياً. اضغط الزر أدناه لإنشاء أول حملة لك!"
            btns = [
                [Button.inline("➕ إنشاء حملة الآن", b"menu_new_campaign")],
                [Button.inline("🔙 العودة", b"menu_main")]
            ]
            await event.edit(text, buttons=btns)
            return

        lines = ["📢 **حملاتك الإعلانية والنشر:**\n"]
        btns = []
        for c in campaigns:
            status = "🟢 نشطة" if c["enabled"] else "⏸ متوقفة"
            src_count = len(c.get("sources", []))
            lines.append(f"• **{c['name']}** ({status})\n  الهدف: `{c['target_channel']}` | المصادر: {src_count}\n")
            btns.append([Button.inline(f"⚙️ إدارة: {c['name']}", f"camp_manage_{c['id']}".encode())])

        btns.append([Button.inline("➕ إضافة حملة جديدة", b"menu_new_campaign")])
        btns.append([Button.inline("🔙 العودة للرئيسية", b"menu_main")])
        await event.edit("".join(lines), buttons=btns)

    elif data == b"menu_new_campaign":
        INPUT_STATES[user_id] = {"action": "waiting_campaign_name"}
        await event.edit("🏷 **خطوة 1 من 2:** أرسل اسماً توضيحياً لحملتك الجديدة (مثال: `أخبار جامعة الملك سعود`):")

    elif data.startswith(b"camp_manage_"):
        camp_id = data.decode().replace("camp_manage_", "")
        campaigns = db.get_user_campaigns(user_id)
        camp = next((c for c in campaigns if c["id"] == camp_id), None)
        if not camp:
            await event.answer("الحملة غير موجودة", alert=True)
            return

        status_str = "🟢 نشطة" if camp["enabled"] else "⏸ متوقفة"
        sources = camp.get("sources", [])
        src_lines = "\n".join([f"  - `{s['target']}` ({s.get('title', '')})" for s in sources]) if sources else "  (لا توجد مصادر مضافة بعد)"

        text = f"""⚙️ **إدارة الحملة:** **{camp['name']}**
• الحالة: {status_str}
• قناة النشر الهدف: `{camp['target_channel']}`
• المصادر المراقبة ({len(sources)}):
{src_lines}

👇 **إجراءات الحملة:**"""

        toggle_txt = "⏸ إيقاف مؤقت" if camp["enabled"] else "▶️ تفعيل الحملة"
        btns = [
            [Button.inline(toggle_txt, f"camp_toggle_{camp_id}".encode()), Button.inline("➕ إضافة قناة مصدر", f"camp_addsrc_{camp_id}".encode())],
            [Button.inline("🎯 تخصيص إعلان المنافسين", f"camp_ad_{camp_id}".encode()), Button.inline("🗑 حذف الحملة", f"camp_del_{camp_id}".encode())],
            [Button.inline("🔙 قائمة الحملات", b"menu_campaigns")]
        ]
        await event.edit(text, buttons=btns)

    elif data.startswith(b"camp_toggle_"):
        camp_id = data.decode().replace("camp_toggle_", "")
        campaigns = db.get_user_campaigns(user_id)
        camp = next((c for c in campaigns if c["id"] == camp_id), None)
        if camp:
            new_state = 0 if camp["enabled"] else 1
            db.update_campaign(camp_id, enabled=new_state)
            await event.answer("تم تحديث حالة الحملة بنجاح!")
            # إعادة عرض إدارة الحملة
            cb_data = f"camp_manage_{camp_id}".encode()
            event.data = cb_data
            await callback_handler(event)

    elif data.startswith(b"camp_del_"):
        camp_id = data.decode().replace("camp_del_", "")
        db.delete_campaign(camp_id)
        await event.answer("تم حذف الحملة بنجاح!", alert=True)
        event.data = b"menu_campaigns"
        await callback_handler(event)

    elif data.startswith(b"camp_addsrc_"):
        camp_id = data.decode().replace("camp_addsrc_", "")
        INPUT_STATES[user_id] = {"action": "waiting_source_channel", "campaign_id": camp_id}
        await event.edit("📥 **أرسل الآن معرّف أو رابط القناة المصدرية المطلوب مراقبتها** (مثال: `@KSU_News` أو رابط القناة):")

    elif data == b"menu_sources":
        campaigns = db.get_user_campaigns(user_id)
        all_sources = []
        for c in campaigns:
            for s in c.get("sources", []):
                all_sources.append(f"• `{s['target']}` -> تابعة لحملة [{c['name']}] (آخر رسالة: {s.get('last_processed_id', 0)})")

        if not all_sources:
            await event.edit("⚠️ لا توجد مصادر مضافة بعد. قم بإنشاء حملة وأضف إليها قنوات للمراقبة.", buttons=[[Button.inline("🔙 العودة", b"menu_main")]])
        else:
            txt = f"📋 **قائمة المصادر المراقبة الخاصة بك ({len(all_sources)}):**\n\n" + "\n".join(all_sources)
            await event.edit(txt, buttons=[[Button.inline("🔙 العودة", b"menu_main")]])

    elif data == b"menu_stats":
        stats = db.get_stats(user_id)
        text = f"""📊 **إحصائيات حسابك الدقيقة:**
• إجمالي الحملات: {stats.get('total_campaigns', 0)}
• إجمالي المصادر المراقبة: {stats.get('total_sources', 0)}
• المنشورات التي تمت معالجتها: {stats.get('total_processed', 0)}
• المنشورات الناجحة في قناتك: {stats.get('total_forwarded', 0)}
• إعلانات منافسين تم استبدالها: {stats.get('total_ad_replaced', 0)}
• رسائل تم استبعادها بقرار الذكاء (SKIP): {stats.get('total_skipped', 0)}"""
        await event.edit(text, buttons=[[Button.inline("🔙 العودة", b"menu_main")]])

    elif data == b"menu_ad":
        INPUT_STATES[user_id] = {"action": "waiting_global_ad"}
        await event.edit("""🎯 **ضبط إعلانك الخاص للخدمات الطلابية:**
أرسل الآن النص الذي تريد نشره تلقائياً عند رصد أي إعلان لمنافسين في القنوات المصدر:""")

    elif data == b"menu_prompt":
        INPUT_STATES[user_id] = {"action": "waiting_global_prompt"}
        await event.edit("""⚙️ **تخصيص تعليمات الذكاء الاصطناعي:**
أرسل أسلوب الصياغة المطلوب للمحرر الذكي (مثال: `اجعل الأسلوب رسمياً وأكاديمياً ومباشراً للطلبة مع إبراز المواعيد`):""")


# ==============================================================================
# معالجة المدخلات النصية متعددة الخطوات (Login Flow & Config Steps)
# ==============================================================================
@bot.on(events.NewMessage)
async def message_input_dispatcher(event):
    if event.text.startswith("/"):
        return

    user_id = event.sender_id
    text = event.text.strip()

    # 1. تدفق تسجيل الدخول (OTP / Password)
    if user_id in AUTH_STATES:
        state = AUTH_STATES[user_id]
        step = state.get("step")

        # إدخال رمز OTP
        if step == "waiting_code":
            clean_code = text.replace(" ", "").replace("-", "")
            temp_client: TelegramClient = state["client"]
            phone = state["phone"]
            phone_code_hash = state["phone_code_hash"]

            try:
                await temp_client.sign_in(phone, clean_code, phone_code_hash=phone_code_hash)

                # إذا نجح تسجيل الدخول، نستخرج الجلسة النصية
                session_str = temp_client.session.save()
                db.update_user_session(user_id, session_str, phone=phone)
                del AUTH_STATES[user_id]
                await temp_client.disconnect()

                success_msg = f"""🎉 **تم استخراج الجلسة وربط حسابك بنجاح!**
📱 الرقم: `{phone}`
🔒 تم تخزين الجلسة النصية (StringSession) بأمان في قاعدة البيانات.
🚀 عامل الزحف في الخلفية أصبح قادراً الآن على قراءة القنوات نيابة عنك والنشر في قناتك!"""
                await event.respond(success_msg, buttons=get_main_keyboard(True))
                return

            except SessionPasswordNeededError:
                state["step"] = "waiting_password"
                await event.respond("🔐 **حسابك محمي بالتحقق بخطوتين (2FA Password):**\nيرجى إرسال كلمة مرور حسابك الآن:")
                return

            except PhoneCodeInvalidError:
                await event.respond("❌ رمز التحقق غير صحيح! يرجى إعادة إرسال الرمز بشكل صحيح:")
                return

            except PhoneCodeExpiredError:
                await temp_client.disconnect()
                del AUTH_STATES[user_id]
                await event.respond("⚠️ انتهت صلاحية هذا الرمز. اضغط على زر تسجيل الدخول للبدء من جديد.", buttons=get_main_keyboard(False))
                return

            except Exception as e:
                await temp_client.disconnect()
                del AUTH_STATES[user_id]
                await event.respond(f"❌ حدث خطأ أثناء التحقق: {e}", buttons=get_main_keyboard(False))
                return

        # إدخال كلمة مرور 2FA
        elif step == "waiting_password":
            temp_client: TelegramClient = state["client"]
            phone = state["phone"]

            try:
                await temp_client.sign_in(password=text)
                session_str = temp_client.session.save()
                db.update_user_session(user_id, session_str, phone=phone)
                del AUTH_STATES[user_id]
                await temp_client.disconnect()

                success_msg = f"""🎉 **تم توثيق كلمة المرور وربط الحساب بنجاح!**
📱 الرقم: `{phone}`
🚀 البوت جاهز الآن للبدء بالنشر والزحف الذكي."""
                await event.respond(success_msg, buttons=get_main_keyboard(True))
                return

            except PasswordHashInvalidError:
                await event.respond("❌ كلمة المرور غير صحيحة! يرجى إرسالها مرة أخرى:")
                return

            except Exception as e:
                await temp_client.disconnect()
                del AUTH_STATES[user_id]
                await event.respond(f"❌ حدث خطأ في التحقق من كلمة المرور: {e}", buttons=get_main_keyboard(False))
                return

    # 2. حالات إدخال البيانات الأخرى (الحملات، القنوات، الإعلانات)
    if user_id in INPUT_STATES:
        state = INPUT_STATES.pop(user_id)
        action = state.get("action")

        # إرسال رقم الهاتف لبدء التسجيل
        if action == "waiting_phone":
            phone_match = re.sub(r'[\s\-\(\)]', '', text)
            if not phone_match.startswith("+"):
                phone_match = "+" + phone_match

            await event.respond("⏳ جاري الاتصال بخوادم تيليجرام لطلب رمز التحقق...")

            temp_client = TelegramClient(StringSession(), API_ID, API_HASH)
            try:
                await temp_client.connect()
                send_code_res = await temp_client.send_code_request(phone_match)

                AUTH_STATES[user_id] = {
                    "step": "waiting_code",
                    "phone": phone_match,
                    "client": temp_client,
                    "phone_code_hash": send_code_res.phone_code_hash
                }

                await event.respond(f"""📩 **تم إرسال رمز التحقق (OTP) إلى حسابك على تيليجرام!**
الرقم: `{phone_match}`

يرجى إرسال رمز التحقق الآن في هذه المحادثة:""")
                return

            except PhoneNumberInvalidError:
                await temp_client.disconnect()
                await event.respond("❌ رقم الهاتف غير صالح! تأكد من كتابة الرمز الدولي بشكل صحيح (مثال: `+966500000000`).", buttons=get_main_keyboard(False))
                return
            except Exception as e:
                await temp_client.disconnect()
                await event.respond(f"❌ تعذر إرسال الرمز: {e}", buttons=get_main_keyboard(False))
                return

        # إدخال الجلسة يدوياً
        elif action == "waiting_manual_session":
            if len(text) > 20:
                db.update_user_session(user_id, text)
                await event.respond("🎉 تم حفظ الجلسة النصية بنجاح! حسابك جاهز الآن.", buttons=get_main_keyboard(True))
            else:
                await event.respond("❌ كود الجلسة غير صالح أو قصير جداً.", buttons=get_main_keyboard(False))
            return

        # إنشاء حملة جديدة - خطوة 1: الاسم
        elif action == "waiting_campaign_name":
            INPUT_STATES[user_id] = {"action": "waiting_campaign_target", "name": text}
            await event.respond(f"""📢 **خطوة 2 من 2 للحملة [{text}]:**
أرسل الآن معرّف أو رابط **قناة النشر الهدف** التي تريد أن ينشر البوت فيها المنشورات الجديدة:
(مثال: `@MyUniversityChannel` أو `-100123456789`)""")
            return

        # إنشاء حملة جديدة - خطوة 2: قناة الهدف
        elif action == "waiting_campaign_target":
            camp_name = state.get("name", "حملة جديدة")
            target_ch = text.strip()
            camp_id = db.create_campaign(user_id, camp_name, target_ch)
            await event.respond(f"""🎉 **تم إنشاء الحملة بنجاح!**
🏷 الاسم: **{camp_name}**
📢 القناة الهدف: `{target_ch}`

يمكنك الآن إضافة القنوات المصدرية التي تريد مراقبتها من زر إدارة الحملات.""", buttons=get_main_keyboard(True))
            return

        # إضافة قناة مصدرية لحملة
        elif action == "waiting_source_channel":
            camp_id = state.get("campaign_id")
            source_target = text.strip()
            db.add_source(camp_id, user_id, source_target, title=source_target)
            await event.respond(f"""✅ **تمت إضافة المصدر بنجاح!**
📥 المصدر: `{source_target}`
سيقوم عامل الزحف بمراقبة المنشورات الجديدة فقط فور نزولها.""", buttons=get_main_keyboard(True))
            return

        # تحديث إعلان الخدمات الطلابية
        elif action == "waiting_global_ad":
            campaigns = db.get_user_campaigns(user_id)
            for c in campaigns:
                db.update_campaign(c["id"], custom_ad=text)
            await event.respond("✅ تم حفظ وتحديث إعلان خدماتك الطلابية لجميع حملاتك بنجاح!", buttons=get_main_keyboard(True))
            return

        # تحديث تعليمات المشرف للذكاء الاصطناعي
        elif action == "waiting_global_prompt":
            campaigns = db.get_user_campaigns(user_id)
            for c in campaigns:
                db.update_campaign(c["id"], custom_instruction=text)
            await event.respond("✅ تم حفظ وتحديث تعليمات الذكاء الاصطناعي بنجاح!", buttons=get_main_keyboard(True))
            return


# ==============================================================================
# دمج وتشغيل خادم البوت وعامل الزحف معاً (All-in-One Engine for Free Hosts)
# ==============================================================================
async def start_combined_app():
    """تشغيل البوت وعامل الزحف والخادم معاً لدعم الاستضافات المجانية الفردية"""
    # 1. تهيئة قاعدة البيانات
    db.init_db()

    # 2. تشغيل خادم Keep-Alive في خيط مستقل
    http_thread = threading.Thread(target=run_keepalive_http, daemon=True)
    http_thread.start()

    # 3. تشغيل عامل الزحف كـ Background Task داخل نفس حلقة الأحداث (Asyncio)
    import worker
    asyncio.create_task(worker.worker_main_loop())

    # 4. تشغيل عميل التيليجرام بوت
    logging.info("🚀 جاري بدء تشغيل البوت الأساسي عبر Telethon...")
    await bot.start(bot_token=BOT_TOKEN)
    bot_me = await bot.get_me()
    logging.info(f"✅ البوت يعمل بنجاح باسم: @{bot_me.username} ({bot_me.first_name})")

    # إبقاء البوت مستمراً
    await bot.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(start_combined_app())
    except KeyboardInterrupt:
        logging.info("🛑 تم إيقاف البوت يدوياً.")
