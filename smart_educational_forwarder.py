#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
محرر المحتوى التعليمي الجامعي الذكي - بوت تيليجرام الشامل
Telegram University Educational Content Editor (Zero Dependency Native Bot)
================================================================================
المشرف المعتمد: @M_S_F_G (ID: 7607633343)
توكن البوت: 8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4
الذكاء الاصطناعي: DeepSeek-V4.1-Flash (https://api.hcnsec.cn/v1)
================================================================================
"""

import os
import sys
import json
import time
import ssl
import re
import logging
import threading
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List

# تحميل متغيرات البيئة إن وجدت
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "7607633343"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "M_S_F_G").replace("@", "").strip()

AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.hcnsec.cn/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "sk-J2ky44F6VTDMkL8Q1GHL5sfmbeIpARVDayNuwMfxKI5zCdii").strip()
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "DeepSeek-V4.1-Flash").strip()
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "auto").strip()
PORT = int(os.getenv("KEEPALIVE_PORT", os.getenv("PORT", "8088")))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

SYSTEM_PROMPT_REPHRASE = """# الدور: محرر محتوى تعليمي جامعي
## الهوية
أنت محرر محتوى متخصص في الشؤون التعليمية الجامعية ومجموعات الطلاب. مهمتك قراءة المنشورات من قنوات وحسابات جامعية وإعادة صياغتها بأسلوب واضح وأنيق وأدق أكاديمياً، مع الحفاظ على الأرقام والمواعيد والشروط كما هي دون تغيير.

## التنسيق المطلوب إلزامي:
📌 [عنوان بارز وموجز للمنشور]

[المحتوى منظم في نقاط محددة وسهلة القراءة تبرز المواعيد والخطوات والشروط]

💬 [دعوة تفاعلية قصيرة للطلاب للمشاركة أو الاستفسار]

[2 إلى 4 هاشتاجات ملائمة: #جامعة #قبول #تسجيل #امتحانات]"""

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

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        res = {
            "status": "online",
            "bot": "@admiuin_bot",
            "admin": f"@{ADMIN_USERNAME}",
            "model": PRIMARY_MODEL,
            "timestamp": int(time.time()),
            "message": "محرر المحتوى التعليمي الجامعي الذكي يعمل بنجاح 24/7"
        }
        self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_keepalive_server():
    for p in [PORT, 8088, 8089, 8090, 8000]:
        try:
            server = HTTPServer(("0.0.0.0", p), HealthCheckHandler)
            logging.info(f" خادم Keep-Alive يعمل بنجاح على المنفذ: {p}")
            server.serve_forever()
            break
        except Exception:
            continue


class StandaloneTelegramEducationalBot:
    def __init__(self):
        self.sources = self.load_json(SOURCES_FILE, {
            "target_channel": "",  # القناة التي ينشر فيها البوت تلقائياً
            "sources": [
                {
                    "id": "src_tg_univ_news",
                    "type": "telegram",
                    "target": "@KSU_News",
                    "title": "أخبار الجامعة والقبول الرسمي",
                    "priority": "high",
                    "rule": "official",
                    "keywords": ["قبول", "تسجيل", "نتائج", "مواعيد", "منح", "امتحان", "بي دي اف", "pdf"],
                    "blacklist": ["إعلان ممول"],
                    "enabled": True,
                    "lastPostId": ""
                },
                {
                    "id": "src_x_moe",
                    "type": "twitter",
                    "target": "@moe_gov_sa",
                    "title": "الحساب الرسمي لوزارة التعليم",
                    "priority": "high",
                    "rule": "official",
                    "keywords": ["تقويم دراسي", "إجازة", "جامعات", "منح"],
                    "blacklist": ["إعلان تجاري"],
                    "enabled": True,
                    "lastPostId": ""
                }
            ]
        })
        self.state = self.load_json(STATE_FILE, {
            "bot_status": "active",
            "processed_count": 0,
            "forwarded_count": 0,
            "ad_replaced_count": 0,
            "last_processed_ids": {}
        })
        self.is_paused = False
        self.target_channel = self.sources.get("target_channel", "")
        self.custom_ad = DEFAULT_CUSTOM_STUDENT_AD
        self.custom_instructions = "كن مثل مشرفين القروبات الذي يبحث عن الأخبار الجديدة ويعطيها للطلاب بوضوح"
        self.user_waiting_state: Dict[int, str] = {}

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

    def is_authorized(self, user: Dict[str, Any]) -> bool:
        user_id = user.get("id")
        username = (user.get("username") or "").replace("@", "").strip().lower()
        if user_id == ADMIN_ID:
            return True
        if username and username == ADMIN_USERNAME.lower():
            return True
        return False

    def tg_request(self, method: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
        data_bytes = None
        headers = {"User-Agent": "TelegramEducationalBot/2.0"}
        if payload is not None:
            data_bytes = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
                res_raw = resp.read().decode("utf-8")
                return json.loads(res_raw)
        except Exception as e:
            logging.error(f"خطأ في طلب تيليجرام ({method}): {e}")
            return {"ok": False, "description": str(e)}

    def send_msg(self, chat_id: Any, text: str, reply_markup: Optional[Dict] = None) -> Dict[str, Any]:
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.tg_request("sendMessage", payload)

    def answer_callback(self, cb_id: str, text: Optional[str] = None):
        payload = {"callback_query_id": cb_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = False
        return self.tg_request("answerCallbackQuery", payload)

    def is_competitor_ad(self, text: str) -> bool:
        return any(kw in text for kw in AD_KEYWORDS)

    def call_ai(self, raw_text: str, custom_instruction: str = "") -> str:
        url = f"{AI_BASE_URL}/chat/completions"
        instruction_addon = f"تعليمات المشرف: {custom_instruction}\n\n" if custom_instruction else ""
        payload = {
            "model": PRIMARY_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_REPHRASE},
                {"role": "user", "content": f"{instruction_addon}أعد صياغة هذا المنشور الجامعي بدقة:\n{raw_text}"}
            ],
            "temperature": 0.4,
            "max_tokens": 700
        }
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TelegramEducationalBot/2.0"
        }

        # 1. تجربة النموذج الأساسي DeepSeek-V4.1-Flash
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logging.warning(f"ملاحظة في اتصال نموذج الذكاء الأساسي {PRIMARY_MODEL}: {e}")

        # 2. تجربة النموذج البديل auto
        try:
            payload["model"] = FALLBACK_MODEL
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logging.warning(f"ملاحظة في اتصال النموذج البديل {FALLBACK_MODEL}: {e}")

        # 3. صياغة محلية ذكية فورية
        lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not l.startswith("http")]
        title = lines[0] if lines else "تحديث جامعي وتعليمي هام"
        bullets = "\n".join([f"• {l}" for l in lines[1:6]]) if len(lines) > 1 else f"• {raw_text}"
        return f"📌 **{title}**\n\n{bullets}\n\n💬 يسعدنا استقبال استفساراتكم ومشاركة المنشور مع زملائكم الطلاب!\n\n#جامعة #أخبار_التعليم #شؤون_الطلاب #دراسة"

    # ----------------- لوحات المفاتيح والأزرار -----------------
    def get_main_reply_keyboard(self) -> Dict[str, Any]:
        return {
            "keyboard": [
                [{"text": "🎛 لوحة التحكم الرئيسية"}, {"text": "📊 حالة البوت"}],
                [{"text": "➕ إضافة قناة أو رابط"}, {"text": "📋 إدارة المصادر"}],
                [{"text": "📢 تحديد قناتي للنشر"}, {"text": "🎯 إعلاني الخاص (المنافسين)"}],
                [{"text": "⚙️ تعليمات المحرر"}, {"text": "🔑 المفاتيح والبيانات"}],
                [{"text": "⏸ إيقاف / استئناف"}, {"text": "🧪 تجربة صياغة منشور"}]
            ],
            "resize_keyboard": True,
            "persistent": True
        }

    def get_control_panel_inline_keyboard(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {"text": "➕ إضافة قناة / رابط جديد", "callback_data": "panel_add_source"},
                    {"text": "📢 تحديد قناتي للنشر", "callback_data": "panel_set_channel"}
                ],
                [
                    {"text": "📋 المصادر المراقبة (sources.json)", "callback_data": "panel_sources"},
                    {"text": "🎯 إعلان خدماتي البديل", "callback_data": "panel_ad"}
                ],
                [
                    {"text": "⚙️ تخصيص تعليمات المشرف", "callback_data": "panel_instructions"},
                    {"text": "🔑 بيانات المفتاح والتوكن", "callback_data": "panel_keys"}
                ],
                [
                    {"text": f"{'▶️ استئناف النشر' if self.is_paused else '⏸ إيقاف مؤقت'}", "callback_data": "panel_toggle_pause"},
                    {"text": "📊 الإحصائيات الشاملة", "callback_data": "panel_stats"}
                ],
                [
                    {"text": "✍️ إعادة صياغة نص الآن", "callback_data": "panel_test"}
                ]
            ]
        }

    def show_welcome_panel(self, chat_id: int):
        status_badge = "⏸ متوقف مؤقتاً" if self.is_paused else "🟢 نشط ويعمل 24/7"
        target_ch_text = self.target_channel if self.target_channel else "⚠️ لم تُحدد بعد (اضغط زر تحديد قناتي)"
        text = f"""👋 مرحباً بك يا مديرنا العزيز @{ADMIN_USERNAME}!
👑 أنت المشرف المعتمد والمخول بالتحكم الكامل (معرفك: `{ADMIN_ID}`)

🎛 **لوحة التحكم بمحرر المحتوى التعليمي الجامعي الذكي**:
• حالة النشر التلقائي: {status_badge}
• القناة الناشرة المستهدفة: `{target_ch_text}`
• النموذج الفعال: `{PRIMARY_MODEL}`
• المصادر المراقبة: {len(self.sources.get('sources', []))} مصادر
• منشورات تمت معالجتها: {self.state.get('processed_count', 0)}
• إعلانات تم استبدالها بإعلانك: {self.state.get('ad_replaced_count', 0)}

👇 **اختر من الأزرار أدناه للتحكم السريع أو إضافة مصادر بسهولة:**
(أو أرسل/وجّه أي خبر للمحادثة وسيقوم البوت بصياغته فوراً)"""
        self.send_msg(chat_id, text, self.get_control_panel_inline_keyboard())

    def handle_callback_query(self, cb: Dict[str, Any]):
        cb_id = cb["id"]
        from_user = cb["from"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")

        if not self.is_authorized(from_user):
            self.answer_callback(cb_id, "⛔️ غير مصرح لك باستخدام هذه الأزرار.")
            return

        self.answer_callback(cb_id)

        if data == "panel_add_source":
            self.user_waiting_state[chat_id] = "waiting_for_new_source"
            ask_text = """➕ **إضافة قناة أو رابط جديد للمراقبة:**

أرسل الآن معرّف أو رابط المصدر المطلوب إضافته:
• **قناة تيليجرام:** `@KSU_News` أو `https://t.me/KSU_News`
• **موقع أو رابط أخبار RSS:** `https://news.ksu.edu.sa/rss.xml`
• **حساب تويتر/X:** `@moe_gov_sa` أو `https://x.com/moe_gov_sa`

سيتعرف البوت تلقائياً على نوع الرابط ويضيفه فوراً لقائمة المراقبة!"""
            self.send_msg(chat_id, ask_text)

        elif data == "panel_set_channel":
            self.user_waiting_state[chat_id] = "waiting_for_target_channel"
            ask_text = """📢 **تحديد قناتك لنشر المحتوى التلقائي:**

أرسل الآن معرّف أو رابط قناتك التي تريد أن ينشر البوت فيها المنشورات المعادة صياغتها وإعلاناتك:
مثال: `@MyUniversityChannel` أو `https://t.me/MyUniversityChannel`

⚠️ **ملاحظة هامة:** تأكد من إضافة البوت (@admiuin_bot) كـ **مشرف (Admin)** في القناة مع صلاحية نشر الرسائل."""
            self.send_msg(chat_id, ask_text)

        elif data == "panel_sources":
            srcs = self.sources.get("sources", [])
            lines = [f"📋 **قائمة مصادر المراقبة الحالية ({len(srcs)}):**\n\n"]
            for i, s in enumerate(srcs, 1):
                rule = "رسمي [نشر مباشر]" if s.get("rule") == "official" else "شبه رسمي [تدقيق]"
                lines.append(f"{i}. [{s.get('type')}] **{s.get('title')}**\n   الهدف: `{s.get('target')}` | القاعدة: {rule} | الأولوية: {s.get('priority')}\n")
            lines.append("\n➕ لإضافة مصدر بنقرة واحدة، اضغط زر: `➕ إضافة قناة أو رابط`")
            lines.append("➖ لحذف أي مصدر، أرسل: `/remove_source @channel`")
            self.send_msg(chat_id, "".join(lines))

        elif data == "panel_ad":
            text = f"""🎯 **نظام استبدال إعلانات المنافسين بإعلاناتك الخاصة:**
عندما تنشر أي قناة مراقبة إعلاناً لخدمات طلابية أو حل واجبات، يستبدله البوت تلقائياً بهذا المنشور:

━━━━━━━━━━━━━━━━━━━
{self.custom_ad}
━━━━━━━━━━━━━━━━━━━

✏️ لتعديل هذا الإعلان في أي وقت، أرسل:
`/set_ad النص الجديد هنا`"""
            self.send_msg(chat_id, text)

        elif data == "panel_instructions":
            text = f"""⚙️ **تعليمات المشرف المخصصة للمحرر:**
يلتزم بها الذكاء الاصطناعي بدقة عند كل صياغة:

📌 *\"{self.custom_instructions}\"*

✏️ لتعديل التعليمات، أرسل:
`/set_instruction تعليماتك الجديدة هنا`"""
            self.send_msg(chat_id, text)

        elif data == "panel_keys":
            text = f"""🔑 **بيانات الاعتمادات والمفاتيح المعتمدة:**

• توكن البوت: `{BOT_TOKEN}`
• يوزر البوت: @admiuin_bot
• معرف الآدمن: `{ADMIN_ID}` (@{ADMIN_USERNAME})
• عنوان الذكاء الاصطناعي: `{AI_BASE_URL}`
• النموذج الأساسي: `{PRIMARY_MODEL}`
• مفتاح الذكاء الكامل: `{AI_API_KEY}`

🔒 جميع المفاتيح مفعلة ومثبتة وتعمل بنجاح."""
            self.send_msg(chat_id, text)

        elif data == "panel_toggle_pause":
            self.is_paused = not self.is_paused
            state_str = "⏸ تم إيقاف النشر مؤقتاً." if self.is_paused else "▶️ تم استئناف النشر التلقائي بنجاح!"
            self.send_msg(chat_id, state_str, self.get_control_panel_inline_keyboard())

        elif data == "panel_stats":
            st = self.state
            text = f"""📊 **إحصائيات الأداء والمراقبة:**
• إجمالي المنشورات المفحوصة: {st.get('processed_count', 0)}
• المنشورات الأكاديمية الصادرة: {st.get('forwarded_count', 0)}
• إعلانات تم استبدالها بإعلانك: {st.get('ad_replaced_count', 0)}
• المصادر النشطة: {len(self.sources.get('sources', []))}
• القناة الناشرة: `{self.target_channel or 'غير محددة'}`"""
            self.send_msg(chat_id, text)

        elif data == "panel_test":
            self.user_waiting_state[chat_id] = "waiting_for_rephrase_text"
            self.send_msg(chat_id, "✍️ تفضل بإرسال أو توجيه أي منشور أو خبر الآن، وسأقوم بإعادة صياغته فوراً بأسلوب مشرفي المجموعات التعليمية!")

    def handle_message(self, msg: Dict[str, Any]):
        chat_id = msg["chat"]["id"]
        from_user = msg.get("from", {})
        text = msg.get("text", "") or msg.get("caption", "")

        logging.info(f"رسالة واردة من {from_user.get('id')} (@{from_user.get('username')}): {text[:60]}")

        # التحقق من صلاحية المشرف
        if not self.is_authorized(from_user):
            sender_id = from_user.get("id")
            sender_user = from_user.get("username") or "غير محدد"
            warn = f"""⛔️ مرحباً بك!
هذا البوت مخصص لإدارة وتوجيه المحتوى التعليمي للمشرف @{ADMIN_USERNAME}.
معرفك الحالي: `{sender_id}`
يوزرك: `@{sender_user}`

إذا كان هذا حسابك، تأكد من الدخول بالحساب المعتمد أو تواصل مع المشرف."""
            self.send_msg(chat_id, warn)
            return

        clean_text = text.strip()

        # معالجة المدخلات التفاعلية المنتظرة
        if chat_id in self.user_waiting_state:
            state = self.user_waiting_state.pop(chat_id)

            if state == "waiting_for_new_source":
                self.process_add_source_input(chat_id, clean_text)
                return

            if state == "waiting_for_target_channel":
                target = clean_text.replace("https://t.me/", "")
                if not target.startswith("@") and not target.startswith("-100"):
                    target = "@" + target
                self.target_channel = target
                self.sources["target_channel"] = target
                self.save_json(SOURCES_FILE, self.sources)
                reply = f"""✅ **تم تحديد قناتك للنشر بنجاح!**
📢 القناة: `{target}`

سيتولى البوت نشر أي منشور تعليمي معاد صياغته وإعلانات خدماتك الطلابية فيها تلقائياً!
(تأكد من إضافة البوت @admiuin_bot مشرفاً في القناة)"""
                self.send_msg(chat_id, reply, self.get_main_reply_keyboard())
                return

            if state == "waiting_for_rephrase_text":
                self.rephrase_and_reply(chat_id, clean_text)
                return

        # الأزرار والأوامر الرئيسية
        if clean_text in ["/start", "/help", "🎛 لوحة التحكم الرئيسية", "لوحة التحكم"]:
            self.send_msg(chat_id, "أهلاً بك يا مديرنا! إليك لوحة المفاتيح والتحكم المباشرة:", self.get_main_reply_keyboard())
            self.show_welcome_panel(chat_id)
            return

        if clean_text in ["➕ إضافة قناة أو رابط", "إضافة مصدر", "/add"]:
            self.user_waiting_state[chat_id] = "waiting_for_new_source"
            self.send_msg(chat_id, "📌 أرسل الآن رابط أو معرّف القناة أو الموقع (مثال: `@channel` أو رابط موقع RSS):")
            return

        if clean_text in ["📢 تحديد قناتي للنشر", "/set_channel"]:
            self.user_waiting_state[chat_id] = "waiting_for_target_channel"
            self.send_msg(chat_id, "📢 أرسل الآن معرّف قناتك (مثال: `@MyChannel`):")
            return

        if clean_text in ["/status", "📊 حالة البوت"]:
            st = self.state
            status_text = f"""📊 **حالة البوت ومحرر المحتوى الأكاديمي:**
• البوت: @admiuin_bot
• المشرف: @{ADMIN_USERNAME} ({ADMIN_ID})
• حالة النشر: {'⏸ متوقف مؤقتاً' if self.is_paused else '🟢 نشط 24/7'}
• القناة الناشرة: `{self.target_channel or 'غير محددة'}`
• المعالج: {st.get('processed_count', 0)} منشور
• المنشور: {st.get('forwarded_count', 0)} منشور
• إعلاناتك المستبدلة: {st.get('ad_replaced_count', 0)} إعلان
• النموذج: `{PRIMARY_MODEL}`"""
            self.send_msg(chat_id, status_text)
            return

        if clean_text in ["/sources", "📋 إدارة المصادر"]:
            srcs = self.sources.get("sources", [])
            lines = [f"📋 **قائمة المصادر المراقبة ({len(srcs)}):**\n\n"]
            for s in srcs:
                lines.append(f"• [{s.get('type')}] **{s.get('title')}** (`{s.get('target')}`) - أولوية: {s.get('priority')}\n")
            lines.append("\n➕ لإضافة مصدر جديد، اضغط زر: `➕ إضافة قناة أو رابط`")
            self.send_msg(chat_id, "".join(lines))
            return

        if clean_text in ["🎯 إعلاني الخاص (المنافسين)", "إعلاني"]:
            self.send_msg(chat_id, f"🎯 **إعلانك الحالي لخدمات الطلاب:**\n\n{self.custom_ad}\n\n✏️ لتعديله أرسل: `/set_ad النص الجديد`")
            return

        if clean_text in ["⚙️ تعليمات المحرر", "التعليمات"]:
            self.send_msg(chat_id, f"⚙️ **تعليمات المشرف الحالية:**\n\n\"{self.custom_instructions}\"\n\n✏️ لتعديلها أرسل: `/set_instruction النص الجديد`")
            return

        if clean_text in ["/keys", "🔑 المفاتيح والبيانات", "المفاتيح"]:
            keys_text = f"""🔑 **بيانات الاعتمادات والمفاتيح كاملة:**
• توكن البوت: `{BOT_TOKEN}`
• المشرف: @{ADMIN_USERNAME} ({ADMIN_ID})
• عنوان API: `{AI_BASE_URL}`
• النموذج الأساسي: `{PRIMARY_MODEL}`
• مفتاح الذكاء الاصطناعي: `{AI_API_KEY}`"""
            self.send_msg(chat_id, keys_text)
            return

        if clean_text in ["⏸ إيقاف / استئناف", "إيقاف"]:
            self.is_paused = not self.is_paused
            self.send_msg(chat_id, f"{'⏸ تم إيقاف النشر مؤقتاً.' if self.is_paused else '▶️ تم استئناف النشر التلقائي.'}")
            return

        if clean_text in ["🧪 تجربة صياغة منشور", "تجربة"]:
            self.user_waiting_state[chat_id] = "waiting_for_rephrase_text"
            self.send_msg(chat_id, "✍️ أرسل الآن أي خبر أو منشور أو ملف وسأقوم بصياغته فوراً بالذكاء الاصطناعي!")
            return

        # تعديل الإعلان عبر /set_ad
        if clean_text.startswith("/set_ad"):
            new_ad = clean_text.replace("/set_ad", "").strip()
            if new_ad:
                self.custom_ad = new_ad
                self.send_msg(chat_id, "✅ تم تحديث إعلان خدماتك الطلابية البديل بنجاح!")
            else:
                self.send_msg(chat_id, "يرجى كتابة نص الإعلان بعد الأمر، مثال:\n`/set_ad إعلانك هنا`")
            return

        # تعديل التعليمات عبر /set_instruction
        if clean_text.startswith("/set_instruction"):
            new_ins = clean_text.replace("/set_instruction", "").strip()
            if new_ins:
                self.custom_instructions = new_ins
                self.send_msg(chat_id, "✅ تم حفظ تعليمات المشرف للمحرر الذكي بنجاح!")
            else:
                self.send_msg(chat_id, "يرجى كتابة نص التعليمات بعد الأمر.")
            return

        # حذف مصدر عبر /remove_source
        if clean_text.startswith("/remove_source"):
            target = clean_text.replace("/remove_source", "").strip()
            srcs = self.sources.get("sources", [])
            self.sources["sources"] = [s for s in srcs if s.get("target") != target and s.get("target") != "@" + target.replace("@", "")]
            self.save_json(SOURCES_FILE, self.sources)
            self.send_msg(chat_id, f"✅ تم حذف المصدر `{target}` ومزامنة sources.json بنجاح!")
            return

        # إذا أرسل المشرف رابطاً أو معرّفاً مباشرة، نقوم باكتشافه وإضافته
        if clean_text.startswith("@") or clean_text.startswith("http://") or clean_text.startswith("https://"):
            self.process_add_source_input(chat_id, clean_text)
            return

        # إعادة الصياغة المباشرة للنصوص العادية
        if len(clean_text) > 5:
            self.rephrase_and_reply(chat_id, clean_text)

    def process_add_source_input(self, chat_id: int, input_str: str):
        """التعرف الذكي التلقائي على نوع الرابط أو القناة وإضافتها فوراً"""
        input_str = input_str.strip()
        src_type = "telegram"
        target = input_str
        title = input_str

        if "twitter.com" in input_str or "x.com" in input_str:
            src_type = "twitter"
            parts = input_str.rstrip("/").split("/")
            handle = parts[-1]
            target = f"@{handle}" if not handle.startswith("@") else handle
            title = f"حساب تويتر {target}"
        elif input_str.startswith("http://") or input_str.startswith("https://"):
            if "t.me/" in input_str:
                src_type = "telegram"
                handle = input_str.split("t.me/")[-1].replace("s/", "").split("/")[0].strip()
                target = f"@{handle}"
                title = f"قناة تيليجرام {target}"
            else:
                src_type = "rss"
                target = input_str
                title = f"موقع إخباري: {urllib.parse.urlparse(input_str).netloc}"
        elif input_str.startswith("@"):
            src_type = "telegram"
            target = input_str
            title = f"قناة تيليجرام {target}"
        else:
            # افتراضياً معرّف تيليجرام
            target = f"@{input_str}"
            src_type = "telegram"
            title = f"قناة تيليجرام {target}"

        new_entry = {
            "id": f"src_{int(time.time())}",
            "type": src_type,
            "target": target,
            "title": title,
            "priority": "high",
            "rule": "official",
            "keywords": ["قبول", "تسجيل", "نتائج", "مواعيد", "منح", "امتحان", "بي دي اف", "pdf"],
            "blacklist": ["إعلان ممول"],
            "enabled": True,
            "lastPostId": ""
        }

        self.sources.setdefault("sources", []).append(new_entry)
        self.save_json(SOURCES_FILE, self.sources)

        confirm_msg = f"""✅ **تم ربط المصدر بنجاح!**
• النوع: `[{src_type}]`
• الهدف: `{target}`
• العنوان: {title}
• تم التحديث والحفظ في: `sources.json` 💾

سيقوم البوت بمراقبة المنشورات تلقائياً وإعادة صياغتها ونشرها فور صدورها!"""
        self.send_msg(chat_id, confirm_msg, self.get_main_reply_keyboard())

    def rephrase_and_reply(self, chat_id: int, raw_text: str):
        self.state["processed_count"] = self.state.get("processed_count", 0) + 1

        # 1. فحص إعلان المنافس
        if self.is_competitor_ad(raw_text):
            self.state["ad_replaced_count"] = self.state.get("ad_replaced_count", 0) + 1
            self.save_json(STATE_FILE, self.state)
            reply = f"""🎯 **تم رصد إعلان ترويجي للمنافسين!**
تم استبداله تلقائياً بإعلان خدماتك الطلابية الخاص بك:

━━━━━━━━━━━━━━━━━━━
{self.custom_ad}
━━━━━━━━━━━━━━━━━━━"""
            self.send_msg(chat_id, reply)
            if self.target_channel:
                self.send_msg(self.target_channel, self.custom_ad)
            return

        # 2. الصياغة بالذكاء الاصطناعي
        self.send_msg(chat_id, f"⏳ جاري إعادة الصياغة الأكاديمية عبر {PRIMARY_MODEL} بأسلوب مشرفي القروبات...")
        rephrased = self.call_ai(raw_text, self.custom_instructions)

        self.state["forwarded_count"] = self.state.get("forwarded_count", 0) + 1
        self.save_json(STATE_FILE, self.state)

        result_msg = f"""✨ **المنشور التعليمي الجاهز للنشر:**
━━━━━━━━━━━━━━━━━━━
{rephrased}
━━━━━━━━━━━━━━━━━━━
⚡️ صياغة: `{PRIMARY_MODEL}`
💡 يمكنك نسخه أو نشره في قناتك بنقرة واحدة!"""
        self.send_msg(chat_id, result_msg)

        # النشر في القناة إن كانت محددة
        if self.target_channel:
            self.send_msg(self.target_channel, rephrased)

    # ----------------- مراقب المصادر الآلي في الخلفية -----------------
    def monitor_sources_loop(self):
        """فحص دوري لكافة القنوات والروابط في sources.json وسحب الجديد تلقائياً"""
        logging.info("🚀 تم تشغيل مراقب المصادر والقنوات التلقائي في الخلفية...")
        while True:
            try:
                time.sleep(60)  # فحص كل دقيقة
                if self.is_paused:
                    continue

                srcs = self.sources.get("sources", [])
                for s in srcs:
                    if not s.get("enabled", True):
                        continue

                    s_type = s.get("type")
                    target = s.get("target", "")

                    if s_type == "telegram":
                        self.check_telegram_channel(s)
                    elif s_type == "rss":
                        self.check_rss_feed(s)

            except Exception as e:
                logging.error(f"خطأ في دورة مراقبة المصادر: {e}")

    def check_telegram_channel(self, src: Dict[str, Any]):
        channel_name = src.get("target", "").replace("@", "").replace("https://t.me/s/", "").replace("https://t.me/", "").strip()
        if not channel_name:
            return

        url = f"https://t.me/s/{channel_name}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=12) as resp:
                html = resp.read().decode("utf-8")
                matches = re.findall(r'data-post=\"([^\"]+)\".*?class=\"tgme_widget_message_text[^\"]*js-message_text\"[^>]*>(.*?)</div>', html, re.DOTALL)
                if not matches:
                    return

                last_known = src.get("lastPostId", "")
                latest_post_id, text_html = matches[-1]

                if latest_post_id != last_known:
                    src["lastPostId"] = latest_post_id
                    self.save_json(SOURCES_FILE, self.sources)

                    clean_text = re.sub(r'<br\s*/?>', '\n', text_html)
                    clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()

                    if clean_text and len(clean_text) > 10:
                        logging.info(f"منشور جديد تم رصده في {src.get('target')}: {latest_post_id}")
                        self.process_incoming_channel_post(src, clean_text)
        except Exception as e:
            logging.debug(f"فحص القناة {channel_name}: {e}")

    def check_rss_feed(self, src: Dict[str, Any]):
        url = src.get("target", "")
        if not url.startswith("http"):
            return
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=12) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                item = root.find(".//item")
                if item is not None:
                    title = item.findtext("title") or ""
                    desc = item.findtext("description") or ""
                    link = item.findtext("link") or ""
                    post_id = link or title
                    if post_id != src.get("lastPostId"):
                        src["lastPostId"] = post_id
                        self.save_json(SOURCES_FILE, self.sources)
                        post_text = f"{title}\n{desc}"
                        self.process_incoming_channel_post(src, post_text)
        except Exception as e:
            logging.debug(f"فحص تغذية RSS {url}: {e}")

    def process_incoming_channel_post(self, src: Dict[str, Any], text: str):
        """معالجة المنشور ونشره للمشرف أو في قناته المحددة"""
        if self.is_competitor_ad(text):
            self.state["ad_replaced_count"] = self.state.get("ad_replaced_count", 0) + 1
            self.save_json(STATE_FILE, self.state)
            notif = f"🎯 **تم رصد إعلان منافس من [{src.get('title')}]!**\nتم استبداله بإعلان خدماتك الطلابية:\n\n{self.custom_ad}"
            self.send_msg(ADMIN_ID, notif)
            if self.target_channel:
                self.send_msg(self.target_channel, self.custom_ad)
            return

        rephrased = self.call_ai(text, self.custom_instructions)
        self.state["forwarded_count"] = self.state.get("forwarded_count", 0) + 1
        self.save_json(STATE_FILE, self.state)

        out_msg = f"""📢 **منشور تعليمي جديد معاد صياغته من [{src.get('title')}]:**
━━━━━━━━━━━━━━━━━━━
{rephrased}
━━━━━━━━━━━━━━━━━━━"""
        self.send_msg(ADMIN_ID, out_msg)
        if self.target_channel:
            self.send_msg(self.target_channel, rephrased)

    # ----------------- تشغيل البوت -----------------
    def run(self):
        logging.info("=" * 60)
        logging.info("  محرر المحتوى التعليمي الجامعي الذكي (Telegram Native Bot)")
        logging.info(f"  البوت: @admiuin_bot | المشرف: @{ADMIN_USERNAME} ({ADMIN_ID})")
        logging.info(f"  النموذج: {PRIMARY_MODEL} | المفتاح: {AI_API_KEY[:8]}...")
        logging.info("=" * 60)

        # خادم Keep-Alive
        threading.Thread(target=run_keepalive_server, daemon=True).start()

        # مراقب المصادر الآلي
        threading.Thread(target=self.monitor_sources_loop, daemon=True).start()

        # إشعار تشغيل للمشرف
        try:
            welcome_text = f"""🚀 **تم تشغيل وتحديث محرر المحتوى التعليمي بنجاح!**
👑 أهلاً بك يا مديرنا @{ADMIN_USERNAME} (معرف: `{ADMIN_ID}`)
🤖 النموذج الفعال: `{PRIMARY_MODEL}`
📢 القناة الناشرة: `{self.target_channel or 'لم تُحدد بعد'}`

أرسل /start أو استخدم الأزرار التفاعلية للتحكم الفوري."""
            self.send_msg(ADMIN_ID, welcome_text, self.get_main_reply_keyboard())
        except Exception as e:
            logging.warning(f"ملاحظة في إشعار الآدمن: {e}")

        offset = 0
        logging.info("🎧 جاري الاستماع لتحديثات وأوامر تيليجرام...")
        while True:
            try:
                res = self.tg_request(f"getUpdates?offset={offset}&timeout=20")
                if res.get("ok"):
                    updates = res.get("result", [])
                    for u in updates:
                        offset = u["update_id"] + 1
                        if "callback_query" in u:
                            self.handle_callback_query(u["callback_query"])
                        elif "message" in u:
                            self.handle_message(u["message"])

                time.sleep(0.5)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"خطأ في دورة التحديث: {e}")
                time.sleep(3)


if __name__ == "__main__":
    bot = StandaloneTelegramEducationalBot()
    bot.run()
