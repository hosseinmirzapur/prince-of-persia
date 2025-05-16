# Prince of Persia Telegram Bot ✨

An intelligent Telegram bot powered by the Gemini AI model, designed to answer user queries.

## Features 🚀

-   Answers user questions using the Gemini API.
-   Free tier with a limit of 20 questions per user per day.
-   10-second interval between consecutive questions.
-   User management and credit tracking.
-   Basic caching for Gemini API responses.
-   Message history storage.
-   Payment integration outline with ZarinPal (requires further implementation).
-   Error handling and logging.
-   `/start`, `/help`, and `/buyplan` commands.

## Technical Documentation 📚

### Prerequisites ✅

-   Python 3.6 or higher
-   Telegram Bot API Token
-   Gemini API Key
-   ZarinPal Merchant ID (for payment integration)

### Setup 🛠️

1.  **Clone the repository (or create the project structure manually):**

    ```bash
    # If you have the project files
    # git clone <repository_url>
    # cd prince_of_persia_bot

    # If creating manually
    mkdir prince_of_persia_bot
    cd prince_of_persia_bot
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**

    -   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    -   On Windows:
        ```bash
        venv\Scripts\activate
        ```

4.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```
    (If you created the project manually, make sure you have a `requirements.txt` file with `python-telegram-bot`, `python-dotenv`, and `requests` listed).

5.  **Configure API Keys 🔑:**

    Create a `.env` file in the `prince_of_persia_bot` directory with the following content, replacing the placeholder values with your actual keys:

    ```dotenv
    TELEGRAM_API_TOKEN="YOUR_TELEGRAM_API_TOKEN"
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ZARINPAL_MERCHANT_ID="YOUR_ZARINPAL_MERCHANT_ID"
    BOT_CALLBACK_BASE_URL="YOUR_CALLBACK_URL" # Required for ZarinPal webhook
    ```
    **Note:** Replace `"YOUR_CALLBACK_URL"` with the base URL where your bot's webhook will be accessible if you implement the ZarinPal callback handler on a server.

6.  **Database Setup 🗄️:**

    The project uses SQLite for the database. The database file (`bot_database.db`) will be automatically created when you run the `database.py` script.

    To create the database tables, run:

    ```bash
    python database.py
    ```

    You can optionally add initial plans to the `Plan` table by uncommenting and modifying the `add_plan` calls in the `if __name__ == '__main__':` block of `database.py` and running the script.

### Running the Bot ▶️

#### Local Development (Polling) 🖥️

For local testing, you can run the bot using polling. This method checks for new messages periodically.

1.  Activate your virtual environment (if not already active).
2.  Run the `bot.py` script:

    ```bash
    python bot.py
    ```
    The bot should start and begin polling for updates.

#### Server Deployment (Webhooks and ZarinPal Callback) ☁️

For production deployment, using webhooks is recommended for better performance and scalability. Additionally, handling the ZarinPal payment callback requires a web server accessible from the internet.

1.  **Webhook Setup:** Configure your Telegram bot to use webhooks and point the webhook URL to your server's endpoint that will receive updates from Telegram. The `python-telegram-bot` library supports webhook setups, but requires a web framework (like Flask, FastAPI, orio) to handle incoming requests.
2.  **ZarinPal Callback:** The ZarinPal payment gateway will send a callback request to a specified URL after a user completes a payment. The `zarinpal_callback_handler` function in `bot.py` contains the logic to handle this callback, but it needs to be integrated into a web framework endpoint that matches the `BOT_CALLBACK_BASE_URL` and `/zarinpal_callback` path configured in your `.env` file.

    Example (using Flask - conceptual):

    ```python
    # This is a conceptual example and requires a full Flask setup
    from flask import Flask, request
    from bot import zarinpal_callback_handler # Import the handler

    app = Flask(__name__)

    @app.route('/zarinpal_callback', methods=['GET', 'POST']) # ZarinPal uses GET for callback
    async def zarinpal_callback():
        # Extract data from the request (query parameters for GET)
        # You might need to adapt this based on how your web framework handles async
        # return await zarinpal_callback_handler(request)
        pass # Placeholder for actual implementation

    if __name__ == '__main__':
        # Run the Flask app (consider using a production-ready server like Gunicorn)
        app.run(port=5000)
    ```
    **Note:** Implementing the webhook and ZarinPal callback on a server requires additional setup and configuration beyond the scope of this README. You will need to choose a web framework, set up a server (e.g., Nginx, Apache), and potentially use a process manager (e.g., Gunicorn, PM2).

## Bot Commands 🤖

-   `/start`: Initiates interaction with the bot.
-   `/help`: Displays help information and available commands.
-   `/buyplan`: Shows a list of available plans for purchasing credits.

## Code Structure 📁

-   `bot.py`: Contains the main Telegram bot logic, command handlers, and message handler.
-   `database.py`: Handles database connection and operations (creating tables, adding/getting data).
-   `gemini_api.py`: Contains functions for interacting with the Gemini API.
-   `zarinpal_api.py`: Contains placeholder functions for interacting with the ZarinPal API.
-   `.env`: Stores environment variables (API keys, etc.).
-   `requirements.txt`: Lists project dependencies.

## TODOs and Future Improvements 📝

-   **Full ZarinPal Integration:** Complete the implementation of the ZarinPal payment initiation and verification, including handling the callback on a web server.
-   **DeepSeek Integration:** Implement the logic to send Gemini's response to DeepSeek for refinement.
-   **Prompt Enhancement:** Implement logic to enhance user prompts before sending them to the Gemini API.
-   **Re-credit Logic Refinement:** Ensure robust re-crediting logic in case of API failures or other issues after credit deduction.
-   **Comprehensive Testing:** Write automated unit tests and perform thorough testing of all bot functionalities and edge cases.
-   **User Experience:** Refine bot responses and interactions for a better user experience.
-   **Security:** Implement additional security measures as outlined in the project overview (firewall, SSL/TLS, etc.) for server deployment.
-   **Scalability:** Consider using a more scalable database and hosting solution for production.
-   **Bale Integration:** Extend user ID handling to include Bale users.

This README provides a technical overview and instructions for setting up and running the bot. For detailed code implementation, refer to the respective Python files.
