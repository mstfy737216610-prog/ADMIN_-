/*CMD
  command: /ad
  help: إعلاني الخاص واستبدال إعلانات المنافسين
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: إعلاني الخاص, الإعلان
CMD*/

var myAd = Bot.getProperty("custom_ad") || "🎓 *خدمات طلابية وبحوث جامعية متميزة* 🎓\nنقدم استشارات أكاديمية وتنسيق مشاريع تخرج بأعلى درجات الدقة والاحترافية!\n📲 للتواصل والاستفسار: @M_S_F_G";

var inline_keyboard = [
  [
    { title: "🔙 القائمة الرئيسية", command: "/start" }
  ]
];

var text = "🎯 *إعلان الخدمات الطلابية الخاص بك:*\n\n" +
  myAd + "\n\n" +
  "💡 *الآلية:* عند رصد أي منشور يحتوي على إعلان لمنافسين أو روابط خارجية، يقوم البوت تلقائياً بحذف إعلان المنافس ووضع إعلانك أعلاه بدلاً منه!";

Bot.sendInlineKeyboard(inline_keyboard, text);
