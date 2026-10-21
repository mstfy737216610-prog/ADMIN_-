/*CMD
  command: /sources
  help: عرض وإدارة القنوات المصدرية
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: المصادر, القنوات المصدرية
CMD*/

var inline_keyboard = [
  [
    { title: "🔄 فحص المصادر الآن", command: "/status" },
    { title: "🔙 القائمة الرئيسية", command: "/start" }
  ]
];

var text = "📋 *القنوات والمصادر المراقبة حالياً:*\n\n" +
  "1️⃣ `@KSU_News` (أخبار القبول والتسجيل) - نشط 🟢\n" +
  "2️⃣ `@Univ_Announcements` (إعلانات الجامعات الرسمية) - نشط 🟢\n\n" +
  "📌 يقوم اليوزربوت بمراقبة هذه المصادر تلقائياً باستخدام جلستك الخاصة وإعادة صياغة الأخبار فور صدورها.";

Bot.sendInlineKeyboard(inline_keyboard, text);
