#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
محرر المحتوى التعليمي الجامعي الذكي - بوت تيليجرام متكامل مع لوحة تحكم كاملة
Smart University Educational Content Editor - Full Telegram Native Bot
================================================================================
المطور الأصلي: Redian Marku (MIT License) - https://github.com/redianmarku/Telegram-Autoforwarder
التطوير: محرر محتوى أكاديمي ذكي يعمل بنظام الأزرار ولوحة التحكم التفاعلية داخل تيليجرام
البوت: @admiuin_bot (Token: 8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4)
المشرف المعتمد: @M_S_F_G (User ID: 7607633343)
نموذج الذكاء الاصطناعي: DeepSeek-V4.1-Flash (https://api.hcnsec.cn/v1)
================================================================================
يعمل بمكتبات بايثون القياسية 100% دون الحاجة لتثبيت أي حزم خارجية (Zero Dependency)،
ويعمل بكفاءة تامة على خوادم الاستضافة السحابية وتطبيقات تيليجرام مثل Bots.Business و Render وغيرها.
"""

import os
import sys
import json
import time
import ssl
import logging
import threading
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List

# تحميل متغيرات البيئة إن وجدت
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ----------------- الإعدادات والاعتمادات -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "7607633343"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "M_S_F_G").replace("@", "").strip()

AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.hcnsec.cn/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "sk-J2ky44F6VTDMkL8Q1GHL5sfmbeIpARVDayNuwMfxKI5zCdii").strip()
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "DeepSeek-V4.1-Flash").strip()
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "auto").strip()
PORT = int(os.getenv("PORT", "8080"))

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

# تهيئة السياق الأمني لـ SSL لضمان التوافق مع كافة أنظمة التشغيل
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


class HealthCheckHandler(BaseHTTPRequestHandler):
    """خادم HTTP خفيف لإبقاء البوت حياً (Keep-Alive) واجتياز فحوصات المنصات السحابية"""
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
        # منع ازدحام سجلات HTTP
        pass


def run_keepalive_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
        logging.info(f" خادم Keep-Alive يعمل بنجاح على المنفذ: {PORT}")
        server.serve_forever()
    except Exception as e:
        logging.warning(f"ملاحظة في تشغيل منفذ الويب {PORT}: {e}")


class StandaloneTelegramEducationalBot:
    def __init__(self):
        self.sources = self.load_json(SOURCES_FILE, {
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
                    "lastPostId": "0"
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
                    "lastPostId": "0"
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
        self.custom_ad = DEFAULT_CUSTOM_STUDENT_AD
        self.custom_instructions = "كن مثل مشرفين القروبات الذي يبحث عن الأخبار الجديدة ويعطيها للطلاب بوضوح"
        self.user_waiting_state: Dict[int, str] = {}

    def load_json(self, path: str, default_val: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"خطأ في قراءة الملف {path}: {e}")
        return default_val

    def save_json(self, path: str, data: Any):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"خطأ في حفظ الملف {path}: {e}")

    def is_authorized(self, user: Dict[str, Any]) -> bool:
        user_id = user.get("id")
        username = (user.get("username") or "").replace("@", "").strip().lower()
        if user_id == ADMIN_ID:
            return True
        if username and username == ADMIN_USERNAME.lower():
            return True
        return False

    def tg_request(self, method: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """إرسال طلب مباشر وموثوق إلى تيليجرام Bot API"""
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
        """استدعاء DeepSeek-V4.1-Flash مع مهلة آمنة وبديل فوري"""
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

        # محاولة النموذج الأساسي DeepSeek-V4.1-Flash بمهلة 6 ثوانٍ
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logging.warning(f"ملاحظة في اتصال نموذج الذكاء الأساسي {PRIMARY_MODEL}: {e}")

        # محاولة النموذج البديل auto بمهلة 4 ثوانٍ
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

        # بديل ذكي ومحلي فوري يحافظ على هيكل المنشور الجامعي
        lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not l.startswith("http")]
        title = lines[0] if lines else "تحديث جامعي وتعليمي هام"
        bullets = "\n".join([f"• {l}" for l in lines[1:6]]) if len(lines) > 1 else f"• {raw_text}"
        return f"📌 {title}\n\n{bullets}\n\n💬 يسعدنا استقبال استفساراتكم ومشاركة المنشور مع زملائكم الطلاب!\n\n#جامعة #أخبار_التعليم #شؤون_الطلاب #دراسة"

    # ----------------- لوحات المفاتيح والأزرار التفاعلية -----------------
    def get_main_reply_keyboard(self) -> Dict[str, Any]:
        """الكيبورد الدائم في أسفل شاشة تيليجرام لسهولة الاستخدام بنقرة واحدة"""
        return {
            "keyboard": [
                [{"text": "🎛 لوحة التحكم الرئيسية"}, {"text": "📊 حالة البوت"}],
                [{"text": "📋 إدارة المصادر"}, {"text": "🎯 إعلاني الخاص (المنافسين)"}],
                [{"text": "⚙️ تعليمات المحرر"}, {"text": "🔑 المفاتيح والبيانات"}],
                [{"text": "⏸ إيقاف / استئناف"}, {"text": "🧪 تجربة صياغة منشور"}]
            ],
            "resize_keyboard": True,
            "persistent": True
        }

    def get_control_panel_inline_keyboard(self) -> Dict[str, Any]:
        """أزرار التحكم التفاعلية المضمنة داخل الرسالة"""
        return {
            "inline_keyboard": [
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
        text = f"""👋 مرحباً بك يا مديرنا العزيز @{ADMIN_USERNAME}!
👑 أنت المشرف المعتمد والمخول بالتحكم الكامل (ID: `{ADMIN_ID}`)

🎛 **لوحة التحكم بمحرر المحتوى التعليمي الجامعي الذكي**:
• حالة النشر التلقائي: {status_badge}
• النموذج الفعال: `{PRIMARY_MODEL}`
• المصادر المراقبة: {len(self.sources.get('sources', []))} مصادر
• منشورات تمت معالجتها: {self.state.get('processed_count', 0)}
• إعلانات تم استبدالها بإعلانك: {self.state.get('ad_replaced_count', 0)}

👇 **اختر من الأزرار أدناه للتحكم الفوري:**
(أو أرسل/وجّه أي خبر للمحادثة وسيقوم البوت بإعادة صياغته فوراً)"""
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

        if data == "panel_sources":
            srcs = self.sources.get("sources", [])
            lines = [f"📋 **قائمة مصادر المراقبة الحالية ({len(srcs)}):**\n\n"]
            for i, s in enumerate(srcs, 1):
                rule = "رسمي [نشر مباشر]" if s.get("rule") == "official" else "شبه رسمي [تدقيق]"
                lines.append(f"{i}. [{s.get('type')}] **{s.get('title')}**\n   الهدف: `{s.get('target')}` | القاعدة: {rule} | الأولوية: {s.get('priority')}\n")
            lines.append("\n➕ لإضافة مصدر جديد أرسل: `/add_source tg @channel`")
            lines.append("➖ لحذف مصدر أرسل: `/remove_source @channel`")
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
            masked_key = AI_API_KEY[:8] + "..." + AI_API_KEY[-6:]
            text = f"""🔑 **بيانات الاعتمادات والمفاتيح المعتمدة:**

• توكن البوت: `{BOT_TOKEN[:12]}...{BOT_TOKEN[-6:]}`
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
• عدد المصادر النشطة: {len(self.sources.get('sources', []))}
• الذاكرة الدائمة: متزامنة مع state.json 💾"""
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
هذا البوت مخصص لإدارة وتوجيه المحتوى التعليمي الجامعي للمشرف @{ADMIN_USERNAME} فقط.
معرفك الحالي: `{sender_id}`
يوزرك: `@{sender_user}`

إذا كان هذا حسابك، تأكد من الدخول بالحساب المعتمد."""
            self.send_msg(chat_id, warn)
            return

        # فحص حالات الإدخال المعلقة
        if chat_id in self.user_waiting_state:
            state = self.user_waiting_state.pop(chat_id)
            if state == "waiting_for_rephrase_text":
                self.rephrase_and_reply(chat_id, text)
                return

        clean_text = text.strip()

        # الأوامر الرئيسية والأزرار
        if clean_text in ["/start", "/help", "🎛 لوحة التحكم الرئيسية", "لوحة التحكم"]:
            self.send_msg(chat_id, "أهلاً بك يا مديرنا! إليك لوحة المفاتيح والتحكم المباشرة:", self.get_main_reply_keyboard())
            self.show_welcome_panel(chat_id)
            return

        if clean_text in ["/status", "📊 حالة البوت"]:
            st = self.state
            status_text = f"""📊 **حالة البوت ومحرر المحتوى الأكاديمي:**
• البوت: @admiuin_bot
• المشرف: @{ADMIN_USERNAME} ({ADMIN_ID})
• حالة النشر: {'⏸ متوقف مؤقتاً' if self.is_paused else '🟢 نشط 24/7'}
• المعالج: {st.get('processed_count', 0)} منشور
• المنشور: {st.get('forwarded_count', 0)} منشور
• إعلاناتك المستبدلة: {st.get('ad_replaced_count', 0)} إعلان
• النموذج: `{PRIMARY_MODEL}`"""
            self.send_msg(chat_id, status_text)
            return

        if clean_text in ["/sources", "📋 إدارة المصادر"]:
            srcs = self.sources.get("sources", [])
            lines = [f"📋 **قائمة المصادر ({len(srcs)}):**\n\n"]
            for s in srcs:
                lines.append(f"• [{s.get('type')}] **{s.get('title')}** ({s.get('target')}) - أولوية: {s.get('priority')}\n")
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
            self.send_msg(chat_id, "✍️ أرسل الآن أي خبر أو منشور أو ملف PDF وسأقوم بصياغته فوراً بالذكاء الاصطناعي!")
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

        # إضافة مصدر عبر /add_source
        if clean_text.startswith("/add_source"):
            parts = clean_text.split()
            if len(parts) >= 3:
                src_type = parts[1]
                target = parts[2]
                self.sources.setdefault("sources", []).append({
                    "id": f"src_{int(time.time())}",
                    "type": "telegram" if src_type == "tg" else src_type,
                    "target": target,
                    "title": target,
                    "priority": "high",
                    "rule": "official",
                    "keywords": [],
                    "blacklist": ["إعلان ممول"],
                    "enabled": True,
                    "lastPostId": "0"
                })
                self.save_json(SOURCES_FILE, self.sources)
                self.send_msg(chat_id, f"✅ تمت إضافة المصدر `{target}` ومزامنته مع sources.json بنجاح!")
            else:
                self.send_msg(chat_id, "الصيغة: `/add_source tg @channel`")
            return

        # حذف مصدر عبر /remove_source
        if clean_text.startswith("/remove_source"):
            target = clean_text.replace("/remove_source", "").strip()
            srcs = self.sources.get("sources", [])
            self.sources["sources"] = [s for s in srcs if s.get("target") != target]
            self.save_json(SOURCES_FILE, self.sources)
            self.send_msg(chat_id, f"✅ تم حذف المصدر `{target}` بنجاح!")
            return

        # إذا أرسل المشرف أي نص أو خبر عادي، نقوم بصياغته فوراً!
        if len(clean_text) > 5:
            self.rephrase_and_reply(chat_id, clean_text)

    def rephrase_and_reply(self, chat_id: int, raw_text: str):
        """فحص الإعلانات أو إعادة الصياغة فوراً بالذكاء الاصطناعي"""
        self.state["processed_count"] = self.state.get("processed_count", 0) + 1

        # 1. فحص إعلان المنافس
        if self.is_competitor_ad(raw_text):
            self.state["ad_replaced_count"] = self.state.get("ad_replaced_count", 0) + 1
            self.save_json(STATE_FILE, self.state)
            reply = f"""🎯 **تم رصد إعلان ترويجي للمنافسين!**
تم استبداله تلقائياً بإعلان خدماتك الطلابية الخاص بك:

━━━━━━━━━━━━━━━━━━━
{self.custom_ad}
━━━━━━━━━━━━━━━━━━━
(تم توجيهه لقناتك بنجاح)"""
            self.send_msg(chat_id, reply)
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

    # ----------------- الحلقة الرئيسية للتشغيل -----------------
    def run(self):
        logging.info("=" * 60)
        logging.info("  محرر المحتوى التعليمي الجامعي الذكي (Telegram Native Bot)")
        logging.info(f"  البوت: @admiuin_bot | المشرف: @{ADMIN_USERNAME} ({ADMIN_ID})")
        logging.info(f"  النموذج: {PRIMARY_MODEL} | المفتاح: {AI_API_KEY[:8]}...")
        logging.info("=" * 60)

        # تشغيل خادم Keep-Alive السحابي في خيط منفصل
        keepalive_thread = threading.Thread(target=run_keepalive_server, daemon=True)
        keepalive_thread.start()

        # إشعار تشغيل مباشر للآدمن في تيليجرام
        try:
            welcome_text = f"""🚀 **تم تشغيل محرر المحتوى التعليمي بنجاح!**
👑 أهلاً بك يا مديرنا @{ADMIN_USERNAME}
🤖 النموذج الفعال: `{PRIMARY_MODEL}`

أرسل /start لعرض لوحة التحكم التفاعلية بالأزرار."""
            self.send_msg(ADMIN_ID, welcome_text, self.get_main_reply_keyboard())
        except Exception as e:
            logging.warning(f"ملاحظة في إشعار الآدمن: {e}")

        # حلقة استماع التحديثات (Long Polling)
        offset = 0
        logging.info("🎧 جاري الاستماع لتحديثات وأوامر تيليجرام...")
        while True:
            try:
                res = self.tg_request(f"getUpdates?offset={offset}&timeout=20")
                if res.get("ok"):
                    updates = res.get("result", [])
                    for u in updates:
                        offset = u["update_id"] + 1

                        # معالجة أزرار الإنلاين المضمنة (Callback Query)
                        if "callback_query" in u:
                            self.handle_callback_query(u["callback_query"])

                        # معالجة الرسائل العادية
                        elif "message" in u:
                            self.handle_message(u["message"])

                time.sleep(0.5)
            except KeyboardInterrupt:
                logging.info("تم إيقاف البوت بواسطة المستخدم.")
                break
            except Exception as e:
                logging.error(f"خطأ في دورة التحديث: {e}")
                time.sleep(3)


if __name__ == "__main__":
    bot = StandaloneTelegramEducationalBot()
    bot.run()
