import os
import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from dotenv import load_dotenv
from database import (
    add_user,
    get_user_credits,
    get_last_message_timestamp,
    decrement_user_credits,
    get_cached_response,
    store_cached_response,
    add_message,
    get_all_plans,
    add_payment,
    update_payment_status,
    get_payment_details,
    get_plan_by_id,
    add_credits_to_user,
    get_user_phone_number,
    update_user_phone_number,
)
from gemini_api import get_gemini_response
from zarinpal_api import create_payment_request, verify_payment

# Load environment
load_dotenv()
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
BOT_CALLBACK_BASE_URL = os.getenv("BOT_CALLBACK_BASE_URL", "https://example.com")
PROXY_URL = os.getenv("PROXY_URL")

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    user_id = f"{user.id}-0"
    try:
        add_user(user_id, str(user.id), "Telegram", username=user.username)
        logger.info(f"Added or exists user {user_id}")
    except Exception as e:
        logger.error(f"DB error adding user {user_id}: {e}")

    phone = get_user_phone_number(user_id)
    if phone:
        await update.message.reply_text(f"سلام {user.first_name}! هر سوالی دارید بپرسید.")
    else:
        kb = [[KeyboardButton("اشتراک گذاری مخاطب", request_contact=True)]]
        markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            f"خوش آمدید {user.first_name}! لطفا شماره موبایل خود را برای ادامه به اشتراک بگذارید.",
            reply_markup=markup
        )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (user := update.effective_user) or not update.message.contact:
        return
    user_id = f"{user.id}-0"
    phone = update.message.contact.phone_number
    try:
        update_user_phone_number(user_id, phone)
        logger.info(f"Stored phone for {user_id}: {phone}")
        await update.message.reply_text(
            "متشکرم! اکنون می توانید از ربات استفاده کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Error storing phone: {e}")
        await update.message.reply_text("خطا در ذخیره مخاطب. لطفا دوباره تلاش کنید.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        user_id = f"{user.id}-0"
        if not get_user_phone_number(user_id):
            kb = [[KeyboardButton("اشتراک گذاری مخاطب", request_contact=True)]]
            markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "لطفا شماره موبایل خود را به اشتراک بگذارید.",
                reply_markup=markup
            )
            return
    await update.message.reply_text(
        "/start - شروع ربات\n"
        "/help - این پیام\n"
        "/buyplan - خرید اعتبار"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message.text:
        return
    user_id = f"{user.id}-0"
    if not get_user_phone_number(user_id):
        kb = [[KeyboardButton("اشتراک گذاری مخاطب", request_contact=True)]]
        markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "لطفا شماره موبایل خود را به اشتراک بگذارید.",
            reply_markup=markup
        )
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    text = update.message.text

    # Rate limiting
    last_ts = get_last_message_timestamp(user_id)
    if last_ts:
        try:
            last = datetime.datetime.fromisoformat(last_ts)
            if (now - last).total_seconds() < 10:
                await update.message.reply_text("لطفا بین ارسال پیام ها ۱۰ ثانیه صبر کنید.")
                return
        except ValueError:
            pass

    # Credits check
    credits = get_user_credits(user_id) or 0
    if credits <= 0:
        await update.message.reply_text("اعتبار شما کافی نیست. از /buyplan استفاده کنید.")
        return
    decrement_user_credits(user_id)

    msg = await update.message.reply_text("در حال پردازش...")

    # Gemini
    resp = get_cached_response(text, "Gemini")
    if resp:
        answer = resp
    else:
        data = get_gemini_response(text)
        if not data:
            add_credits_to_user(user_id, 1)
            await update.message.reply_text("خطا در هوش مصنوعی. اعتبار شما بازگردانده شد.")
            return
        parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        answer = ''.join(p.get('text','') for p in parts)
        store_cached_response(text, answer, "Gemini", expires_in_seconds=300)

    add_message(
        user_id=user_id,
        text=text,
        enhanced_text=text,
        gemini_response=answer,
        deepseek_response=None,
        response_text=answer,
        timestamp=update.message.date.isoformat(),
        response_timestamp=datetime.datetime.utcnow().isoformat()
    )
    await msg.edit_text(answer)

async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    user_id = f"{user.id}-0"
    if not get_user_phone_number(user_id):
        kb = [[KeyboardButton("اشتراک گذاری مخاطب", request_contact=True)]]
        markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "لطفا شماره موبایل خود را به اشتراک بگذارید.",
            reply_markup=markup
        )
        return
    plans = get_all_plans() or []
    if not plans:
        await update.message.reply_text("هیچ پلنی موجود نیست.")
        return
    kb = [[InlineKeyboardButton(f"{name} - {price}$ ({credits}cr)", callback_data=f"plan_{plan_id}")]
          for plan_id,name,price,credits,_ in plans]
    await update.message.reply_text("یک پلن انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb))

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("plan_"):
        plan_id = int(data.split("_")[1])
        # omitted payment logic for brevity
        await query.edit_message_text("Payment flow not shown in this snippet.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Update error:", exc_info=context.error)

def main():
    builder = Application.builder().token(TELEGRAM_API_TOKEN)
    if PROXY_URL:
        builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)
    application: Application = builder.build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('buyplan', buy_plan))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
