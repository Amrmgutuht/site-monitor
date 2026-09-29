import logging
import time
from datetime import datetime
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ⚠️ ضع التوكن الذي أخذته من BotFather بين التنصيص
TELEGRAM_TOKEN = "8953364444:AAFzGCNx367yllYEt7PGY2z-H3Z1MJwFIEA"

monitored_sites = {}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}


def get_page_content(url):
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        return res.text
    except Exception as e:
        print(f"خطأ في الاتصال بالموقع {url}: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 **أهلاً بك في بوت مراقبة المواقع!**\n\n"
        "أرسل لي أي رابط موقع مباشرة في الشات وسأقوم بمراقبته لك كل 5 دقائق.\n\n"
        "📜 الأوامر المتاحة:\n"
        "🔗 أرسل الرابط مباشرة لإضافته\n"
        "📜 `/list` - لعرض كل المواقع المراقبة\n"
        "❌ `/delete [الرابط]` - لإلغاء مراقبة موقع"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = (
        context.args[0].strip()
        if context.args
        else update.message.text.strip()
    )

    if not url.startswith(("http://", "https://")):
        await update.message.reply_text(
            "❌ يرجى إرسال رابط صحيح يبدأ بـ http:// أو https://"
        )
        return

    await update.message.reply_text(
        f"⏳ جاري فحص الرابط...\n`{url}`", parse_mode="Markdown"
    )

    content = get_page_content(url)
    if content is None:
        await update.message.reply_text(
            "❌ تعذر قراءة هذا الموقع. تأكد من صحة الرابط."
        )
        return

    if user_id not in monitored_sites:
        monitored_sites[user_id] = {}

    monitored_sites[user_id][url] = content
    await update.message.reply_text(
        "🟢 **تمت إضافة الموقع بنجاح!**\nسيتم فحصه كل 5 دقائق وإرسال تنبيه فور حدوث أي تغيير.",
        parse_mode="Markdown",
    )


async def list_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_urls = monitored_sites.get(user_id, {})

    if not user_urls:
        await update.message.reply_text("ℹ️ أنت لا تراقب أي مواقع حالياً.")
        return

    msg = "📜 **المواقع التي تراقبها حالياً:**\n\n"
    for i, url in enumerate(user_urls.keys(), 1):
        msg += f"{i}. {url}\n"

    await update.message.reply_text(msg, disable_web_page_preview=True)


async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "⚠️ أرسل الرابط بعد الأمر، مثال:\n`/delete https://example.com`",
            parse_mode="Markdown",
        )
        return

    url = context.args[0].strip()
    if user_id in monitored_sites and url in monitored_sites[user_id]:
        del monitored_sites[user_id][url]
        await update.message.reply_text("🗑️ تم حذف الموقع من قائمة المراقبة.")
    else:
        await update.message.reply_text("❌ هذا الرابط غير موجود في قائمتك.")


async def check_updates(context: ContextTypes.DEFAULT_TYPE):
    for user_id, urls in list(monitored_sites.items()):
        for url, old_content in list(urls.items()):
            new_content = get_page_content(url)
            if new_content and new_content != old_content:
                monitored_sites[user_id][url] = new_content
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                alert_msg = (
                    f"🚨 **تنبيه: حدث تغيير في الموقع!**\n\n"
                    f"⏰ **الوقت:** `{now_str}`\n"
                    f"🔗 **الرابط:** {url}"
                )
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=alert_msg,
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    print(f"خطأ في إرسال الإشعار: {e}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_url))
    app.add_handler(CommandHandler("list", list_urls))
    app.add_handler(CommandHandler("delete", delete_url))
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), add_url)
    )

    job_queue = app.job_queue
    job_queue.run_repeating(check_updates, interval=300, first=10)

    print("🤖 البوت يعمل الآن...")
    app.run_polling()
