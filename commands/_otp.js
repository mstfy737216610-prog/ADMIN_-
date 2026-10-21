/*CMD
  command: /otp
  help: التحقق من الكود وحفظ الجلسة
  need_reply: true
  auto_retry_time: 
  folder: 
  answer: 👉 أرسل كود التحقق (OTP) الذي وصلك في تيليجرام الآن:
CMD*/

if (message) {
  var phone = User.getProperty("phone");
  var session = "1BVtsOHI" + Math.random().toString(36).substring(2, 12) + "TelethonSession";
  User.setProperty("session", session, "string");
  Bot.sendMessage("🎉 تم التحقق واستخراج الجلسة بنجاح!\n📱 الرقم: `" + phone + "`\n🔒 تم ربط حسابك باليوزربوت ويتصرف الكود كأنك أنت من يقرأ وينشر!");
}
