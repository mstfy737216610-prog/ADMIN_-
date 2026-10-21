#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
محرر المحتوى التعليمي الجامعي الذكي - النسخة الإنتاجية المتقدمة (Native Bot)
Telegram University Educational Content Editor & Publisher
================================================================================
المطور الأصلي: Redian Marku (MIT License) - https://github.com/redianmarku/Telegram-Autoforwarder
المشرف المعتمد: @M_S_F_G (معرف: 7607633343)
توكن البوت: 8901693218:AAEOQmHMZLy-xaPbTUMq1KGhDwp1l0wFWP4
الذكاء الاصطناعي: DeepSeek-V4.1-Flash (https://api.hcnsec.cn/v1)
================================================================================
المميزات المتقدمة:
1. منع تكرار أو نشر أي منشورات قديمة نهائياً (Baseline initialization & Hash tracking).
2. استخراج ونشر الصور الأصلية بدقة عالية عبر sendPhoto مباشرة في القناة.
3. منع ذكر اسم المصدر أو القناة الأصلية أو أي عبارة تشير للنسخ (كتابة المنشور كأنه حصري وأصلي 100%).
4. فلترة وحذف كافة معرفات وروابط القنوات المنافسة واستبدال إعلاناتهم بإعلان المشرف الخاص @M_S_F_G.
5. خادم Keep-Alive ومكتبات قياسية 100% دون الحاجة لأي مكتبات خارجية (Zero Dependency).
"""

import os
import sys
import json
import time
import ssl
import re
import hashlib
import logging
import threading
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List, Tuple

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

# برومبت صارم لمنع ذكر المصدر ولجعل المنشور أصلياً وحصرياً
SYSTEM_PROMPT_REPHRASE = """# الدور: الناشر والكاتب الرسمي للمحتوى التعليمي والجامعي
## الهوية:
أنت الكاتب الرسمي والناشر الحصري لقناة تعليمية وجامعية رائدة.
مهمتك كتابة وصياغة المنشورات بأسلوبك الخاص الأصيل كأنك أنت المصدر الأول والأساسي للخبر.

## قواعد صارمة جداً (إلزامية 100%):
1. ممنوع منعاً باتاً ذكر اسم القناة الأصلية أو المصدر أو الحساب المنقول منه، وممنوع استخدام عبارات مثل "وفقاً للمصدر" أو "بحسب القناة" أو "معاد صياغته" أو "كما ورد" أو أي تنويه بأن المنشور منقول.
2. احذف نهائياً أي روابط أو معرفات قنوات تيليجرام أخرى (مثل @channel أو t.me).
3. اكتب بأسلوب عربي فصيح، راقٍ، منظم بنقاط واضحة ومباشرة للطلاب.
4. حافظ بدقة تامة على الأرقام، النسب، التواريخ، والمواعيد الرسمية، والشروط دون أي تحريف.
5. احتفظ فقط بالروابط الحكومية والجامعية الرسمية المباشرة (مثل مواقع الجامعات الرسمية أو الوزارة).

## التنسيق المطلوب:
📌 [عنوان بارز وجذاب بدون أي إشارة لمصادر]

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
            "target_channel": "",
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
            "seen_post_ids": [],
            "seen_hashes": []
        })
        self.is_paused = False
        self.target_channel = self.sources.get("target_channel", "")
        self.custom_ad = DEFAULT_CUSTOM_STUDENT_AD
        self.custom_instructions = "كن مثل مشرفين القروبات الذي يبحث عن الأخبار الجديدة ويعطيها للطلاب بوضوح دون أي إشارة للمصادر"
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
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logging.error(f"خطأ تيليجرام ({method}): {e.code} - {err_body}")
            return {"ok": False, "description": err_body}
        except Exception as e:
            logging.error(f"خطأ في طلب تيليجرام ({method}): {e}")
            return {"ok": False, "description": str(e)}

    def send_msg(self, chat_id: Any, text: str, reply_markup: Optional[Dict] = None, parse_mode: Optional[str] = None) -> Dict[str, Any]:
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return self.tg_request("sendMessage", payload)

    def send_photo(self, chat_id: Any, photo: str, caption: str = "", parse_mode: Optional[str] = None) -> Dict[str, Any]:
        """إرسال صورة مباشرة مع الشرح إلى القناة أو المحادثة"""
        # حد تليجرام للشرح في الصور هو 1024 حرفاً
        if len(caption) <= 1024:
            payload = {"chat_id": chat_id, "photo": photo, "caption": caption}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            res = self.tg_request("sendPhoto", payload)
            if res.get("ok"):
                return res

        # إذا تعذر أو كان الشرح طويلاً، نرسل الصورة ثم النص كاملاً
        res_photo = self.tg_request("sendPhoto", {"chat_id": chat_id, "photo": photo})
        if caption:
            self.send_msg(chat_id, caption, parse_mode=parse_mode)
        return res_photo

    def answer_callback(self, cb_id: str, text: Optional[str] = None):
        payload = {"callback_query_id": cb_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = False
        return self.tg_request("answerCallbackQuery", payload)

    def is_competitor_ad(self, text: str) -> bool:
        return any(kw in text for kw in AD_KEYWORDS)

    def clean_text_from_sources(self, text: str) -> str:
        """تنظيف كامل لأي إشارات للمصادر أو القنوات الأصلية برمجياً"""
        # إزالة معرفات تيليجرام (@channel)
        cleaned = re.sub(r'@[a-zA-Z0-9_]+', '', text)
        # إزالة روابط تيليجرام (t.me/...)
        cleaned = re.sub(r'https?://t\.me/[^\s]+', '', cleaned)
        # إزالة عبارات الترويج للمصادر
        cleaned = re.sub(r'(وفقاً لـ?|بحسب|نقلاً عن|المصدر:|قناة|حساب)\s+[^\s\n]+', '', cleaned)
        cleaned = re.sub(r'لا تنسوا الاشتراك[^\n.]*', '', cleaned)
        cleaned = re.sub(r'تابعونا على[^\n.]*', '', cleaned)
        cleaned = re.sub(r'انضموا إلى[^\n.]*', '', cleaned)
        # إزالة الأسطر الفارغة الزائدة
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        return cleaned

    def call_ai(self, raw_text: str, custom_instruction: str = "") -> str:
        """إعادة صياغة ذكية بالذكاء الاصطناعي مع منع ذكر المصدر نهائياً"""
        clean_input = self.clean_text_from_sources(raw_text)

        url = f"{AI_BASE_URL}/chat/completions"
        instruction_addon = f"تعليمات إضافية من المشرف: {custom_instruction}\n\n" if custom_instruction else ""
        payload = {
            "model": PRIMARY_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_REPHRASE},
                {"role": "user", "content": f"{instruction_addon}صيغ هذا المحتوى الأكاديمي كمنشور رسمي أصلي لقناتك (بدون ذكر أي مصادر أو قنوات سابقة):\n{clean_input}"}
            ],
            "temperature": 0.35,
            "max_tokens": 700
        }
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TelegramEducationalBot/2.0"
        }

        # 1. محاولة DeepSeek-V4.1-Flash
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    ai_text = data["choices"][0]["message"]["content"].strip()
                    # تنظيف نهائي لأي تسرب للمصدر
                    return self.clean_text_from_sources(ai_text)
        except Exception as e:
            logging.warning(f"ملاحظة في اتصال نموذج الذكاء الأساسي {PRIMARY_MODEL}: {e}")

        # 2. محاولة النموذج البديل auto
        try:
            payload["model"] = FALLBACK_MODEL
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    ai_text = data["choices"][0]["message"]["content"].strip()
                    return self.clean_text_from_sources(ai_text)
        except Exception as e:
            logging.warning(f"ملاحظة في اتصال النموذج البديل {FALLBACK_MODEL}: {e}")

        # 3. صياغة محلية ذكية وأصلية (بدون أي ذكر للمصدر)
        lines = [l.strip() for l in clean_input.split("\n") if l.strip() and not l.startswith("http")]
        title = lines[0] if lines else "تحديث جامعي وأكاديمي هام"
        bullets = "\n".join([f"• {l}" for l in lines[1:6]]) if len(lines) > 1 else f"• {clean_input}"
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
• دعم الصور: ✅ مفعل لنشر الصور الأصلية بدقة عالية
• حماية الهوية: ✅ ممنوع ذكر أي مصادر أو معرفات سابقة
• النموذج الفعال: `{PRIMARY_MODEL}`
• المصادر المراقبة: {len(self.sources.get('sources', []))} مصادر
• منشورات تمت معالجتها: {self.state.get('processed_count', 0)}
• إعلانات تم استبدالها بإعلانك: {self.state.get('ad_replaced_count', 0)}

👇 **اختر من الأزرار أدناه للتحكم السريع:**
(أو أرسل/وجّه أي خبر أو صورة للمحادثة وسيتم صياغتها ونشرها فوراً)"""
        self.send_msg(chat_id, text, self.get_control_panel_inline_keyboard())

    def handle_callback_query(self, cb: Dict[str, Any]):
        cb_id = cb["id"]
        from_user = cb["from"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")

        if not self.is_authorized(from_user):
            self.answer_callback(cb_id, "⛔️ غير مصرح لك.")
            return

        self.answer_callback(cb_id)

        if data == "panel_add_source":
            self.user_waiting_state[chat_id] = "waiting_for_new_source"
            ask_text = """➕ **إضافة قناة أو رابط جديد للمراقبة:**

أرسل الآن معرّف أو رابط المصدر:
• **قناة تيليجرام:** `@KSU_News` أو `https://t.me/KSU_News`
• **موقع أخبار جامعي (RSS):** `https://news.ksu.edu.sa/rss.xml`
• **حساب تويتر/X:** `@moe_gov_sa` أو `https://x.com/moe_gov_sa`

سيتعرف البوت تلقائياً على الرابط ويبدأ المراقبة دون نشر أي منشورات قديمة!"""
            self.send_msg(chat_id, ask_text)

        elif data == "panel_set_channel":
            self.user_waiting_state[chat_id] = "waiting_for_target_channel"
            ask_text = """📢 **تحديد قناتك لنشر المحتوى التلقائي والصور:**

أرسل الآن معرّف أو رابط قناتك (مثال: `@MyUniversityChannel` أو `https://t.me/MyUniversityChannel`):

⚠️ **تأكد من:**
1. إضافة البوت (@admiuin_bot) كـ **مشرف (Admin)** في القناة.
2. تفعيل صلاحية نشر الرسائل والصور."""
            self.send_msg(chat_id, ask_text)

        elif data == "panel_sources":
            srcs = self.sources.get("sources", [])
            lines = [f"📋 **قائمة المصادر المراقبة ({len(srcs)}):**\n\n"]
            for i, s in enumerate(srcs, 1):
                rule = "رسمي" if s.get("rule") == "official" else "شبه رسمي"
                lines.append(f"{i}. [{s.get('type')}] **{s.get('title')}**\n   الهدف: `{s.get('target')}` | القاعدة: {rule} | الأولوية: {s.get('priority')}\n")
            lines.append("\n➕ لإضافة مصدر اضغط زر: `➕ إضافة قناة أو رابط`")
            lines.append("➖ لحذف أي مصدر أرسل: `/remove_source @channel`")
            self.send_msg(chat_id, "".join(lines))

        elif data == "panel_ad":
            text = f"""🎯 **نظام استبدال إعلانات المنافسين بإعلاناتك:**
عندما تنشر أي قناة إعلاناً لخدمات طلابية أو حل واجبات، يستبدله البوت تلقائياً بهذا المنشور في قناتك:

━━━━━━━━━━━━━━━━━━━
{self.custom_ad}
━━━━━━━━━━━━━━━━━━━

✏️ لتعديل هذا الإعلان أرسل:
`/set_ad النص الجديد هنا`"""
            self.send_msg(chat_id, text)

        elif data == "panel_instructions":
            text = f"""⚙️ **تعليمات المشرف المخصصة:**
📌 *\"{self.custom_instructions}\"*

✏️ لتعديل التعليمات، أرسل:
`/set_instruction تعليماتك الجديدة هنا`"""
            self.send_msg(chat_id, text)

        elif data == "panel_keys":
            text = f"""🔑 **بيانات الاعتمادات والمفاتيح المعتمدة:**
• توكن البوت: `{BOT_TOKEN}`
• يوزر البوت: @admiuin_bot
• المشرف: @{ADMIN_USERNAME} (`{ADMIN_ID}`)
• عنوان API: `{AI_BASE_URL}`
• النموذج الأساسي: `{PRIMARY_MODEL}`
• مفتاح الذكاء: `{AI_API_KEY}`
• القناة الناشرة: `{self.target_channel or 'لم تحدد'}`"""
            self.send_msg(chat_id, text)

        elif data == "panel_toggle_pause":
            self.is_paused = not self.is_paused
            state_str = "⏸ تم إيقاف النشر مؤقتاً." if self.is_paused else "▶️ تم استئناف النشر التلقائي بنجاح!"
            self.send_msg(chat_id, state_str, self.get_control_panel_inline_keyboard())

        elif data == "panel_stats":
            st = self.state
            text = f"""📊 **إحصائيات الأداء والمراقبة:**
• إجمالي المنشورات المعالجة: {st.get('processed_count', 0)}
• المنشورات الصادرة لقناتك: {st.get('forwarded_count', 0)}
• إعلانات تم استبدالها بإعلانك: {st.get('ad_replaced_count', 0)}
• القناة الناشرة: `{self.target_channel or 'لم تُحدد'}`
• النشر مع الصور: مفعل تلقائياً 📸"""
            self.send_msg(chat_id, text)

        elif data == "panel_test":
            self.user_waiting_state[chat_id] = "waiting_for_rephrase_text"
            self.send_msg(chat_id, "✍️ أرسل الآن أي منشور أو صورة، وسأقوم بصياغتها ونشرها فوراً بدون أي ذكر للمصدر!")

    def handle_message(self, msg: Dict[str, Any]):
        chat_id = msg["chat"]["id"]
        from_user = msg.get("from", {})
        text = msg.get("text", "") or msg.get("caption", "")

        # استخراج الصورة المرفقة إن وجدت
        photo_id = None
        if "photo" in msg and isinstance(msg["photo"], list) and len(msg["photo"]) > 0:
            # نأخذ أعلى جودة للصورة (آخر عنصر في المصفوفة)
            photo_id = msg["photo"][-1]["file_id"]

        logging.info(f"رسالة واردة من {from_user.get('id')} (@{from_user.get('username')}): {text[:60]}")

        # التحقق من صلاحية المشرف
        if not self.is_authorized(from_user):
            sender_id = from_user.get("id")
            sender_user = from_user.get("username") or "غير محدد"
            warn = f"""⛔️ مرحباً بك!
هذا البوت مخصص لإدارة ونشر المحتوى التعليمي للمشرف @{ADMIN_USERNAME}.
معرفك الحالي: `{sender_id}`
يوزرك: `@{sender_user}`"""
            self.send_msg(chat_id, warn)
            return

        clean_text = text.strip()

        # معالجة الحالات المنتظرة
        if chat_id in self.user_waiting_state:
            state = self.user_waiting_state.pop(chat_id)

            if state == "waiting_for_new_source":
                self.process_add_source_input(chat_id, clean_text)
                return

            if state == "waiting_for_target_channel":
                self.set_and_verify_target_channel(chat_id, clean_text)
                return

            if state == "waiting_for_rephrase_text":
                self.rephrase_and_dispatch(chat_id, clean_text, photo_id)
                return

        # الأزرار والأوامر الرئيسية
        if clean_text in ["/start", "/help", "🎛 لوحة التحكم الرئيسية", "لوحة التحكم"]:
            self.send_msg(chat_id, "أهلاً بك يا مديرنا! إليك لوحة التحكم الفورية:", self.get_main_reply_keyboard())
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
• القناة الناشرة: `{self.target_channel or 'لم تُحدد بعد'}`
• دعم الصور: ✅ مفعل لنشر الصور الأصلية
• حماية المصدر: ✅ لا يتم ذكر أي مصدر أصلي نهائياً
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
• مفتاح الذكاء الاصطناعي: `{AI_API_KEY}`
• القناة الناشرة: `{self.target_channel or 'لم تحدد'}`"""
            self.send_msg(chat_id, keys_text)
            return

        if clean_text in ["⏸ إيقاف / استئناف", "إيقاف"]:
            self.is_paused = not self.is_paused
            self.send_msg(chat_id, f"{'⏸ تم إيقاف النشر مؤقتاً.' if self.is_paused else '▶️ تم استئناف النشر التلقائي.'}")
            return

        if clean_text in ["🧪 تجربة صياغة منشور", "تجربة"]:
            self.user_waiting_state[chat_id] = "waiting_for_rephrase_text"
            self.send_msg(chat_id, "✍️ أرسل الآن أي خبر أو منشور أو صورة وسأقوم بصياغتها ونشرها بدون ذكر المصدر!")
            return

        # تعديل الإعلان
        if clean_text.startswith("/set_ad"):
            new_ad = clean_text.replace("/set_ad", "").strip()
            if new_ad:
                self.custom_ad = new_ad
                self.send_msg(chat_id, "✅ تم حفظ وتحديث إعلان خدماتك الطلابية الخاص بك بنجاح!")
            else:
                self.send_msg(chat_id, "يرجى كتابة نص الإعلان بعد الأمر، مثال:\n`/set_ad إعلانك هنا`")
            return

        # تعديل التعليمات
        if clean_text.startswith("/set_instruction"):
            new_ins = clean_text.replace("/set_instruction", "").strip()
            if new_ins:
                self.custom_instructions = new_ins
                self.send_msg(chat_id, "✅ تم حفظ تعليمات المشرف بنجاح!")
            else:
                self.send_msg(chat_id, "يرجى كتابة نص التعليمات بعد الأمر.")
            return

        # حذف مصدر
        if clean_text.startswith("/remove_source"):
            target = clean_text.replace("/remove_source", "").strip()
            srcs = self.sources.get("sources", [])
            self.sources["sources"] = [s for s in srcs if s.get("target") != target and s.get("target") != "@" + target.replace("@", "")]
            self.save_json(SOURCES_FILE, self.sources)
            self.send_msg(chat_id, f"✅ تم حذف المصدر `{target}` بنجاح!")
            return

        # إضافة مصدر مباشر من الرابط
        if clean_text.startswith("@") and not photo_id and len(clean_text.split()) == 1:
            self.process_add_source_input(chat_id, clean_text)
            return

        # معالجة أي نص أو منشور أو صورة واردة وإرسالها فوراً
        if len(clean_text) > 5 or photo_id:
            self.rephrase_and_dispatch(chat_id, clean_text, photo_id)

    def set_and_verify_target_channel(self, chat_id: int, channel_input: str):
        target = channel_input.replace("https://t.me/", "").strip()
        if not target.startswith("@") and not target.startswith("-100"):
            target = "@" + target

        # التحقق من القناة وصلاحيات البوت فيها
        check = self.tg_request("getChat", {"chat_id": target})
        if check.get("ok"):
            chat_info = check.get("result", {})
            ch_title = chat_info.get("title", target)
            self.target_channel = target
            self.sources["target_channel"] = target
            self.save_json(SOURCES_FILE, self.sources)

            reply = f"""✅ **تم ربط قناتك بنجاح!**
📢 القناة: **{ch_title}** (`{target}`)
📸 ميزة نشر الصور: مفعلة وتلقائية.
🔒 حماية الهوية: يتم النشر بدون أي ذكر للمصادر المنقول منها.

أي منشور جديد يتم رصده أو توجيهه سيتم نشره فوراً داخل هذه القناة!"""
            self.send_msg(chat_id, reply, self.get_main_reply_keyboard())
        else:
            # إذا تعذر، نحفظه وننبه المشرف بإضافة البوت مشرفاً
            self.target_channel = target
            self.sources["target_channel"] = target
            self.save_json(SOURCES_FILE, self.sources)
            warn = f"""⚠️ **تم حفظ القناة: `{target}`**
يرجى التأكد من إضافة البوت (@admiuin_bot) كـ **مشرف (Admin)** في القناة مع تفعيل صلاحية نشر الرسائل والصور ليتمكن من النشر التلقائي بنجاح."""
            self.send_msg(chat_id, warn, self.get_main_reply_keyboard())

    def process_add_source_input(self, chat_id: int, input_str: str):
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
            target = f"@{input_str}"
            src_type = "telegram"
            title = f"قناة تيليجرام {target}"

        # فحص المعرف الحالي لمنع نشر الأرشيف القديم
        initial_last_id = ""
        if src_type == "telegram":
            ch_name = target.replace("@", "")
            try:
                url = f"https://t.me/s/{ch_name}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, context=ssl_ctx, timeout=8) as resp:
                    html = resp.read().decode("utf-8")
                    matches = re.findall(r'data-post=\"([^\"]+)\"', html)
                    if matches:
                        initial_last_id = matches[-1]
            except Exception:
                pass

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
            "lastPostId": initial_last_id  # تثبيت المنشور الأحدث فوراً حتى لا يعيد نشر القديم!
        }

        self.sources.setdefault("sources", []).append(new_entry)
        self.save_json(SOURCES_FILE, self.sources)

        confirm_msg = f"""✅ **تم ربط المصدر بنجاح!**
• النوع: `[{src_type}]`
• الهدف: `{target}`
• العنوان: {title}
• نقطة البداية: تم تثبيتها عند آخر منشور حالي (لن يتم تكرار أو نشر أي منشورات قديمة 🛡)

سيقوم البوت بمراقبة الجديد فقط ونشره في قناتك فور صدوره!"""
        self.send_msg(chat_id, confirm_msg, self.get_main_reply_keyboard())

    def rephrase_and_dispatch(self, chat_id: int, raw_text: str, photo: Optional[str] = None):
        """صياغة المنشور ونشره في القناة دون ذكر أي مصدر أو تنويه بالنقل"""
        self.state["processed_count"] = self.state.get("processed_count", 0) + 1

        # 1. فحص إعلان المنافس
        if raw_text and self.is_competitor_ad(raw_text):
            self.state["ad_replaced_count"] = self.state.get("ad_replaced_count", 0) + 1
            self.save_json(STATE_FILE, self.state)

            # النشر في القناة إن وجدت
            if self.target_channel:
                if photo:
                    self.send_photo(self.target_channel, photo, self.custom_ad)
                else:
                    self.send_msg(self.target_channel, self.custom_ad)

            # إشعار للمشرف في الخاص
            reply = f"""🎯 **تم رصد إعلان ترويجي للمنافسين!**
تم استبداله تلقائياً ونشر إعلان خدماتك الطلابية الخاص بك:

━━━━━━━━━━━━━━━━━━━
{self.custom_ad}
━━━━━━━━━━━━━━━━━━━
📢 تم النشر في: `{self.target_channel or 'لم تحدد قناة'}`"""
            self.send_msg(chat_id, reply)
            return

        # 2. الصياغة بالذكاء الاصطناعي (منشور أصلي وحصري بدون أي ذكر للمصدر)
        self.send_msg(chat_id, "⏳ جاري الصياغة الأكاديمية الذكية والنشر الحصري...")
        rephrased = self.call_ai(raw_text or "إعلان جامعي هام", self.custom_instructions)

        self.state["forwarded_count"] = self.state.get("forwarded_count", 0) + 1
        self.save_json(STATE_FILE, self.state)

        # 3. النشر داخل القناة مباشرة (المحتوى النقي فقط + الصورة إن وجدت)
        published_to_channel = False
        if self.target_channel:
            if photo:
                res = self.send_photo(self.target_channel, photo, rephrased)
                published_to_channel = res.get("ok", False)
            else:
                res = self.send_msg(self.target_channel, rephrased)
                published_to_channel = res.get("ok", False)

        # 4. إشعار المشرف في الخاص مع المعاينة
        status_note = f"✅ تم النشر في قناتك `{self.target_channel}` بنجاح 📸" if published_to_channel else "⚠️ المنشور جاهز (حدد قناتك عبر زر 'تحديد قناتي للنشر' ليتم النشر التلقائي)"
        result_msg = f"""✨ **المنشور التعليمي (أصلي وحصري 100%):**
━━━━━━━━━━━━━━━━━━━
{rephrased}
━━━━━━━━━━━━━━━━━━━
{status_note}"""

        if photo and not published_to_channel:
            self.send_photo(chat_id, photo, result_msg)
        else:
            self.send_msg(chat_id, result_msg)

    # ----------------- مراقب المصادر الآلي في الخلفية -----------------
    def monitor_sources_loop(self):
        """فحص دوري للمصادر وسحب الجديد فقط مع الصورة ونشره في القناة دون أي أثر للمصدر"""
        logging.info("🚀 تشغيل مراقب المصادر التلقائي ومنع المنشورات القديمة...")
        while True:
            try:
                time.sleep(50)
                if self.is_paused:
                    continue

                srcs = self.sources.get("sources", [])
                for s in srcs:
                    if not s.get("enabled", True):
                        continue

                    s_type = s.get("type")
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

                # تقسيم المنشورات حسب الكتل
                blocks = html.split('class="tgme_widget_message_wrap')
                if len(blocks) <= 1:
                    return

                # استخراج كافة المنشورات الصالحة
                posts_extracted = []
                for b in blocks[1:]:
                    post_id_m = re.search(r'data-post=\"([^\"]+)\"', b)
                    if not post_id_m:
                        continue
                    pid = post_id_m.group(1)

                    photo_m = re.search(r'background-image:url\(\'([^\']+)\'\)', b)
                    photo_url = photo_m.group(1) if photo_m else None

                    text_m = re.search(r'class=\"tgme_widget_message_text[^\"]*js-message_text\"[^>]*>(.*?)</div>', b, re.DOTALL)
                    text_content = ""
                    if text_m:
                        raw_h = text_m.group(1)
                        clean_h = re.sub(r'<br\s*/?>', '\n', raw_h)
                        text_content = re.sub(r'<[^>]+>', '', clean_h).strip()

                    posts_extracted.append({"id": pid, "photo": photo_url, "text": text_content})

                if not posts_extracted:
                    return

                latest_post = posts_extracted[-1]
                latest_post_id = latest_post["id"]
                last_known = src.get("lastPostId", "")

                # 🛑 قاعدة ذهبية: إذا كان المصدر جديداً أو لم يُحدد له lastPostId، نثبته حالاً ونمنع نشر القديم!
                if not last_known:
                    src["lastPostId"] = latest_post_id
                    self.save_json(SOURCES_FILE, self.sources)
                    logging.info(f"تمت تهيئة المصدر {src.get('target')} عند المنشور الأخير {latest_post_id} - لن يتم نشر منشورات قديمة.")
                    return

                # إذا وصل منشور جديد بعد النقطة المحفوظة
                if latest_post_id != last_known:
                    seen_keys = self.state.setdefault("seen_post_ids", [])
                    post_hash = hashlib.md5((latest_post.get("text", "")[:80]).encode("utf-8")).hexdigest()
                    seen_hashes = self.state.setdefault("seen_hashes", [])

                    # فحص مانع التكرار
                    if latest_post_id in seen_keys or post_hash in seen_hashes:
                        src["lastPostId"] = latest_post_id
                        self.save_json(SOURCES_FILE, self.sources)
                        return

                    # تحديث المعرف وسجل المشاهدة
                    src["lastPostId"] = latest_post_id
                    seen_keys.append(latest_post_id)
                    seen_hashes.append(post_hash)
                    if len(seen_keys) > 500:
                        seen_keys.pop(0)
                    if len(seen_hashes) > 500:
                        seen_hashes.pop(0)

                    self.save_json(SOURCES_FILE, self.sources)
                    self.save_json(STATE_FILE, self.state)

                    logging.info(f"⚡️ منشور جديد حقيقي تم رصده في {src.get('target')}: {latest_post_id}")
                    self.publish_fresh_post(latest_post.get("text", ""), latest_post.get("photo"))

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
                    last_known = src.get("lastPostId", "")

                    if not last_known:
                        src["lastPostId"] = post_id
                        self.save_json(SOURCES_FILE, self.sources)
                        return

                    if post_id != last_known:
                        src["lastPostId"] = post_id
                        self.save_json(SOURCES_FILE, self.sources)
                        clean_desc = re.sub(r'<[^>]+>', '', desc).strip()
                        post_text = f"{title}\n{clean_desc}"
                        self.publish_fresh_post(post_text, None)
        except Exception as e:
            logging.debug(f"فحص RSS {url}: {e}")

    def publish_fresh_post(self, raw_text: str, photo_url: Optional[str] = None):
        """نشر المنشور الحصري الجديد في القناة بدون أي اسم مصدر أو إشارة للنقل"""
        self.state["processed_count"] = self.state.get("processed_count", 0) + 1

        # 1. فحص إعلان المنافسين
        if raw_text and self.is_competitor_ad(raw_text):
            self.state["ad_replaced_count"] = self.state.get("ad_replaced_count", 0) + 1
            self.save_json(STATE_FILE, self.state)

            if self.target_channel:
                if photo_url:
                    self.send_photo(self.target_channel, photo_url, self.custom_ad)
                else:
                    self.send_msg(self.target_channel, self.custom_ad)

            notif = f"🎯 **تم رصد إعلان منافس واستبداله بإعلانك تلقائياً في قناتك!**\n\n{self.custom_ad}"
            self.send_msg(ADMIN_ID, notif)
            return

        # 2. الصياغة الاحترافية الحصرية
        clean_rephrased = self.call_ai(raw_text, self.custom_instructions)

        self.state["forwarded_count"] = self.state.get("forwarded_count", 0) + 1
        self.save_json(STATE_FILE, self.state)

        # 3. النشر المباشر في القناة (منشور أصلي نقي مع الصورة)
        if self.target_channel:
            if photo_url:
                self.send_photo(self.target_channel, photo_url, clean_rephrased)
            else:
                self.send_msg(self.target_channel, clean_rephrased)

        # 4. تنبيه الآدمن في الخاص بنجاح النشر
        admin_notif = f"""📢 **تم النشر الحصري في قناتك `{self.target_channel or 'لم تحدد'}`:**
━━━━━━━━━━━━━━━━━━━
{clean_rephrased}
━━━━━━━━━━━━━━━━━━━"""
        if photo_url and not self.target_channel:
            self.send_photo(ADMIN_ID, photo_url, admin_notif)
        else:
            self.send_msg(ADMIN_ID, admin_notif)

    # ----------------- تشغيل البوت -----------------
    def run(self):
        logging.info("=" * 60)
        logging.info("  محرر المحتوى التعليمي الجامعي الذكي (النسخة الأصلية الحصرية)")
        logging.info(f"  البوت: @admiuin_bot | المشرف: @{ADMIN_USERNAME} ({ADMIN_ID})")
        logging.info(f"  النموذج: {PRIMARY_MODEL} | القناة: {self.target_channel or 'لم تحدد'}")
        logging.info("=" * 60)

        # تشغيل خادم Keep-Alive
        threading.Thread(target=run_keepalive_server, daemon=True).start()

        # تشغيل مراقب المصادر التلقائي
        threading.Thread(target=self.monitor_sources_loop, daemon=True).start()

        # إشعار تشغيل للمشرف
        try:
            welcome_text = f"""🚀 **تم تشغيل محرر المحتوى التعليمي بنجاح!**
👑 المشرف المعتمد: @{ADMIN_USERNAME} (معرف: `{ADMIN_ID}`)
📢 القناة الناشرة: `{self.target_channel or 'لم تُحدد بعد (اضغط زر تحديد قناتي)'}`
📸 دعم نشر الصور: مفعل بدقة عالية 
🛡 منع المنشورات القديمة: مفعل بدقة
🔒 حماية الهوية والمصدر: مفعل بنسبة 100% (بدون أي ذكر للمصادر المنقول منها)

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
