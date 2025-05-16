import sqlite3
import os
import datetime

DATABASE_FILE = 'bot_database.db'

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

def get_db_connection():
    """Establishes a database connection, raising an error if the database file does not exist."""
    if not os.path.exists(DATABASE_FILE):
        raise DatabaseError(f"Database file not found: {DATABASE_FILE}. Please run database.py to create it.")
    return sqlite3.connect(DATABASE_FILE)

def create_tables():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE) # This will create the file if it doesn't exist, intended for initial setup
        cursor = conn.cursor()

        # Create User Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS User (
                user_id TEXT PRIMARY KEY,
                platform_user_id TEXT,
                origin TEXT,
                username TEXT NULLABLE,
                phone_number TEXT NULLABLE,
                credits INTEGER,
                created_at DATETIME
            )
        ''')

        # Create Plan Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Plan (
                plan_id INTEGER PRIMARY KEY,
                name TEXT,
                price DECIMAL,
                credits INTEGER,
                description TEXT NULLABLE,
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')

        # Create Payment Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Payment (
                payment_id INTEGER PRIMARY KEY,
                user_id TEXT,
                plan_id INTEGER,
                amount DECIMAL,
                payment_status TEXT,
                created_at DATETIME,
                completed_at DATETIME NULLABLE,
                authority TEXT NULLABLE,
                FOREIGN KEY (user_id) REFERENCES User(user_id),
                FOREIGN KEY (plan_id) REFERENCES Plan(plan_id)
            )
        ''')

        # Create Transaction Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "Transaction" (
                payment_id INTEGER PRIMARY KEY,
                transaction_id TEXT,
                amount DECIMAL,
                provider_status TEXT,
                provider_response TEXT NULLABLE,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (payment_id) REFERENCES Payment(payment_id)
            )
        ''')

        # Create Message Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Message (
                message_id INTEGER PRIMARY KEY,
                user_id TEXT,
                text TEXT,
                enhanced_text TEXT,
                gemini_response TEXT,
                deepseek_response TEXT NULLABLE,
                response_text TEXT,
                timestamp DATETIME,
                response_timestamp DATETIME,
                FOREIGN KEY (user_id) REFERENCES User(user_id)
            )
        ''')

        # Create Cache Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Cache (
                cache_id INTEGER PRIMARY KEY,
                question TEXT,
                response TEXT,
                service TEXT,
                created_at DATETIME,
                expires_at DATETIME
            )
        ''')

        # Create API Key Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS API_Key (
                api_key_id INTEGER PRIMARY KEY,
                service_name TEXT,
                api_key_value TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')

        conn.commit()
        print("Tables created successfully.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def add_user(user_id, platform_user_id, origin, username=None, phone_number=None, initial_credits=20):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT OR IGNORE INTO User (user_id, platform_user_id, origin, username, phone_number, credits, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, platform_user_id, origin, username, phone_number, initial_credits, created_at))
        conn.commit()
        print(f"User {user_id} added or already exists.")
    except DatabaseError as e:
        print(f"Error adding user: {e}")
    except sqlite3.Error as e:
        print(f"Database error adding user: {e}")
    finally:
        if conn:
            conn.close()

def get_user_credits(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT credits FROM User WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result and result[0]:
            return result[0]
        return None # User not found
    except DatabaseError as e:
        print(f"Error getting user credits: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error getting user credits: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_phone_number(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT phone_number FROM User WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result and result[0]: # Check if result exists and phone_number is not None or empty
            return result[0]
        return None # User not found or phone number not set
    except DatabaseError as e:
        print(f"Error getting user phone number: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error getting user phone number: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_user_phone_number(user_id, phone_number):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET phone_number = ? WHERE user_id = ?", (phone_number, user_id))
        conn.commit()
        print(f"Phone number updated for user {user_id}.")
    except DatabaseError as e:
        print(f"Error updating user phone number: {e}")
    except sqlite3.Error as e:
        print(f"Database error updating user phone number: {e}")
    finally:
        if conn:
            conn.close()

def get_last_message_timestamp(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM Message WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None # No previous messages
    except DatabaseError as e:
        print(f"Error getting last message timestamp: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error getting last message timestamp: {e}")
        return None
    finally:
        if conn:
            conn.close()

def decrement_user_credits(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET credits = credits - 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        print(f"Credits decremented for user {user_id}.")
    except DatabaseError as e:
        print(f"Error decrementing user credits: {e}")
    except sqlite3.Error as e:
        print(f"Database error decrementing user credits: {e}")
    finally:
        if conn:
            conn.close()

def get_cached_response(question, service):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.datetime.now().isoformat()
        cursor.execute("SELECT response FROM Cache WHERE question = ? AND service = ? AND expires_at > ?", (question, service, current_time))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None # No valid cached response
    except DatabaseError as e:
        print(f"Error getting cached response: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error getting cached response: {e}")
        return None
    finally:
        if conn:
            conn.close()

def store_cached_response(question, response, service, expires_in_seconds=300):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.datetime.now()
        expires_at = created_at + datetime.timedelta(seconds=expires_in_seconds)
        cursor.execute('''
            INSERT INTO Cache (question, response, service, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (question, response, service, created_at.isoformat(), expires_at.isoformat()))
        conn.commit()
        print(f"Cached response stored for service {service}.")
    except DatabaseError as e:
        print(f"Error storing cached response: {e}")
    except sqlite3.Error as e:
        print(f"Database error storing cached response: {e}")
    finally:
        if conn:
            conn.close()

def add_message(user_id, text, enhanced_text, gemini_response, deepseek_response, response_text, timestamp, response_timestamp):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Message (user_id, text, enhanced_text, gemini_response, deepseek_response, response_text, timestamp, response_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, text, enhanced_text, gemini_response, deepseek_response, response_text, timestamp, response_timestamp))
        conn.commit()
        print(f"Message added for user {user_id}.")
    except DatabaseError as e:
        print(f"Error adding message: {e}")
    except sqlite3.Error as e:
        print(f"Database error adding message: {e}")
    finally:
        if conn:
            conn.close()

def add_plan(name, price, credits, description=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.datetime.now().isoformat()
        updated_at = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO Plan (name, price, credits, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, price, credits, description, created_at, updated_at))
        conn.commit()
        print(f"Plan '{name}' added.")
    except DatabaseError as e:
        print(f"Error adding plan: {e}")
    except sqlite3.Error as e:
        print(f"Database error adding plan: {e}")
    finally:
        if conn:
            conn.close()

def get_all_plans():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT plan_id, name, price, credits, description FROM Plan")
        return cursor.fetchall()
    except DatabaseError as e:
        print(f"Error getting plans: {e}")
        return []
    except sqlite3.Error as e:
        print(f"Database error getting plans: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_credits_to_user(user_id, credits):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET credits = credits + ? WHERE user_id = ?", (credits, user_id))
        conn.commit()
        print(f"Added {credits} credits to user {user_id}.")
    except DatabaseError as e:
        print(f"Error adding credits to user: {e}")
    except sqlite3.Error as e:
        print(f"Database error adding credits to user: {e}")
    finally:
        if conn:
            conn.close()

def add_payment(user_id, plan_id, amount, payment_status="pending", authority=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO Payment (user_id, plan_id, amount, payment_status, created_at, authority)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, plan_id, amount, payment_status, created_at, authority))
        conn.commit()
        print(f"Payment recorded for user {user_id}, plan {plan_id}.")
        return cursor.lastrowid # Return the payment_id
    except DatabaseError as e:
        print(f"Error adding payment: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error adding payment: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_payment_status(payment_id, payment_status, completed_at=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if completed_at is None:
            completed_at = datetime.datetime.now().isoformat()
        cursor.execute('''
            UPDATE Payment SET payment_status = ?, completed_at = ? WHERE payment_id = ?
        ''', (payment_status, completed_at, payment_id))
        conn.commit()
        print(f"Payment {payment_id} status updated to {payment_status}.")
    except DatabaseError as e:
        print(f"Error updating payment status: {e}")
    except sqlite3.Error as e:
        print(f"Database error updating payment status: {e}")
    finally:
        if conn:
            conn.close()

def add_transaction(payment_id, transaction_id, amount, provider_status, provider_response=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.datetime.now().isoformat()
        updated_at = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO Transaction (payment_id, transaction_id, amount, provider_status, provider_response, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (payment_id, transaction_id, amount, provider_status, provider_response, created_at, updated_at))
        conn.commit()
        print(f"Transaction recorded for payment {payment_id}.")
    except DatabaseError as e:
        print(f"Error adding transaction: {e}")
    except sqlite3.Error as e:
        print(f"Database error adding transaction: {e}")
    finally:
        if conn:
            conn.close()

def get_payment_details(payment_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT payment_id, user_id, plan_id, amount, payment_status FROM Payment WHERE payment_id = ?", (payment_id,))
        return cursor.fetchone()
    except DatabaseError as e:
        print(f"Error getting payment details: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error getting payment details: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_plan_by_id(plan_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT plan_id, name, price, credits, description FROM Plan WHERE plan_id = ?", (plan_id,))
        return cursor.fetchone()
    except DatabaseError as e:
        print(f"Error getting plan by id: {e}")
        return None
    except sqlite3.Error as e:
        print(f"Database error getting plan by id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def empty_all_tables():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        tables = ["User", "Plan", "Payment", "Transaction", "Message", "Cache", "API_Key"]
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Emptied table: {table}")

        conn.commit()
        print("All tables emptied successfully.")

    except DatabaseError as e:
        print(f"Error emptying tables: {e}")
    except sqlite3.Error as e:
        print(f"Database error emptying tables: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    create_tables()
    # Example of adding a plan (can be run once initially)
    # add_plan("Basic", 10.00, 100, "100 questions per month")
    
    # Uncomment the following line to empty all tables
    # empty_all_tables()
