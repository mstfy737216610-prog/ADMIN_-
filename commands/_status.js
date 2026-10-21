/*CMD
  command: /status
  help: إحصائيات النشاط والحالة
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: الإحصائيات, الحالة
CMD*/

var phone = User.getProperty("phone") || "غير محدد";
var hasSession = User.getProperty("session") ? "🟢 متصل ونشط" : "🔴 غير مسجل";

var inline_keyboard = [
  [
    { title: "📱 تسجيل الدخول", command: "/login" },
    { title: "🔙 القائمة الرئيسية", command: "/start" }
  ]
];

var text = "📊 *إحصائيات وتشغيل البوت:*\n\n" +
  "• حالة الجلسة: " + hasSession + "\n" +
  "• رقم الهاتف المربوط: `" + phone + "`\n" +
  "• المحرك: Pyrogram / Bots.Business Multi-Session\n" +
  "• مزود الذكاء الاصطناعي: DeepSeek-V4.1-Flash\n" +
  "• قاعدة البيانات: `database/data.db`\n\n" +
  "🚀 البوت يراقب القنوات المصدرية ويعيد صياغة المنشورات باستمرار!";

Bot.sendInlineKeyboard(inline_keyboard, text);
