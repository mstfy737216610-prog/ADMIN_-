/*CMD
  command: /campaigns
  help: إدارة الحملات وقنوات النشر
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: الحملات, قنوات النشر
CMD*/

var inline_keyboard = [
  [
    { title: "➕ إضافة حملة جديدة", command: "/login" },
    { title: "📋 عرض المصادر المرتبطة", command: "/sources" }
  ],
  [
    { title: "🔙 العودة للوحة الرئيسية", command: "/start" }
  ]
];

var text = "📢 *إدارة الحملات وقنوات النشر:*\n\n" +
  "• حملة الأخبار الجامعية الرسمية (نشطة 🟢)\n" +
  "  - القناة المستهدفة: قناتك الرسمية\n" +
  "  - وضع إعادة الصياغة: الذكاء الاصطناعي الأكاديمي الحصري\n" +
  "  - استبدال إعلانات المنافسين: مفعّل 🎯\n\n" +
  "اختر إجراءً من الخيارات أدناه:";

Bot.sendInlineKeyboard(inline_keyboard, text);
