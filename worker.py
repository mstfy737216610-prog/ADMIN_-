#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
عامل الزحف والنشر الذكي في الخلفية (Background Crawler & AI Publisher Engine)
================================================================================
الوظيفة:
1. يعمل كـ Background Worker مستمر في حلقة (Loop).
2. يقرأ الحملات والمصادر النشطة من database.py.
3. يفتح اتصال Telethon لكل مستخدم بجلسته الخاصة (Session String) حصراً.
   (تنبيه أمني صارم: لا يتم استخدام جلسة الآدمن أبداً لعمليات المستخدمين).
4. يجلب الرسائل الجديدة فقط (Message ID > last_processed_id).
5. يمرر الرسالة للذكاء الاصطناعي (DeepSeek) لإعادة الصياغة.
6. إذا كان رد الذكاء الاصطناعي SKIP، يتم تجاهل المنشور ومسحه من الذاكرة.
7. يستبدل إعلانات المنافسين بإعلان المستخدم في حال اكتشاف إعلان.
8. ينشر الرسالة في القناة الهدف باسم حساب المستخدم نفسه.
9. يحدث last_processed_id في قاعدة بيانات SQLite لمنع أي تكرار.
"""

import os
import sys
import re
import time
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
import aiohttp

# استيراد دوال قاعدة البيانات
import database as db

# استيراد مكتبة Telethon
try:
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    from telethon.errors import (
        FloodWaitError,
        ChannelPrivateError,
        ChatAdminRequiredError,
        UserDeactivatedBanError,
        AuthKeyUnregisteredError
    )
except ImportError:
    print("❌ مكتبة Telethon غير مثبتة! يرجى تثبيتها عبر: pip install telethon aiohttp")
    sys.exit(1)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# الإعدادات العامة ومفاتيح API لتيليجرام
API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")

# إعدادات الذكاء الاصطناعي الافتراضية
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.hcnsec.cn/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "sk-J2ky44F6VTDMkL8Q1GHL5sfmbeIpARVDayNuwMfxKI5zCdii").strip()
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "DeepSeek-V4.1-Flash").strip()
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "auto").strip()

# فترة التهدئة بين دورات الزحف (بالثواني)
CRAWL_INTERVAL = int(os.getenv("CRAWL_INTERVAL_SECONDS", "15"))

# الكلمات المفتاحية الدالة على إعلانات المنافسين
COMPETITOR_AD_KEYWORDS = [
    "إعلان مدفوع", "ترويج لخدمات طلابية", "حل واجبات", "بحوث تخرج",
    "خدمات طلابية", "مشاريع تخرج", "كتابة أبحاث", "إعلان ممول",
    "برعاية", "للتواصل والإعلان", "سعر رمزي", "خصم خاص للطلاب"
]

DEFAULT_PROMPT = """# الدور: محرر وكاتب محتوى تعليمي وجامعي حصري
## المهمة:
أعد صياغة المنشور الأكاديمي التالي ليكون منشوراً أصيلاً وجذاباً للطلاب، كأنك أنت الناشر والمصدر الأول.

## القواعد الصارمة:
1. إذا كان المنشور غير مفيد أو تافهاً أو إعلاناً عشوائياً لا قيمة له، أجب فقط بكلمة: SKIP
2. احذف نهائياً أي ذكر لأسماء القنوات الأصلية أو روابط تيليجرام (@channel أو t.me).
3. لا تستخدم عبارات مثل (وفقاً للمصدر، نقلاً عن، صرحت القناة).
4. حافظ بدقة تامة على الأرقام، النسب، التواريخ، والمواعيد الرسمية، والشروط.
5. احتفظ فقط بالروابط الحكومية والجامعية الرسمية المباشرة.

## التنسيق المطلوب:
📌 [عنوان بارز وجذاب]
• [المحتوى في نقاط محددة وسهلة القراءة]
💬 [دعوة تفاعلية قصيرة للطلاب]
[2 إلى 4 هاشتاجات ملائمة: #جامعة #قبول #تسجيل #دراسة]"""


def is_ad_text(text: str) -> bool:
    """التحقق مما إذا كان النص يحتوي على إعلان منافسين"""
    if not text:
        return False
    return any(kw in text for kw in COMPETITOR_AD_KEYWORDS)


def clean_text_sources(text: str) -> str:
    """إزالة أي روابط لقنوات تيليجرام أو أسماء معرفات"""
    cleaned = re.sub(r'@[a-zA-Z0-9_]+', '', text)
    cleaned = re.sub(r'https?://t\.me/[^\s]+', '', cleaned)
    cleaned = re.sub(r'(وفقاً لـ?|بحسب|نقلاً عن|المصدر:|قناة|حساب)\s+[^\s\n]+', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned


async def call_ai_rephrase(raw_text: str, custom_instruction: str = "") -> Optional[str]:
    """
    إرسال النص إلى API الذكاء الاصطناعي لإعادة الصياغة.
    يعيد None أو SKIP إذا كان المنشور غير ملائم، أو النص الجديد المعاد صياغته.
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
        # المحاولة الأولى مع النموذج الأساسي
        try:
            async with session.post(f"{AI_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if "SKIP" in ai_reply[:10].upper():
                        return "SKIP"
                    return clean_text_sources(ai_reply)
        except Exception as e:
            logging.warning(f"تعذر الاستجابة من النموذج الأساسي {PRIMARY_MODEL}: {e}")

        # المحاولة الثانية مع النموذج البديل إن وجد
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
                logging.warning(f"تعذر الاستجابة من النموذج البديل {FALLBACK_MODEL}: {e}")

    # صياغة بديلة محلية ذكية في حال انقطاع بوابة الذكاء الاصطناعي
    lines = [l.strip() for l in clean_input.split("\n") if l.strip() and not l.startswith("http")]
    title = lines[0] if lines else "تحديث جامعي هام"
    bullets = "\n".join([f"• {l}" for l in lines[1:6]]) if len(lines) > 1 else f"• {clean_input}"
    return f"📌 **{title}**\n\n{bullets}\n\n💬 يسعدنا استقبال استفساراتكم ومشاركة المنشور مع زملائكم!\n\n#جامعة #أخبار_التعليم #شؤون_الطلاب"


async def process_source_for_user(client: TelegramClient, user_info: Dict[str, Any],
                                  campaign: Dict[str, Any], source: Dict[str, Any]):
    """
    معالجة مصدر محدد لحساب مستخدم معين:
    - يجلب فقط الرسائل الجديدة (ID > last_processed_id)
    - يفحص الكلمات المحظورة والمفتاحية
    - يمرر للذكاء الاصطناعي
    - ينشر في القناة الهدف بجلسة المستخدم
    """
    user_id = user_info["user_id"]
    campaign_id = campaign["id"]
    source_id = source["id"]
    source_target = source["target"].strip()
    target_channel = campaign["target_channel"].strip()
    last_id = int(source.get("last_processed_id") or 0)

    keywords = campaign.get("keywords") or []
    blacklist = campaign.get("blacklist") or []
    custom_instruction = campaign.get("custom_instruction") or ""
    custom_ad = campaign.get("custom_ad") or ""

    logging.info(f"🔍 فحص المصدر [{source_target}] لحملة [{campaign['name']}] (آخر معرف رسالة: {last_id})")

    try:
        # جلب الكيان (Entity) للقناة المصدرية
        source_entity = await client.get_entity(source_target)
    except Exception as e:
        logging.error(f"❌ تعذر الوصول للقناة المصدر [{source_target}]: {e}")
        return

    try:
        # جلب الرسائل التي تحمل ID أكبر من آخر ID تم حفظه (من الأقدم للأحدث بالترتيب)
        # نحدد limit=10 لتفادي الحمل الزائد
        messages = await client.get_messages(source_entity, min_id=last_id, limit=10, reverse=True)
    except Exception as e:
        logging.error(f"❌ خطأ أثناء جلب الرسائل من [{source_target}]: {e}")
        return

    if not messages:
        return

    for msg in messages:
        if not msg:
            continue

        msg_id = msg.id
        raw_text = msg.text or msg.message or ""

        # تحديث آخر ID تمت معالجته فوراً في قاعدة البيانات لمنع التكرار
        db.update_source_last_id(source_id, msg_id)

        # التحقق مما إذا تمت معالجة هذه الرسالة سابقاً
        if db.is_message_processed(user_id, source_target, msg_id, raw_text):
            logging.info(f"⏭ تم تخطي رسالة معالجة مسبقاً (ID: {msg_id})")
            continue

        # فحص القائمة السوداء (Blacklist)
        if blacklist and any(bad_word.strip() in raw_text for bad_word in blacklist if bad_word.strip()):
            logging.info(f"🛑 تم استبعاد الرسالة {msg_id} لاحتوائها على كلمة محظورة")
            db.add_log(user_id, campaign_id, source_target, target_channel, msg_id, raw_text, "", "skipped", "blacklist_filtered")
            continue

        # فحص الكلمات المفتاحية المطلوبة (Keywords) إن تم تحديدها
        if keywords and len(keywords) > 0:
            if not any(kw.strip() in raw_text for kw in keywords if kw.strip()):
                logging.info(f"⏭ تم تخطي الرسالة {msg_id} لعدم احتوائها على الكلمات المفتاحية المحددة")
                continue

        # فحص إعلانات المنافسين: استبدال بإعلان المستخدم الخاص إن وجد
        is_competitor = is_ad_text(raw_text)
        final_text = ""
        action_status = "forwarded"

        if is_competitor and custom_ad:
            final_text = custom_ad
            action_status = "ad_replaced"
            logging.info(f"🎯 تم رصد إعلان منافس في الرسالة {msg_id} - سيتم استبداله بإعلانك الخاص!")
        elif raw_text:
            # تمرير النص للذكاء الاصطناعي
            ai_result = await call_ai_rephrase(raw_text, custom_instruction)
            if ai_result == "SKIP" or not ai_result:
                logging.info(f"⏩ تخطي الرسالة {msg_id} بناءً على قرار الذكاء الاصطناعي (SKIP)")
                db.add_log(user_id, campaign_id, source_target, target_channel, msg_id, raw_text, "", "skipped", "ai_skip")
                continue
            final_text = ai_result

        # النشر في القناة الهدف بجلسة المستخدم
        try:
            target_entity = await client.get_entity(target_channel)

            if msg.media and not is_competitor:
                # إذا كانت الرسالة تحتوي على وسائط (صورة، ملف PDF، مستند)
                await client.send_file(
                    target_entity,
                    msg.media,
                    caption=final_text if len(final_text) <= 1024 else "",
                    parse_mode="md"
                )
                if len(final_text) > 1024:
                    await client.send_message(target_entity, final_text, parse_mode="md")
            else:
                # نشر نصي فقط
                if final_text:
                    await client.send_message(target_entity, final_text, parse_mode="md")

            # تسجيل العملية وحفظ بصمة الهاش
            db.mark_message_processed(user_id, source_target, msg_id, raw_text)
            db.add_log(user_id, campaign_id, source_target, target_channel, msg_id, raw_text, final_text, action_status, "success")
            logging.info(f"✅ تم النشر بنجاح في [{target_channel}] من الرسالة {msg_id} (الحالة: {action_status})")

            # تهدئة قصيرة بين المنشورات لتجنب FloodWait
            await asyncio.sleep(3)

        except FloodWaitError as e:
            logging.warning(f"⏳ تيليجرام يطلب الانتظار {e.seconds} ثانية (FloodWait)...")
            await asyncio.sleep(min(e.seconds, 60))
        except Exception as e:
            logging.error(f"❌ خطأ أثناء النشر في القناة الهدف [{target_channel}]: {e}")
            db.add_log(user_id, campaign_id, source_target, target_channel, msg_id, raw_text, final_text, "error", str(e))


async def run_worker_cycle():
    """دورة زحف واحدة تفحص جميع الحملات والمستخدمين النشطين"""
    active_campaigns = db.get_all_active_campaigns()
    if not active_campaigns:
        return

    # تجميع الحملات حسب المستخدم لتفادي فتح اتصالات متعددة لنفس الحساب
    user_campaigns_map: Dict[int, List[Dict[str, Any]]] = {}
    for camp in active_campaigns:
        uid = camp["user_id"]
        user_campaigns_map.setdefault(uid, []).append(camp)

    for user_id, campaigns in user_campaigns_map.items():
        session_str = campaigns[0].get("session_string", "")
        if not session_str or len(session_str) < 15:
            continue

        user_info = db.get_user(user_id)
        if not user_info or not user_info.get("is_active"):
            continue

        client = None
        try:
            # فتح اتصال بجلسة المستخدم الخاصة حصراً
            client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                logging.warning(f"⚠️ جلسة المستخدم {user_id} غير مصرح بها أو منتهية الصلاحية.")
                continue

            for campaign in campaigns:
                sources = campaign.get("sources") or []
                for source in sources:
                    if not source.get("enabled"):
                        continue
                    await process_source_for_user(client, user_info, campaign, source)

        except (UserDeactivatedBanError, AuthKeyUnregisteredError):
            logging.error(f"❌ جلسة المستخدم {user_id} أصبحت ملغاة أو محذوفة.")
            db.delete_user_session(user_id)
        except Exception as e:
            logging.error(f"❌ خطأ في معالجة حملات المستخدم {user_id}: {e}")
        finally:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass


async def worker_main_loop():
    """الحلقة اللانهائية لعامل الزحف"""
    logging.info("🚀 بدء تشغيل عامل الزحف الذكي (Smart Worker Engine)...")
    logging.info(f"⏱ فترة التهدئة بين الدورات: {CRAWL_INTERVAL} ثوانٍ")

    # تهيئة قاعدة البيانات
    db.init_db()

    while True:
        try:
            await run_worker_cycle()
        except Exception as e:
            logging.error(f"❌ خطأ غير متوقع في دورة الزحف: {e}")

        await asyncio.sleep(CRAWL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(worker_main_loop())
    except KeyboardInterrupt:
        logging.info("🛑 تم إيقاف عامل الزحف يدوياً.")
