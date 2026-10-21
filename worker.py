#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
المرحلة الثانية: مهمة الزحف والنشر في الخلفية (Background Crawler Task)
باستخدام جلسة المستخدم المستقلة (Pyrogram session_string)
================================================================================
الوظيفة:
1. قراءة جلسة المستخدم (session_string) من قاعدة البيانات database/data.db.
2. تشغيل عميل Pyrogram باستخدام جلسة المستخدم الخاصة حصراً (وليس جلسة الأدمن):
   app = Client("::memory::", session_string=session_string)
3. جلب آخر رسائل من قناة المصدر (app.get_chat_history(source_channel, limit=10)).
4. التحقق من الكلمات المفتاحية وتفادي تكرار الرسائل المعالجة مسبقاً.
5. إرسال النص للذكاء الاصطناعي (DeepSeek) لإعادة الصياغة كمنشور أصلي وحصري.
6. إذا كان رد الذكاء الاصطناعي SKIP، يتم تخطي الرسالة ومسحها فوراً.
7. استبدال إعلانات المنافسين بإعلان المستخدم في حال اكتشاف إعلان.
8. النشر في قناة الهدف باستخدام جلسة المستخدم (await app.send_message).
9. حفظ معرف الرسالة لمنع تكرار النشر.
================================================================================
"""

import os
import sys
import re
import time
import json
import sqlite3
import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiohttp

# استيراد طبقة قاعدة البيانات
import database as db

# استيراد Pyrogram
try:
    from pyrogram import Client
    from pyrogram.errors import (
        FloodWait,
        ChannelPrivate,
        ChatAdminRequired,
        UserDeactivatedBan,
        AuthKeyUnregistered
    )
except ImportError:
    print("⚠️ مكتبة Pyrogram غير مثبتة. يرجى تثبيتها عبر: pip install pyrogram tgcrypto")

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "data.db")

# الإعدادات ومفاتيح تيليجرام
API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")

# إعدادات الذكاء الاصطناعي
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.hcnsec.cn/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "sk-J2ky44F6VTDMkL8Q1GHL5sfmbeIpARVDayNuwMfxKI5zCdii").strip()
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "DeepSeek-V4.1-Flash").strip()
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "auto").strip()

# فترة التهدئة بين دورات الزحف (بالثواني)
CRAWL_INTERVAL = int(os.getenv("CRAWL_INTERVAL_SECONDS", "15"))

# الكلمات الدالة على إعلانات المنافسين
COMPETITOR_AD_KEYWORDS = [
    "إعلان مدفوع", "ترويج لخدمات طلابية", "حل واجبات", "بحوث تخرج",
    "خدمات طلابية", "مشاريع تخرج", "كتابة أبحاث", "إعلان ممول",
    "برعاية", "للتواصل والإعلان", "سعر رمزي"
]

DEFAULT_PROMPT = """# الدور: محرر وكاتب محتوى تعليمي وجامعي حصري
## المهمة:
أعد صياغة هذا المحتوى الأكاديمي كمنشور أصلي ورسمي لقناتك (بدون ذكر أي مصادر أو قنوات سابقة).

## قواعد صارمة:
1. إذا كان المنشور غير ملائم أو تافهاً أو إعلاناً عشوائياً، أجب فقط بكلمة: SKIP
2. احذف نهائياً أي روابط أو معرفات قنوات تيليجرام (@channel أو t.me).
3. لا تستخدم عبارات النقل مثل (وفقاً للمصدر، نقلاً عن).
4. حافظ بدقة تامة على الأرقام، النسب، التواريخ، والمواعيد الرسمية، والشروط.
5. احتفظ فقط بالروابط الحكومية والجامعية الرسمية المباشرة.

## التنسيق المطلوب:
📌 [عنوان بارز وجذاب]
• [المحتوى في نقاط محددة وسهلة القراءة]
💬 [دعوة تفاعلية قصيرة للطلاب]
[2 إلى 4 هاشتاجات ملائمة: #جامعة #قبول #تسجيل #دراسة]"""


def is_competitor_ad(text: str) -> bool:
    """التحقق مما إذا كان النص إعلاناً لمنافسين"""
    if not text:
        return False
    return any(kw in text for kw in COMPETITOR_AD_KEYWORDS)


def clean_text_sources(text: str) -> str:
    """إزالة أي روابط لقنوات أو معرفات خارجية"""
    cleaned = re.sub(r'@[a-zA-Z0-9_]+', '', text)
    cleaned = re.sub(r'https?://t\.me/[^\s]+', '', cleaned)
    cleaned = re.sub(r'(وفقاً لـ?|بحسب|نقلاً عن|المصدر:|قناة|حساب)\s+[^\s\n]+', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned


async def call_ai_rephrase(raw_text: str, custom_instruction: str = "") -> Optional[str]:
    """
    إرسال النص إلى API الذكاء الاصطناعي لإعادة الصياغة.
    يعيد SKIP للتخطي، أو النص المعاد صياغته.
    """
    clean_input = clean_text_sources(raw_text)
    if not clean_input or len(clean_input.strip()) < 15:
        return None

    instruction_addon = f"\n\nتعليمات إضافية خاصة بالمشرف:\n{custom_instruction}" if custom_instruction else ""
    user_prompt = f"المنشور الأصلي المطلوب معالجته:\n{clean_input}{instruction_addon}"

    payload = {
        "model": PRIMARY_MODEL,
        "messages": [
            {"role": "system", "content": DEFAULT_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.35,
        "max_tokens": 800
    }

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{AI_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if "SKIP" in ai_reply[:10].upper():
                        return "SKIP"
                    return clean_text_sources(ai_reply)
        except Exception as e:
            logging.warning(f"تعذر الرد من النموذج الأساسي {PRIMARY_MODEL}: {e}")

        if FALLBACK_MODEL and FALLBACK_MODEL != "auto":
            try:
                payload["model"] = FALLBACK_MODEL
                async with session.post(f"{AI_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        ai_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if "SKIP" in ai_reply[:10].upper():
                            return "SKIP"
                        return clean_text_sources(ai_reply)
            except Exception as e:
                logging.warning(f"تعذر الرد من النموذج البديل {FALLBACK_MODEL}: {e}")

    # بديل محلي سريع وذكي في حال تعذر البوابة
    lines = [l.strip() for l in clean_input.split("\n") if l.strip() and not l.startswith("http")]
    title = lines[0] if lines else "تحديث جامعي وأكاديمي هام"
    bullets = "\n".join([f"• {l}" for l in lines[1:6]]) if len(lines) > 1 else f"• {clean_input}"
    return f"📌 **{title}**\n\n{bullets}\n\n💬 يسعدنا استقبال استفساراتكم ومشاركة المنشور مع زملائكم الطلاب!\n\n#جامعة #أخبار_التعليم #شؤون_الطلاب"


# ==============================================================================
# 3. دالة الزحف والنشر باستخدام جلسة المستخدم (الكود الأساسي المطلوب بدقة)
# ==============================================================================
async def crawl_and_publish(user_id: int, source_channel: str, target_channel: str, keywords: List[str],
                            campaign_id: str = "default", custom_ad: str = "", custom_instruction: str = ""):
    """
    المرحلة الثانية: الزحف والنشر باستخدام جلسة المستخدم الخاصة حصراً:
    1. قراءة الجلسة من قاعدة البيانات database/data.db.
    2. تشغيل عميل باستخدام جلسة المستخدم: app = Client("::memory::", session_string=session_string)
    3. جلب آخر 10 رسائل من قناة المصدر (get_chat_history).
    4. التحقق من الكلمات المفتاحية ومنع التكرار.
    5. تمرير النص للذكاء الاصطناعي (مع دعم SKIP واستبدال إعلانات المنافسين).
    6. النشر في قناة الهدف باستخدام جلسة المستخدم (send_message / media).
    """
    # 1. قراءة الجلسة من قاعدة البيانات
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT session FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        print(f"لا توجد جلسة للمستخدم {user_id}")
        return

    session_string = result[0]

    # 2. تشغيل عميل باستخدام جلسة المستخدم (وليس جلسة الأدمن)
    app = Client(
        "::memory::",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True
    )

    try:
        async with app:
            logging.info(f"🔍 [User: {user_id}] فحص القناة المصدر: {source_channel} -> الهدف: {target_channel}")

            # جلب آخر 10 رسائل من قناة المصدر
            try:
                chat_messages = []
                async for message in app.get_chat_history(source_channel, limit=10):
                    chat_messages.append(message)
            except Exception as e:
                logging.error(f"❌ تعذر الوصول للقناة المصدر {source_channel}: {e}")
                return

            # معالجة الرسائل من الأقدم للأحدث
            chat_messages.reverse()

            for message in chat_messages:
                msg_id = message.id
                msg_text = message.text or message.caption or ""

                if not msg_text:
                    continue

                # التحقق مما إذا كانت الرسالة عولجت مسبقاً لمنع التكرار
                if db.is_message_processed(user_id, source_channel, msg_id, msg_text):
                    continue

                # تحقق من الكلمات المفتاحية (إن حدد المستخدم كلمات)
                if keywords and len(keywords) > 0:
                    if not any(word.strip() in msg_text for word in keywords if word.strip()):
                        continue

                # فحص إعلانات المنافسين: استبدال بإعلان المستخدم المخصص
                is_ad = is_competitor_ad(msg_text)
                final_text = ""
                action_status = "forwarded"

                if is_ad and custom_ad:
                    final_text = custom_ad
                    action_status = "ad_replaced"
                    logging.info(f"🎯 تم رصد إعلان منافس في الرسالة {msg_id} - استبدال بإعلانك!")
                else:
                    # تمرير النص للذكاء الاصطناعي لإعادة الصياغة
                    rephrased_text = await call_ai_rephrase(msg_text, custom_instruction)

                    # فحص رد SKIP
                    if rephrased_text == "SKIP" or not rephrased_text:
                        logging.info(f"⏩ تخطي الرسالة {msg_id} لعدم الأهمية بقرار الذكاء (SKIP)")
                        db.add_log(user_id, campaign_id, source_channel, target_channel, msg_id, msg_text, "", "skipped", "ai_skip")
                        continue

                    final_text = rephrased_text

                # النشر في قناة الهدف باستخدام جلسة المستخدم
                try:
                    if message.photo:
                        # نشر مع الصورة الأصلية بدقة عالية
                        await app.send_photo(target_channel, message.photo.file_id, caption=final_text)
                    elif message.document:
                        # نشر مع ملف PDF أو المستند
                        await app.send_document(target_channel, message.document.file_id, caption=final_text)
                    else:
                        # نشر نصي فقط
                        await app.send_message(target_channel, final_text)

                    print(f"✅ تم النشر في {target_channel} باسم جلسة المستخدم {user_id}")
                    db.mark_message_processed(user_id, source_channel, msg_id, msg_text)
                    db.add_log(user_id, campaign_id, source_channel, target_channel, msg_id, msg_text, final_text, action_status, "success")

                    # تأخير قصير لتجنب قيود تيليجرام
                    await asyncio.sleep(2)

                except FloodWait as fw:
                    logging.warning(f"⏳ تيليجرام يطلب الانتظار {fw.value} ثانية (FloodWait)...")
                    await asyncio.sleep(min(fw.value, 60))
                except Exception as pub_err:
                    logging.error(f"❌ خطأ أثناء النشر في {target_channel}: {pub_err}")
                    db.add_log(user_id, campaign_id, source_channel, target_channel, msg_id, msg_text, final_text, "error", str(pub_err))

    except (UserDeactivatedBan, AuthKeyUnregistered):
        logging.error(f"❌ جلسة المستخدم {user_id} أصبحت ملغاة أو منتهية.")
        db.delete_user_session(user_id)
    except Exception as e:
        logging.error(f"❌ خطأ في تشغيل جلسة المستخدم {user_id}: {e}")


# ==============================================================================
# الحلقة الخلفية الدائمة لعامل الزحف (Background Task Loop)
# ==============================================================================
async def worker_task_loop():
    """
    المهمة الخلفية المستمرة:
    تفحص بانتظام قاعدة البيانات database/data.db،
    وتستدعي crawl_and_publish لكل مستخدم وحملة وقناة مراقبة بجلسة حسابه المستقلة.
    """
    logging.info("🚀 تشغيل المهمة الخلفية للزحف والنشر بجلسات المستخدمين...")
    db.init_db()

    while True:
        try:
            active_campaigns = db.get_all_active_campaigns()
            for camp in active_campaigns:
                user_id = camp["user_id"]
                target_channel = camp["target_channel"].strip()
                keywords = camp.get("keywords") or []
                custom_ad = camp.get("custom_ad") or ""
                custom_instruction = camp.get("custom_instruction") or ""

                sources = camp.get("sources") or []
                for s in sources:
                    if not s.get("enabled"):
                        continue
                    source_target = s["target"].strip()
                    await crawl_and_publish(
                        user_id=user_id,
                        source_channel=source_target,
                        target_channel=target_channel,
                        keywords=keywords,
                        campaign_id=camp["id"],
                        custom_ad=custom_ad,
                        custom_instruction=custom_instruction
                    )

        except Exception as loop_err:
            logging.error(f"❌ خطأ غير متوقع في دورة الزحف: {loop_err}")

        await asyncio.sleep(CRAWL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(worker_task_loop())
    except KeyboardInterrupt:
        logging.info("🛑 تم إيقاف عامل الزحف يدوياً.")
