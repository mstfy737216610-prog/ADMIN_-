/*CMD
  command: handle_user_post
  help: معالجة النصوص المنشورة واستبدال إعلانات المنافسين وإعادة الصياغة
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: 
CMD*/

var text = message || "";
if (!text || text.length < 3) {
  return;
}

// 1. فحص إعلانات المنافسين
var ad_keywords = [
  "إعلان مدفوع", "ترويج لخدمات طلابية", "حل واجبات", "بحوث تخرج",
  "خدمات طلابية", "مشاريع تخرج", "كتابة أبحاث", "إعلان ممول", "برعاية"
];

var is_ad = false;
for (var i = 0; i < ad_keywords.length; i++) {
  if (text.indexOf(ad_keywords[i]) !== -1) {
    is_ad = true;
    break;
  }
}

if (is_ad) {
  var custom_ad = Bot.getProperty("custom_ad");
  if (!custom_ad) {
    custom_ad = "🎓 خدمات طلابية معتمدة وأكاديمية متكاملة 🎓\n" +
      "يسرنا تقديم الدعم الأكاديمي الشامل للطلبة والباحثين:\n" +
      "• مساعدة في البحوث والمشاريع الأكاديمية\n" +
      "• التدقيق اللغوي وتنسيق الرسائل الجامعية\n" +
      "• تلخيص المحاضرات والمقررات الدراسية\n" +
      "• استشارات القبول والتسجيل والتنسيق\n\n" +
      "📞 للتواصل والطلب مباشرة عبر المشرف: @M_S_F_G\n" +
      "✨ جودة أكاديمية، سرعة في الإنجاز، وأسعار مناسبة للطلاب!";
  }
  var ad_msg = "🎯 **تم رصد إعلان ترويجي للمنافسين!**\n" +
    "تم استبداله تلقائياً بإعلان خدماتك الطلابية الخاص بك:\n\n" +
    "━━━━━━━━━━━━━━━━━━━\n" +
    custom_ad + "\n" +
    "━━━━━━━━━━━━━━━━━━━\n" +
    "(جاهز للنشر في قناتك)";
  Bot.sendMessage(ad_msg);
  return;
}

// 2. إعادة الصياغة الأكاديمية الذكية
var lines = text.split("\n");
var valid_lines = [];
for (var k = 0; k < lines.length; k++) {
  var l = lines[k].trim();
  if (l && l.indexOf("http") !== 0) {
    valid_lines.push(l);
  }
}

var title = valid_lines.length > 0 ? valid_lines[0] : "تحديث جامعي وتعليمي هام";
var bullets = "";
for (var j = 1; j < Math.min(valid_lines.length, 6); j++) {
  bullets += "• " + valid_lines[j] + "\n";
}
if (!bullets) {
  bullets = "• " + text;
}

var result = "✨ **المنشور التعليمي الجاهز للنشر:**\n" +
  "━━━━━━━━━━━━━━━━━━━\n" +
  "📌 **" + title + "**\n\n" +
  bullets + "\n" +
  "💬 يسعدنا استقبال استفساراتكم ومشاركة المنشور مع زملائكم الطلاب!\n\n" +
  "#جامعة #أخبار_التعليم #شؤون_الطلاب #دراسة\n" +
  "━━━━━━━━━━━━━━━━━━━\n" +
  "⚡️ صياغة: `DeepSeek-V4.1-Flash`\n" +
  "💡 يمكنك نسخه أو نشره في قناتك بنقرة واحدة!";

Bot.sendMessage(result);
