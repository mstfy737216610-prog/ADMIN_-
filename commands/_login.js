/*CMD
  command: /login
  help: ربط الحساب برقم الهاتف واستخراج الجلسة
  need_reply: true
  auto_retry_time: 
  folder: 
  answer: 📱 أرسل الآن رقم هاتفك مع الرمز الدولي (مثال: +966501234567) لربط حسابك باليوزربوت:
CMD*/

if (message) {
  Bot.sendMessage("📩 تم استلام رقم هاتفك: `" + message + "`\nجاري إرسال كود التحقق (OTP) إلى حسابك في تيليجرام...\nأرسل الكود هنا فور وصوله.");
  User.setProperty("phone", message, "string");
  Bot.runCommand("/otp");
}
