import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# TODO: Get ZarinPal Merchant ID from environment variables or a secure location
ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID", "YOUR_ZARINPAL_MERCHANT_ID") # Placeholder

# ZarinPal API Endpoints (verify with ZarinPal documentation)
ZARINPAL_REQUEST_URL = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZARINPAL_VERIFY_URL = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZARINPAL_STARTPAY_URL = "https://www.zarinpal.com/pg/StartPay/"

def create_payment_request(amount, description, callback_url, metadata=None):
    """
    Creates a payment request with ZarinPal.

    Args:
        amount (float): The payment amount in Toman.
        description (str): A description for the payment.
        callback_url (str): The URL ZarinPal should redirect to after payment.
        metadata (dict, optional): Optional metadata to include. Defaults to None.

    Returns:
        tuple: (authority, payment_url) if successful, otherwise (None, None).
    """
    if not ZARINPAL_MERCHANT_ID or ZARINPAL_MERCHANT_ID == "YOUR_ZARINPAL_MERCHANT_ID":
        print("شناسه مرچنت زرین پال پیکربندی نشده است.") # ZarinPal Merchant ID not configured.
        return None, None

    payload = {
        "merchant_id": ZARINPAL_MERCHANT_ID,
        "amount": amount,
        "description": description,
        "callback_url": callback_url,
        "metadata": metadata
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(ZARINPAL_REQUEST_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes
        response_data = response.json()

        if response_data['data'] and response_data['data']['code'] == 100:
            authority = response_data['data']['authority']
            payment_url = ZARINPAL_STARTPAY_URL + authority
            return authority, payment_url
        else:
            print(f"درخواست زرین پال ناموفق بود: {response_data['errors']['code']} - {response_data['errors']['message']}") # ZarinPal request failed: {response_data['errors']['code']} - {response_data['errors']['message']}
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"خطا در ایجاد درخواست پرداخت زرین پال: {e}") # Error creating ZarinPal payment request: {e}
        return None, None

def verify_payment(authority, amount):
    """
    Verifies a completed payment with ZarinPal.

    Args:
        authority (str): The authority received in the callback.
        amount (float): The amount to verify (should match the request amount).

    Returns:
        tuple: (True, ref_id) if successful, otherwise (False, error_message).
    """
    if not ZARINPAL_MERCHANT_ID or ZARINPAL_MERCHANT_ID == "YOUR_ZARINPAL_MERCHANT_ID":
        return False, "شناسه مرچنت زرین پال پیکربندی نشده است."

    payload = {
        "merchant_id": ZARINPAL_MERCHANT_ID,
        "authority": authority,
        "amount": amount
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(ZARINPAL_VERIFY_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes
        response_data = response.json()

        if response_data['data'] and response_data['data']['code'] == 100:
            ref_id = response_data['data']['ref_id']
            return True, ref_id
        else:
            return False, f"تایید پرداخت زرین پال ناموفق بود: {response_data['errors']['code']} - {response_data['errors']['message']}" # ZarinPal verification failed: {response_data['errors']['code']} - {response_data['errors']['message']}
    except requests.exceptions.RequestException as e:
        return False, f"خطا در تایید پرداخت زرین پال: {e}" # Error verifying ZarinPal payment: {e}

if __name__ == '__main__':
    # Example usage (requires a valid Merchant ID and a running callback URL)
    # print("Creating a test payment request...")
    # test_amount = 1000 # in Toman
    # test_description = "Test payment for bot credits"
    # test_callback_url = "YOUR_CALLBACK_URL" # Replace with your actual callback URL
    #
    # authority, payment_url = create_payment_request(test_amount, test_description, test_callback_url)
    #
    # if authority and payment_url:
    #     print(f"Payment URL: {payment_url}")
    #     print(f"Authority: {authority}")
    # else:
    #     print("Failed to create payment request.")

    # Example verification (requires a valid authority and amount from a completed payment)
    # print("\nVerifying a test payment...")
    # test_authority = "YOUR_AUTHORITY" # Replace with a real authority from a test payment
    # test_verify_amount = 1000 # Replace with the actual amount
    #
    # success, result = verify_payment(test_authority, test_verify_amount)
    #
    # if success:
    #     print(f"Payment verified successfully. Reference ID: {result}")
    # else:
    #     print(f"Payment verification failed: {result}")
    pass
