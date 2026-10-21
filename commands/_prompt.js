/*CMD
  command: /prompt
  help: موجه الذكاء الاصطناعي الأكاديمي
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: الذكاء الاصطناعي, تعليمات الذكاء
CMD*/

var inline_keyboard = [
  [
    { title: "🔙 القائمة الرئيسية", command: "/start" }
  ]
];

var text = "🧠 *موجه الذكاء الاصطناعي الحالي (DeepSeek Core):*\n\n" +
  "• الدور: محرر وكاتب محتوى تعليمي وجامعي حصري.\n" +
  "• القواعد: إعادة الصياغة بدون ذكر المصادر، حذف الروابط وقنوات المنافسين، إبراز المواعيد والنسب، وتنسيق المنشور في نقاط واضحة مع إيموجيات وهاشتاجات.\n" +
  "• رد SKIP: يتم إلغاء وتخطي المنشور فوراً إذا كان تافهاً أو غير ملائم.";

Bot.sendInlineKeyboard(inline_keyboard, text);
