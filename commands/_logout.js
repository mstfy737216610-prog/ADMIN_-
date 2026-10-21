/*CMD
  command: /logout
  help: تسجيل الخروج وحذف الجلسة
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: تسجيل الخروج
CMD*/

User.setProperty("session", "", "string");
User.setProperty("phone", "", "string");

var inline_keyboard = [
  [
    { title: "📱 تسجيل الدخول مجدداً", command: "/login" },
    { title: "🔙 القائمة الرئيسية", command: "/start" }
  ]
];

var text = "🔒 *تم تسجيل الخروج بنجاح!*\n\n" +
  "تم حذف الجلسة وإيقاف الزحف بهذا الحساب.\n" +
  "يمكنك تسجيل الدخول برقم جديد في أي وقت.";

Bot.sendInlineKeyboard(inline_keyboard, text);
