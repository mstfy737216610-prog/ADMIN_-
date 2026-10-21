/*CMD
  command: /sources
  help: قائمة المصادر المراقبة
  need_reply: false
  auto_retry_time: 
  folder: 
  answer: 
  keyboard: 
  aliases: 📋 إدارة المصادر, المصادر
CMD*/

var text = "📋 **قائمة مصادر المراقبة الحالية (sources.json):**\n\n" +
  "1. [telegram] **أخبار الجامعة والقبول الرسمي**\n   الهدف: `@KSU_News` | القاعدة: رسمي [نشر مباشر] | الأولوية: عالي\n\n" +
  "2. [twitter] **الحساب الرسمي لوزارة التعليم**\n   الهدف: `@moe_gov_sa` | القاعدة: رسمي [نشر مباشر] | الأولوية: عالي\n\n" +
  "➕ لإضافة مصدر جديد أرسل: `/add_source tg @channel`\n" +
  "➖ لحذف مصدر أرسل: `/remove_source @channel`";

Bot.sendMessage(text);
