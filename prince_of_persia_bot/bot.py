import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from database import add_user, get_user_credits, get_last_message_timestamp, decrement_user_credits, get_cached_response, store_cached_response, add_message, get_all_plans, add_payment, update_payment_status, get_payment_details, get_plan_by_id, add_credits_to_user # Import database functions
from gemini_api import get_gemini_response # Import Gemini API function
from zarinpal_api import create_payment_request, verify_payment # Import ZarinPal API functions
import datetime

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
# TODO: Define the base URL for the bot's webhook/callback endpoint
# This is required for ZarinPal to redirect the user back after payment
BOT_CALLBACK_BASE_URL = os.getenv("BOT_CALLBACK_BASE_URL", "YOUR_CALLBACK_URL") # Placeholder

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        # Construct a unique user_id
        # Assuming Telegram for now, will need to handle Bale later
        user_id = f"{user.id}-0" # -0 for Telegram, -1 for Bale
        platform_user_id = str(user.id)
        origin = "Telegram"
        username = user.username
        # phone_number is not directly available from user object in this context

        try:
            add_user(user_id, platform_user_id, origin, username=username)
            logger.info(f"User {user_id} started the bot.")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            # Continue without adding user if database operation fails

        await update.message.reply_text(f'Hello {user.first_name}! I am your Prince of Persia bot. Ask me anything!')
    else:
        await update.message.reply_text('Hello! I am your Prince of Persia bot. Ask me anything!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays help information."""
    help_text = """
Welcome to the Prince of Persia Bot!

I can answer your questions using the power of AI.

Available commands:
/start - Start interacting with the bot.
/help - Show this help message.
/buyplan - View available plans to get more credits.

Send me any question, and I will do my best to answer it!
"""
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages."""
    user = update.effective_user
    if user:
        user_id = f"{user.id}-0" # Assuming Telegram
        current_time = datetime.datetime.now()
        user_message = update.message.text

        # Check user credits
        credits = None
        try:
            credits = get_user_credits(user_id)
            if credits is None:
                # User not found, should not happen if start command is used, but handle defensively
                add_user(user_id, str(user.id), "Telegram", username=user.username)
                credits = get_user_credits(user_id) # Try getting credits again
        except Exception as e:
            logger.error(f"Error getting credits for user {user_id}: {e}")
            await update.message.reply_text("Sorry, an error occurred while checking your credits.")
            return

        if credits is not None and credits <= 0:
            await update.message.reply_text("You have run out of credits. Please purchase a plan to continue.")
            return

        # Check rate limiting (10 seconds interval)
        last_message_timestamp_str = None
        try:
            last_message_timestamp_str = get_last_message_timestamp(user_id)
        except Exception as e:
            logger.error(f"Error getting last message timestamp for user {user_id}: {e}")
            # Continue without rate limiting if database operation fails

        if last_message_timestamp_str:
            try:
                last_message_timestamp = datetime.datetime.fromisoformat(last_message_timestamp_str)
                time_difference = current_time - last_message_timestamp
                if time_difference.total_seconds() < 10:
                    await update.message.reply_text("Please wait 10 seconds between messages.")
                    return
            except ValueError:
                logger.error(f"Invalid timestamp format in database for user {user_id}: {last_message_timestamp_str}")
                # Continue without rate limiting if timestamp format is invalid


        # Decrement credits
        try:
            decrement_user_credits(user_id)
        except Exception as e:
            logger.error(f"Error decrementing credits for user {user_id}: {e}")
            await update.message.reply_text("Sorry, an error occurred. Your credit was not deducted.")
            return # Stop processing if credit deduction fails


        # Send processing message
        processing_message = await update.message.reply_text("Processing your request...")

        # Check cache for Gemini response
        cached_response = None
        try:
            cached_response = get_cached_response(user_message, "Gemini")
        except Exception as e:
            logger.error(f"Error getting cached response for user {user_id}: {e}")
            # Continue without using cache if database operation fails


        gemini_text = None
        if cached_response:
            gemini_text = cached_response
            logger.info(f"Using cached Gemini response for user {user_id}.")
        else:
            # Get response from Gemini API
            gemini_response_data = get_gemini_response(user_message)

            if gemini_response_data:
                # Basic parsing, adjust based on actual Gemini API response structure
                try:
                    gemini_text = "".join([part['text'] for part in gemini_response_data['candidates'][0]['content']['parts']])
                    # Store Gemini response in cache (cache for 5 minutes)
                    try:
                        store_cached_response(user_message, gemini_text, "Gemini", expires_in_seconds=300)
                    except Exception as e:
                        logger.error(f"Error storing cached response for user {user_id}: {e}")
                        # Continue without storing cache if database operation fails

                except (KeyError, IndexError) as e:
                    logger.error(f"Could not parse Gemini response for user {user_id}: {e}")
                    await update.message.reply_text("Sorry, I could not process your request.")
                    # Re-credit user on API/parsing failure
                    try:
                        add_credits_to_user(user_id, 1)
                        logger.info(f"Re-credited user {user_id} due to Gemini response parsing error.")
                    except Exception as recredit_e:
                        logger.error(f"Error re-crediting user {user_id} after parsing error: {recredit_e}")
                    return
            else:
                logger.error(f"Gemini API call failed for user {user_id}.")
                await update.message.reply_text("Sorry, I could not get a response from the AI.")
                # Re-credit user on API failure
                try:
                    add_credits_to_user(user_id, 1)
                    logger.info(f"Re-credited user {user_id} due to Gemini API call failure.")
                except Exception as recredit_e:
                    logger.error(f"Error re-crediting user {user_id} after API call failure: {recredit_e}")
                return

        # TODO: Implement DeepSeek refinement here if needed
        deepseek_text = None # Placeholder for DeepSeek response
        final_response_text = gemini_text # For now, final response is Gemini's

        # Store message history
        try:
            add_message(
                user_id=user_id,
                text=user_message,
                enhanced_text=user_message, # TODO: Implement prompt enhancement
                gemini_response=gemini_text,
                deepseek_response=deepseek_text,
                response_text=final_response_text,
                timestamp=update.message.date.isoformat(), # Use message timestamp
                response_timestamp=datetime.datetime.now().isoformat() # Use current time for response timestamp
            )
        except Exception as e:
            logger.error(f"Error adding message to database for user {user_id}: {e}")
            # Continue without storing message if database operation fails


        # Edit processing message or send new message with final response
        # For simplicity, sending a new message for now
        await update.message.reply_text(final_response_text)

async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /buyplan command."""
    plans = []
    try:
        plans = get_all_plans()
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        await update.message.reply_text("Sorry, an error occurred while fetching plans.")
        return

    if not plans:
        await update.message.reply_text("No plans available at the moment.")
        return

    keyboard = []
    for plan in plans:
        plan_id, name, price, credits, description = plan
        button_text = f"{name} - {price} USD - {credits} credits"
        # Use a callback data that includes the plan_id
        callback_data = f"buy_plan_{plan_id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Available Plans:", reply_markup=reply_markup)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button presses from inline keyboards."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press
    user_id = f"{query.from_user.id}-0" # Assuming Telegram

    if query.data.startswith("buy_plan_"):
        plan_id = int(query.data.split("_")[2])
        # Get plan details
        plans = []
        try:
            plans = get_all_plans()
        except Exception as e:
            logger.error(f"Error getting plans for callback: {e}")
            await query.edit_message_text("Sorry, an error occurred.")
            return

        selected_plan = next((plan for plan in plans if plan[0] == plan_id), None)

        if not selected_plan:
            await query.edit_message_text("Invalid plan selected.")
            return

        plan_id, name, price, credits, description = selected_plan

        # Record pending payment in database
        payment_id = None
        try:
            payment_id = add_payment(user_id, plan_id, price, payment_status="pending")
        except Exception as e:
            logger.error(f"Error adding payment for user {user_id}, plan {plan_id}: {e}")
            await query.edit_message_text("Could not initiate payment. Please try again later.")
            return


        if payment_id is None:
            await query.edit_message_text("Could not initiate payment. Please try again later.")
            return

        # Initiate ZarinPal payment request
        description = f"Payment for {name} plan ({credits} credits) for user {user_id}"
        # Construct the callback URL to include payment_id and user_id
        callback_url = f"{BOT_CALLBACK_BASE_URL}/zarinpal_callback?payment_id={payment_id}&user_id={user_id}"

        authority, payment_url = create_payment_request(price, description, callback_url, metadata={"user_id": user_id, "payment_id": payment_id})

        if authority and payment_url:
            # Store authority in database for verification
            try:
                # Assuming update_payment_status can update authority
                update_payment_status(payment_id, "pending", completed_at=None) # Update status to pending
                # TODO: Need a specific function to update authority in DB
                # For now, let's assume add_payment can take authority and update_payment_status can update it
            except Exception as e:
                logger.error(f"Error updating payment status/authority for payment {payment_id}: {e}")
                # Continue without updating status if database operation fails


            # Redirect user to ZarinPal payment page
            await query.edit_message_text(f"Please complete the payment here: {payment_url}")

        else:
            # Payment request failed
            try:
                update_payment_status(payment_id, "failed")
            except Exception as e:
                logger.error(f"Error updating payment status to failed for payment {payment_id}: {e}")
                # Continue without updating status if database operation fails

            await query.edit_message_text("Failed to initiate payment with ZarinPal. Please try again later.")

# This function would be part of a web server handling the ZarinPal callback
async def zarinpal_callback_handler(request): # Placeholder function signature
    """Handles the callback from ZarinPal after payment."""
    # TODO: Extract Authority and Status from request (query parameters)
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    payment_id = request.GET.get('payment_id')
    user_id = request.GET.get('user_id')

    if status == 'OK':
        # Payment was successful, verify it with ZarinPal
        payment_details = None
        try:
            payment_details = get_payment_details(payment_id)
        except Exception as e:
            logger.error(f"Error getting payment details for payment {payment_id} in callback: {e}")
            return "Internal server error."


        if payment_details:
            amount = payment_details[3] # Get amount from database

            success, result = verify_payment(authority, amount)

            if success:
                # Payment verified, update database and add credits
                try:
                    update_payment_status(payment_id, "completed")
                except Exception as e:
                    logger.error(f"Error updating payment status to completed for payment {payment_id}: {e}")
                    return "Internal server error."

                plan_details = None
                try:
                    plan_details = get_plan_by_id(payment_details[2]) # Get plan_id from payment_details
                except Exception as e:
                    logger.error(f"Error getting plan details for payment {payment_id} in callback: {e}")
                    return "Internal server error."

                if plan_details:
                    credits_to_add = plan_details[3] # Get credits from plan details
                    try:
                        add_credits_to_user(user_id, credits_to_add)
                        logger.info(f"Payment successful and {credits_to_add} credits added to user {user_id}.")
                        # TODO: Send a success message to the user via Telegram bot
                        return "Payment successful and credits added!"
                    except Exception as e:
                        logger.error(f"Error adding credits to user {user_id} after payment {payment_id}: {e}")
                        return "Internal server error."

                else:
                    # Should not happen if payment details are valid
                    logger.error(f"Plan details not found for payment {payment_id}.")
                    return "Payment verified, but could not find plan details."
            else:
                # Payment verification failed
                try:
                    update_payment_status(payment_id, "verification_failed")
                except Exception as e:
                    logger.error(f"Error updating payment status to verification_failed for payment {payment_id}: {e}")
                    return "Internal server error."

                logger.warning(f"Payment verification failed for payment {payment_id}: {result}")
                # TODO: Send a failure message to the user via Telegram bot
                return f"Payment verification failed: {result}"
        else:
            # Payment details not found in database
            logger.error(f"Payment details not found for payment ID: {payment_id} in callback.")
            return "Payment details not found."
    else:
        # Payment was cancelled or failed
        status_text = "cancelled" if status == 'NOK' else "failed"
        try:
            update_payment_status(payment_id, status_text)
        except Exception as e:
            logger.error(f"Error updating payment status to {status_text} for payment {payment_id}: {e}")
            return "Internal server error."

        logger.info(f"Payment {payment_id} was {status_text}.")
        # TODO: Send a cancellation/failure message to the user via Telegram bot
        return f"Payment {status_text}."


def main():
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # Add command handler for /help
    help_handler = CommandHandler('help', help_command)
    application.add_handler(help_handler)

    # Add message handler for text messages that are not commands
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(message_handler)

    # Add command handler for /buyplan
    buy_plan_handler = CommandHandler('buyplan', buy_plan)
    application.add_handler(buy_plan_handler)

    # Add callback query handler for inline keyboard buttons
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # TODO: Add a handler for the ZarinPal callback URL (requires a web framework)
    # Example (using Flask):
    # from flask import Flask, request
    # app = Flask(__name__)
    # @app.route('/zarinpal_callback', methods=['GET'])
    # def zarinpal_callback():
    #     # Call the zarinpal_callback_handler function here
    #     # Extract payment_id and user_id from request.args
    #     payment_id = request.args.get('payment_id')
    #     user_id = request.args.get('user_id')
    #     # You might need to pass the request object or relevant data to the handler
    #     # return asyncio.run(zarinpal_callback_handler(request)) # Example with async handler
    #     pass # Placeholder


    application.run_polling()

if __name__ == '__main__':
    main()
