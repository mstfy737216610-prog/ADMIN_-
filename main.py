#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
محرر المحتوى التعليمي الجامعي الذكي - النسخة السحابية لـ GitHub و Bots.Business
Smart Educational Auto-Forwarder (Cloud & BotBusiness Ready)
================================================================================
المطور الأصلي: Redian Marku (MIT License) - https://github.com/redianmarku/Telegram-Autoforwarder
التطوير والتعريب والذكاء الاصطناعي: محرر المحتوى الأكاديمي الذكي
البوت: @admiuin_bot (8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4)
الآدمن: @M_S_F_G (7607633343)
النموذج: DeepSeek-V4.1-Flash (عبر https://api.hcnsec.cn/v1)
================================================================================
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import web

# تحميل متغيرات البيئة إن وجدت
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# الإعدادات
BOT_TOKEN = os.getenv("BOT_TOKEN", "8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7607633343"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@M_S_F_G")

AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.hcnsec.cn/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "sk-J2ky44F6VTDMkL8Q1GHL5sfmbeIpARVDayNuwMfxKI5zCdii")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "DeepSeek-V4.1-Flash")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "auto")
PORT = int(os.getenv("PORT", "8080"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
LOGS_FILE = os.path.join(BASE_DIR, "logs.json")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

SYSTEM_PROMPT_REPHRASE = """# الدور: محرر محتوى تعليمي جامعي
## الهوية
أنت محرر محتوى متخصص في الشؤون التعليمية الجامعية. مهمتك إعادة صياغة المنشورات من قنوات وحسابات جامعية بأسلوب أوضح وأدق، مع الحفاظ على المصداقية الكاملة مثل مشرفي مجموعات الطلاب المخلصين.

## المبادئ الأساسية:
- لا تضف أي معلومة من خيالك لم ترد في النص الأصلي
- لا تحذف أي معلومة جوهرية أو نسب مئوية أو مواعيد أو شروط
- لا تذكر اسم المصدر لأن المنشور معاد صياغته
- اجعل الأسلوب شيقاً وواضحاً مع إيموجيات معتدلة (📚 🎓 📅 📌 💡)

## التنسيق المطلوب إلزامي:
📌 عنوان واضح ومميز
• محتوى منظم في نقاط محددة
💬 دعوة تفاعلية للطلاب
هاشتاجات مناسبة (2-4 فقط)"""

SYSTEM_PROMPT_VERIFY = """# الدور: مدقق معلومات تعليمية
تحقق من صحة المعلومات التالية عبر البحث في مصادر موثوقة (أرقام، مواعيد، نسب):
إذا كانت مؤكدة: أعد VERIFIED
إذا كانت متناقضة: أعد CONTRADICTED
إذا لم تجد تأكيداً: أعد UNVERIFIED"""

DEFAULT_CUSTOM_STUDENT_AD = """🎓 خدمات طلابية معتمدة وأكاديمية متكاملة 🎓
يسرنا تقديم الدعم الأكاديمي الشامل للطلبة والباحثين:
• مساعدة في البحوث والمشاريع الأكاديمية
• التدقيق اللغوي وتنسيق الرسائل الجامعية
• تلخيص المحاضرات والمقررات الدراسية
• استشارات القبول والتسجيل والتنسيق

📞 للتواصل والطلب مباشرة عبر المشرف: @M_S_F_G
✨ جودة أكاديمية، سرعة في الإنجاز، وأسعار مناسبة للطلاب!"""

AD_KEYWORDS = [
    "إعلان مدفوع", "ترويج لخدمات طلابية", "حل واجبات", "بحوث تخرج",
    "خدمات طلابية", "مشاريع تخرج", "كتابة أبحاث", "إعلان ممول", "برعاية"
]

class CloudEducationalBot:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.sources = self.load_json(SOURCES_FILE, {"sources": []})
        self.state = self.load_json(STATE_FILE, {
            "processed_count": 0,
            "forwarded_count": 0,
            "ad_replaced_count": 0,
            "last_processed_ids": {}
        })
        self.is_paused = False
        self.custom_ad = DEFAULT_CUSTOM_STUDENT_AD
        self.last_post_time = 0.0

    def load_json(self, path: str, default_val: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"خطأ في قراءة {path}: {e}")
        return default_val

    def save_json(self, path: str, data: Any):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"خطأ في كتابة {path}: {e}")

    async def call_ai(self, messages: List[Dict[str, str]], model: str = PRIMARY_MODEL) -> str:
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
            async with self.session.post(url, json=payload, headers=headers, timeout=35) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logging.warning(f"النموذج {model} غير متاح مؤقتاً: {e}")

        # محاولة النموذج البديل auto
        if model != FALLBACK_MODEL:
            payload["model"] = FALLBACK_MODEL
            try:
                async with self.session.post(url, json=payload, headers=headers, timeout=35) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
            except Exception:
                pass

        # بديل محلي سريع وذكي
        raw = messages[-1]["content"]
        lines = [l.strip() for l in raw.split("\n") if l.strip() and not l.startswith("http")]
        title = lines[0] if lines else "إعلان جامعي هام"
        bullets = "\n".join([f"• {l}" for l in lines[1:5]]) if len(lines) > 1 else f"• {raw}"
        return f"📌 {title}\n\n{bullets}\n\n💬 يسعدنا استقبال استفساراتكم ومشاركة المنشور مع زملائكم!\n\n#جامعة #أخبار_التعليم #شؤون_الطلاب"

    def is_competitor_ad(self, text: str) -> bool:
        return any(kw in text for kw in AD_KEYWORDS)

    async def send_telegram(self, chat_id: Any, text: str):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()

    async def send_document(self, chat_id: Any, file_id: str, caption: str):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        payload = {"chat_id": chat_id, "document": file_id, "caption": caption[:1024]}
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()

    async def send_photo(self, chat_id: Any, photo_id: str, caption: str):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": chat_id, "photo": photo_id, "caption": caption[:1024]}
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()

    async def process_incoming_post(self, source_info: Dict[str, Any], post_id: str, text: str, media_type: Optional[str] = None, file_id: Optional[str] = None, target_channel: str = "@your_channel"):
        if self.is_paused:
            return

        target = source_info.get("target", "unknown")
        if str(self.state["last_processed_ids"].get(target)) == str(post_id):
            return

        self.state["processed_count"] += 1

        # استبدال إعلان المنافس
        if self.is_competitor_ad(text):
            logging.info(f"🎯 تم استبدال إعلان منافس من [{target}] بإعلان خدماتك الطلابية!")
            self.state["ad_replaced_count"] += 1
            final_text = self.custom_ad
        else:
            # فحص الكلمات المفتاحية
            keywords = source_info.get("keywords", [])
            if keywords and not any(k in text for k in keywords):
                self.state["last_processed_ids"][target] = str(post_id)
                self.save_json(STATE_FILE, self.state)
                return

            # صياغة الذكاء الاصطناعي
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_REPHRASE},
                {"role": "user", "content": text}
            ]
            final_text = await self.call_ai(messages)

        # معدل النشر
        elapsed = time.time() - self.last_post_time
        if elapsed < 40:
            await asyncio.sleep(40 - elapsed)

        try:
            if media_type == "document" and file_id:
                await self.send_document(target_channel, file_id, final_text)
            elif media_type == "photo" and file_id:
                await self.send_photo(target_channel, file_id, final_text)
            else:
                await self.send_telegram(target_channel, final_text)

            self.state["forwarded_count"] += 1
            self.last_post_time = time.time()
            self.state["last_processed_ids"][target] = str(post_id)
            self.save_json(STATE_FILE, self.state)
            logging.info(f"✅ تم النشر في {target_channel} بنجاح!")
        except Exception as e:
            logging.error(f"فشل النشر: {e}")

    async def handle_admin(self, user_id: int, chat_id: int, text: str):
        if user_id != ADMIN_ID:
            return

        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ["/start", "/help"]:
            msg = f"""👋 أهلاً بك يا مديرنا {ADMIN_USERNAME}!
البوت يعمل بنجاح على الاستضافة السحابية / BotBusiness / GitHub 🚀

الأوامر المتاحة:
/status - حالة البوت والإحصائيات
/sources - قائمة المصادر المراقبة
/pause - إيقاف مؤقت
/resume - استئناف
/set_ad <نص> - تحديث إعلان خدماتك الطلابية
/test_rephrase <نص> - تجربة إعادة صياغة فورية"""
            await self.send_telegram(chat_id, msg)

        elif cmd == "/status":
            st = self.state
            msg = f"""📊 حالة المحرر السحابي:
• البوت: @admiuin_bot
• الآدمن: {ADMIN_USERNAME} ({ADMIN_ID})
• المعالج: {st.get('processed_count', 0)} منشور
• المنشور: {st.get('forwarded_count', 0)} منشور
• الإعلانات المستبدلة: {st.get('ad_replaced_count', 0)} إعلان خاص بك
• الحالة: {'⏸ متوقف' if self.is_paused else '🟢 نشط 24/7'}
• النموذج: {PRIMARY_MODEL}"""
            await self.send_telegram(chat_id, msg)

        elif cmd == "/sources":
            srcs = self.sources.get("sources", [])
            lines = [f"📋 المصادر المراقبة ({len(srcs)}):"]
            for s in srcs:
                lines.append(f"• [{s.get('type')}] {s.get('title')} ({s.get('target')})")
            await self.send_telegram(chat_id, "\n".join(lines))

        elif cmd == "/pause":
            self.is_paused = True
            await self.send_telegram(chat_id, "⏸ تم إيقاف النشر التلقائي مؤقتاً.")

        elif cmd == "/resume":
            self.is_paused = False
            await self.send_telegram(chat_id, "▶️ تم استئناف النشر التلقائي.")

        elif cmd == "/set_ad" and arg:
            self.custom_ad = arg
            await self.send_telegram(chat_id, "✅ تم تحديث إعلان الخدمات الطلابية بنجاح!")

        elif cmd == "/test_rephrase" and arg:
            await self.send_telegram(chat_id, "⏳ جاري الصياغة بواسطة DeepSeek-V4.1-Flash...")
            res = await self.call_ai([
                {"role": "system", "content": SYSTEM_PROMPT_REPHRASE},
                {"role": "user", "content": arg}
            ])
            await self.send_telegram(chat_id, f"النتيجة:\n\n{res}")

    # خادم ويب خفيف للفحص الصحي (Keep-Alive Health Check for Free Hosting)
    async def run_health_server(self):
        app = web.Application()
        async def handle_ping(request):
            return web.Response(text="OK - Educational Bot is Running 24/7", status=200)
        app.router.add_get("/", handle_ping)
        app.router.add_get("/health", handle_ping)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logging.info(f"🌐 خادم Keep-Alive يعمل على المنفذ: {PORT}")

    async def run(self):
        self.session = aiohttp.ClientSession()
        logging.info("="*60)
        logging.info("  محرر المحتوى التعليمي الجامعي الذكي (Cloud & GitHub)")
        logging.info(f"  البوت: @admiuin_bot | الآدمن: {ADMIN_USERNAME} ({ADMIN_ID})")
        logging.info("="*60)

        # تشغيل خادم الصحة للاستضافات المجانية لمنع إيقاف السيرفر
        try:
            await self.run_health_server()
        except Exception as e:
            logging.warning(f"تعذر تشغيل منفذ الويب (سيستمر البوت كـ Worker): {e}")

        # إشعار الآدمن بالتشغيل
        try:
            await self.send_telegram(ADMIN_ID, f"🚀 تم تشغيل محرر المحتوى التعليمي بنجاح عبر الاستضافة السحابية!\nالآدمن: {ADMIN_USERNAME}\nالنموذج: {PRIMARY_MODEL}")
        except Exception:
            pass

        offset = 0
        while True:
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=25"
                async with self.session.get(url) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        for u in data.get("result", []):
                            offset = u["update_id"] + 1
                            msg = u.get("message")
                            if msg and "text" in msg:
                                user_id = msg.get("from", {}).get("id")
                                chat_id = msg.get("chat", {}).get("id")
                                text = msg.get("text", "")
                                if text.startswith("/"):
                                    await self.handle_admin(user_id, chat_id, text)

                await asyncio.sleep(4)
            except Exception as e:
                logging.error(f"خطأ في دورة التحديث: {e}")
                await asyncio.sleep(8)

if __name__ == "__main__":
    bot = CloudEducationalBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nتم إيقاف البوت.")
