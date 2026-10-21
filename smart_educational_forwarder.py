#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
محرر المحتوى التعليمي الجامعي الذكي ومُعيد التوجيه التلقائي
Smart University Educational Content Editor & Multi-Source Auto-Forwarder
================================================================================
المطور الأصلي للأداة الأساسية: Redian Marku (https://github.com/redianmarku/Telegram-Autoforwarder)
الترخيص: رخصة معهد ماساتشوستس للتكنولوجيا (MIT License) - جميع الحقوق محفوظة للمطور الأصلي

التطوير والتعريب والذكاء الاصطناعي:
- بوت تيليجرام: @admiuin_bot (Token: 8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4)
- الآدمن المسؤول: @M_S_F_G (User ID: 7607633343)
- مزود الذكاء الاصطناعي: DeepSeek-V4.1-Flash (عبر https://api.hcnsec.cn/v1)
- استبدال إعلانات المنافسين بإعلانات خدمات طلابية مخصصة
- مراقبة متعددة: تيليجرام، حسابات تويتر/X، وتغذيات RSS
- دعم تحميل ونشر ملفات الكتب الجامعية بصيغة PDF والوسائط
================================================================================
"""

import os
import sys
import json
import time
import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
import aiohttp
from datetime import datetime

# ----------------- الإعدادات الرئيسية -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7607633343"))
ADMIN_USERNAME = "@M_S_F_G"

AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.hcnsec.cn/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "sk-J2ky44F6VTDMkL8Q1GHL5sfmbeIpARVDayNuwMfxKI5zCdii")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "DeepSeek-V4.1-Flash")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "auto")

# مسارات الملفات
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(CONFIG_DIR, "sources.json")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")
LOGS_FILE = os.path.join(CONFIG_DIR, "logs.json")

# إعداد التسجيل (Logging)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(CONFIG_DIR, "forwarder.log"), encoding="utf-8")
    ]
)

# ----------------- نصوص تعليمات النموذج والتحقق -----------------
SYSTEM_PROMPT_REPHRASE = """# الدور: محرر محتوى تعليمي جامعي

## الهوية
أنت محرر محتوى متخصص في الشؤون التعليمية الجامعية. مهمتك قراءة المنشورات من قنوات وحسابات جامعية وإعادة صياغتها بأسلوب أوضح وأدق، مع الحفاظ على المصداقية الكاملة مثل مشرفي مجموعات الطلاب المخلصين.

## المبادئ الأساسية
### 1. الدقة أولاً
- لا تضف أي معلومة غير موجودة في النص الأصلي
- لا تحذف أي معلومة جوهرية أو نسب مئوية أو مواعيد أو شروط
- لا تغيّر الأرقام أو المواعيد أو الأسماء
### 2. إعادة الصياغة
- أعد كتابة النص بأسلوبك الخاص (لا نسخ حرفي)
- حسّن التنسيق: عناوين، نقاط، فواصل واضحة
- اجعل اللغة أكاديمية لكن سهلة ومفهومة
- استخدم الإيموجي باعتدال (📚 🎓 📅 📌 💡)
### 3. التنسيق المطلوب إلزامي
كل منشور يجب أن يكون بالشكل:
- 📌 عنوان واضح
- محتوى منظم بنقاط
- 💬 دعوة للتفاعل
- هاشتاجات مناسبة (2-4 فقط)

### 4. قواعد صارمة
- الحفاظ على المعنى الأصلي كاملاً
- عدم ذكر المصدر لانه سيتم إعادة الصياغة
- رفض النشر إذا كان النص غير واضح

## تنسيق الإخراج
أعد النص الجاهز للنشر فقط، دون أي شرح أو تعليق إضافي."""

SYSTEM_PROMPT_VERIFY = """# الدور: مدقق معلومات تعليمية

## المهمة
تحقق من صحة المعلومات التالية عبر البحث في الإنترنت:
- أرقام وإحصاءات
- مواعيد ونتائج
- أسماء جهات أو جامعات

## القواعد
- ابحث في مصادر موثوقة فقط (مواقع جامعات، القنوات الرسمية)
- إذا وجدت تأكيداً: أعد: VERIFIED
- إذا وجدت تناقضاً: أعد: CONTRADICTED مع التصحيح
- إذا لم تجد شيئاً: أعد: UNVERIFIED
لا تنشر أي معلومة مشبوهة."""

# إعلان الخدمات الطلابية الخاص بالآدمن (لاستبدال إعلانات المنافسين)
DEFAULT_CUSTOM_STUDENT_AD = """🎓 خدمات طلابية معتمدة وأكاديمية متكاملة 🎓
يسرنا تقديم الدعم الأكاديمي الشامل للطلبة والباحثين:
• مساعدة في البحوث والمشاريع الأكاديمية
• التدقيق اللغوي وتنسيق الرسائل الجامعية
• تلخيص المحاضرات والمقررات الدراسية
• استشارات القبول والتسجيل والتنسيق

📞 للتواصل والطلب مباشرة عبر المشرف: @M_S_F_G
✨ جودة أكاديمية، سرعة في الإنجاز، وأسعار مناسبة للطلاب!"""

AD_DETECTION_KEYWORDS = [
    "إعلان مدفوع", "ترويج لخدمات طلابية", "حل واجبات", "بحوث تخرج",
    "خدمات طلابية", "مشاريع تخرج", "كتابة أبحاث", "إعلان ممول", "برعاية"
]

class EducationalAutoForwarder:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.sources: Dict[str, Any] = self.load_sources()
        self.state: Dict[str, Any] = self.load_state()
        self.is_paused: bool = False
        self.custom_ad: str = DEFAULT_CUSTOM_STUDENT_AD
        self.custom_instructions: str = "كن مثل مشرفين القروبات الذي يبحث عن الأخبار الجديدة ويعطيها للطلاب"
        self.last_post_time: float = 0.0

    def load_sources(self) -> Dict[str, Any]:
        if os.path.exists(SOURCES_FILE):
            try:
                with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"خطأ في قراءة ملف المصادر sources.json: {e}")
        return {"sources": []}

    def save_sources(self):
        self.sources["lastUpdated"] = datetime.now().isoformat()
        with open(SOURCES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.sources, f, ensure_ascii=False, indent=2)

    def load_state(self) -> Dict[str, Any]:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"خطأ في قراءة ملف الحالة state.json: {e}")
        return {
            "processed_count": 0,
            "forwarded_count": 0,
            "ad_replaced_count": 0,
            "last_processed_ids": {}
        }

    def save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def log_event(self, event_type: str, source: str, raw: str, formatted: str, status: str):
        item = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": event_type,
            "source": source,
            "original": raw[:200],
            "formatted": formatted[:200],
            "status": status
        }
        logs = []
        if os.path.exists(LOGS_FILE):
            try:
                with open(LOGS_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                pass
        logs.insert(0, item)
        logs = logs[:500]  # الحفاظ على آخر 500 حدث
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    async def call_ai(self, messages: List[Dict[str, str]], model: str = PRIMARY_MODEL) -> str:
        """استدعاء خدمة الذكاء الاصطناعي مع معالجة الأخطاء والنموذج البديل"""
        url = f"{AI_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 800
        }

        try:
            async with self.session.post(url, json=payload, headers=headers, timeout=40) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    err_txt = await resp.text()
                    logging.warning(f"فشل النموذج {model} كود {resp.status}: {err_txt}")
        except Exception as e:
            logging.warning(f"استثناء أثناء استدعاء {model}: {e}")

        # محاولة النموذج البديل auto
        if model != FALLBACK_MODEL:
            logging.info(f"🔄 جاري التحويل تلقائياً للنموذج البديل: {FALLBACK_MODEL}")
            payload["model"] = FALLBACK_MODEL
            try:
                async with self.session.post(url, json=payload, headers=headers, timeout=40) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logging.error(f"فشل النموذج البديل أيضاً: {e}")

        # صياغة احتياطية محلية لضمان عدم توقف العمل
        return self.fallback_local_rephrase(messages[-1]["content"])

    def fallback_local_rephrase(self, raw_text: str) -> str:
        lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not l.startswith("http")]
        title = lines[0] if lines else "إعلان جامعي هام"
        bullets = "\n".join([f"• {l}" for l in lines[1:6]]) if len(lines) > 1 else f"• {raw_text}"
        return f"📌 {title}\n\n{bullets}\n\n💬 يسعدنا استقبال استفساراتكم ومشاركة المنشور مع زملائكم!\n\n#جامعة #أخبار_التعليم #شؤون_الطلاب"

    def is_competitor_ad(self, text: str) -> bool:
        """فحص ما إذا كان المنشور إعلاناً لمنافس لخدمات طلابية"""
        for kw in AD_DETECTION_KEYWORDS:
            if kw in text:
                return True
        return False

    async def verify_facts(self, text: str) -> str:
        """التحقق من الحقائق عبر البحث"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_VERIFY},
            {"role": "user", "content": text}
        ]
        return await self.call_ai(messages, model=PRIMARY_MODEL)

    async def rephrase_post(self, raw_text: str, custom_instruction: str = "") -> str:
        """إعادة صياغة المنشور وفق متطلبات المحرر الأكاديمي"""
        content = f"تعليمات المشرف: {custom_instruction}\n\nالنص الأصلي:\n{raw_text}" if custom_instruction else raw_text
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_REPHRASE},
            {"role": "user", "content": content}
        ]
        return await self.call_ai(messages, model=PRIMARY_MODEL)

    async def send_telegram_message(self, chat_id: Any, text: str, reply_markup: Optional[Dict] = None):
        """إرسال رسالة إلى تيليجرام مع احترام معدل الإرسال"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with self.session.post(url, json=payload) as resp:
            data = await resp.json()
            if not data.get("ok"):
                logging.error(f"خطأ تيليجرام: {data.get('description')}")
            return data

    async def send_telegram_document(self, chat_id: Any, file_id_or_url: str, caption: str):
        """إرسال ملف أو كتاب PDF مع النص المعاد صياغته"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        payload = {
            "chat_id": chat_id,
            "document": file_id_or_url,
            "caption": caption[:1024]
        }
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()

    async def send_telegram_photo(self, chat_id: Any, photo_id_or_url: str, caption: str):
        """إرسال صورة مع النص المعاد صياغته"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_id_or_url,
            "caption": caption[:1024]
        }
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()

    # ----------------- معالجة المنشورات الجديدة -----------------
    async def process_new_post(self, source_info: Dict[str, Any], post_id: str, raw_text: str, media_info: Optional[Dict] = None, dest_channel: str = "@your_channel"):
        """معالجة وتدقيق وإعادة صياغة المنشور ثم نشره"""
        self.state["processed_count"] += 1
        source_target = source_info.get("target", "unknown")
        rule_type = source_info.get("rule", "official")

        # 1. التحقق من التكرار
        last_id = self.state["last_processed_ids"].get(source_target)
        if str(last_id) == str(post_id):
            return

        logging.info(f"📥 وارد جديد من [{source_target}] (ID: {post_id}): {raw_text[:60]}...")

        # 2. فحص استبدال الإعلانات
        if self.is_competitor_ad(raw_text):
            logging.info("🎯 تم رصد إعلان ترويجي في المصدر! جاري استبداله بإعلان خدماتك الطلابية...")
            self.state["ad_replaced_count"] += 1
            final_text = self.custom_ad
            self.log_event("ad_replaced", source_target, raw_text, final_text, "replaced")
        else:
            # 3. فحص الكلمات المفتاحية
            keywords = source_info.get("keywords", [])
            if keywords and not any(kw in raw_text for kw in keywords):
                logging.info(f"⏭ تخطي المنشور لعدم مطابقة الكلمات المفتاحية: {source_target}")
                self.state["last_processed_ids"][source_target] = str(post_id)
                self.save_state()
                return

            # 4. تدقيق المعلومات إن كان المصدر شبه رسمي
            if rule_type == "semi-official" and any(char.isdigit() for char in raw_text):
                logging.info("🔍 جاري التحقق من الأرقام والمواعيد عبر محرك البحث...")
                ver_res = await self.verify_facts(raw_text)
                if "CONTRADICTED" in ver_res:
                    logging.warning(f"⚠️ معلومة متناقضة أو مشكوك بها، تم الامتناع عن النشر: {ver_res}")
                    self.log_event("rejected_fact", source_target, raw_text, ver_res, "contradicted")
                    self.state["last_processed_ids"][source_target] = str(post_id)
                    self.save_state()
                    return

            # 5. إعادة الصياغة التعليمية
            logging.info("✍️ جاري إعادة الصياغة بواسطة DeepSeek-V4.1-Flash...")
            final_text = await self.rephrase_post(raw_text, self.custom_instructions)

        # 6. النشر مع مراعاة تأخير المعدل
        now = time.time()
        elapsed = now - self.last_post_time
        if elapsed < 45:  # تأخير 45-60 ثانية بين المنشورات
            await asyncio.sleep(45 - elapsed)

        try:
            if media_info and media_info.get("type") == "document":
                await self.send_telegram_document(dest_channel, media_info["file_id"], final_text)
            elif media_info and media_info.get("type") == "photo":
                await self.send_telegram_photo(dest_channel, media_info["file_id"], final_text)
            else:
                await self.send_telegram_message(dest_channel, final_text)

            self.state["forwarded_count"] += 1
            self.last_post_time = time.time()
            self.state["last_processed_ids"][source_target] = str(post_id)
            self.save_state()
            self.log_event("published", source_target, raw_text, final_text, "success")
            logging.info(f"✅ تم نشر المنشور المعاد صياغته بنجاح إلى: {dest_channel}")

        except Exception as err:
            logging.error(f"❌ خطأ أثناء الإرسال إلى تيليجرام: {err}")
            await asyncio.sleep(30)  # إعادة محاولة بعد 30 ثانية

    # ----------------- معالجة أوامر المشرف (Admin Commands) -----------------
    async def handle_admin_command(self, user_id: int, text: str, chat_id: int):
        """فحص هوية الآدمن والرد على الأوامر"""
        if user_id != ADMIN_ID:
            logging.warning(f"⛔️ محاولة وصول غير مصرح بها من: {user_id}")
            return

        cmd_parts = text.strip().split(maxsplit=2)
        cmd = cmd_parts[0].lower()

        if cmd == "/start" or cmd == "/help":
            msg = f"""👋 أهلاً بك يا مديرنا {ADMIN_USERNAME}!
نظام تحرير المحتوى التعليمي الذكي جاهز وتحت إمرتك.

📌 الأوامر المتاحة:
/status - عرض حالة البوت وإحصائيات النشر
/sources - عرض قائمة المصادر الحالية
/add_source <نوع: tg|x|rss> <المعرف أو الرابط> [أولوية]
/remove_source <المعرف أو الرابط>
/pause - إيقاف النشر التلقائي مؤقتاً
/resume - استئناف النشر
/set_ad <النص> - تحديث إعلان خدماتك الطلابية
/test_rephrase <نص> - اختبار صياغة فورية"""
            await self.send_telegram_message(chat_id, msg)

        elif cmd == "/status":
            st = self.state
            status_text = f"""📊 حالة محرر المحتوى التعليمي:
• البوت: @admiuin_bot
• الآدمن: {ADMIN_USERNAME} ({ADMIN_ID})
• حالة النشر: {'⏸ متوقف مؤقتاً' if self.is_paused else '🟢 نشط ويعمل 24/7'}
• المعالج: {st.get('processed_count', 0)} منشور
• المنشور: {st.get('forwarded_count', 0)} منشور معاد صياغته
• إعلانات تم استبدالها: {st.get('ad_replaced_count', 0)} إعلان خاص بك
• عدد المصادر المراقبة: {len(self.sources.get('sources', []))} مصادر
• النموذج الأساسي: {PRIMARY_MODEL}"""
            await self.send_telegram_message(chat_id, status_text)

        elif cmd == "/sources":
            srcs = self.sources.get("sources", [])
            lines = [f"📋 قائمة المصادر المراقبة ({len(srcs)}):"]
            for s in srcs:
                lines.append(f"• [{s.get('type')}] {s.get('title')} ({s.get('target')}) - {s.get('priority')}")
            await self.send_telegram_message(chat_id, "\n".join(lines))

        elif cmd == "/pause":
            self.is_paused = True
            await self.send_telegram_message(chat_id, "⏸ تم إيقاف النشر التلقائي مؤقتاً.")

        elif cmd == "/resume":
            self.is_paused = False
            await self.send_telegram_message(chat_id, "▶️ تم استئناف النشر التلقائي بنجاح.")

        elif cmd == "/set_ad":
            if len(cmd_parts) > 1:
                self.custom_ad = cmd_parts[1]
                await self.send_telegram_message(chat_id, "✅ تم تحديث نص إعلان خدماتك الطلابية الخاص بك بنجاح!")
            else:
                await self.send_telegram_message(chat_id, "يرجى كتابة نص الإعلان بعد الأمر.")

        elif cmd == "/test_rephrase":
            if len(cmd_parts) > 1:
                sample = cmd_parts[1]
                await self.send_telegram_message(chat_id, "⏳ جاري إعادة الصياغة بالذكاء الاصطناعي...")
                res = await self.rephrase_post(sample, self.custom_instructions)
                await self.send_telegram_message(chat_id, f"النتيجة:\n\n{res}")

    # ----------------- الحلقة الرئيسية للتشغيل -----------------
    async def run(self):
        self.session = aiohttp.ClientSession()
        logging.info("="*60)
        logging.info("  محرر المحتوى التعليمي الجامعي الذكي - قيد التشغيل")
        logging.info(f"  البوت: {BOT_TOKEN[:10]}... | الآدمن: {ADMIN_USERNAME} ({ADMIN_ID})")
        logging.info(f"  النموذج: {PRIMARY_MODEL} | البديل: {FALLBACK_MODEL}")
        logging.info("="*60)

        # إشعار تشغيل للآدمن
        try:
            await self.send_telegram_message(
                ADMIN_ID,
                f"🚀 تم تشغيل محرر المحتوى التعليمي الجامعي بنجاح!\nالآدمن: {ADMIN_USERNAME}\nالنموذج: {PRIMARY_MODEL}"
            )
        except Exception:
            pass

        offset = 0
        while True:
            try:
                # جلب تحديثات وأوامر الآدمن
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=25"
                async with self.session.get(url) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for u in updates:
                            offset = u["update_id"] + 1
                            msg = u.get("message")
                            if msg and "text" in msg:
                                user_id = msg.get("from", {}).get("id")
                                chat_id = msg.get("chat", {}).get("id")
                                text = msg.get("text", "")
                                if text.startswith("/"):
                                    await self.handle_admin_command(user_id, text, chat_id)

                # مراقبة المصادر الذاتية كل دورة
                await asyncio.sleep(5)

            except Exception as e:
                logging.error(f"خطأ في حلقة المراقبة: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    app = EducationalAutoForwarder()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\nتم إيقاف المحرر بأمان.")
