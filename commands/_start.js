/*CMD
  command: /start
  help: لوحة التحكم وربط الحساب
  need_reply: false
  aliases: 🎛 لوحة التحكم الرئيسية, لوحة التحكم, /help
CMD*/

var inline_keyboard = [
  [
    { title: "📱 تسجيل الدخول وربط الحساب برقم الهاتف", command: "/login" },
    { title: "📢 إدارة الحملات وقنوات النشر", command: "/campaigns" }
  ],
  [
    { title: "🎯 إعلاني الخاص (المنافسين)", command: "/ad" },
    { title: "⚙️ تعليمات الذكاء الاصطناعي", command: "/prompt" }
  ],
  [
    { title: "📊 إحصائيات النشاط", command: "/status" },
    { title: "📋 المصادر المراقبة", command: "/sources" }
  ]
];

var text = "👋 مرحباً بك يا مديرنا العزيز @M_S_F_G!\n" +
  "🤖 محرر المحتوى والناشر الأكاديمي الذكي (Userbot Engine)\n\n" +
  "📌 لربط حسابك والتصرف كأنك المستخدم لقراءة القنوات والنشر فيها، اضغط زر تسجيل الدخول أدناه:";

Bot.sendInlineKeyboard(inline_keyboard, text);
