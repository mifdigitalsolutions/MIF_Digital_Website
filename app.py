import os
import sqlite3
from datetime import datetime, timezone
import requests
import resend
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf.csrf import CSRFProtect
load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is not configured.")

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=1 * 1024 * 1024
)

csrf = CSRFProtect(app)
def init_orders_db():
    conn = sqlite3.connect("orders.db")
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                service TEXT NOT NULL,
                amount INTEGER NOT NULL,
                payment_reference TEXT UNIQUE NOT NULL,
                payment_status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_order(customer_email, service, amount, payment_reference):
    conn = sqlite3.connect("orders.db")

    try:
        conn.execute("""
            INSERT INTO orders (
                customer_email,
                service,
                amount,
                payment_reference,
                payment_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_email,
            service,
            amount,
            payment_reference,
            "successful",
            datetime.now(timezone.utc).isoformat()
        ))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


init_orders_db()
# ==============================
# EMAIL CONFIGURATION
# ==============================

BUSINESS_EMAIL = os.environ.get(
    "BUSINESS_EMAIL",
    "hello@mifdigitalsolutions.com"
).strip()


# ==============================
# HOME PAGE
# ==============================

@app.route("/")
def home():
    return render_template("index.html")


# ==============================
# SERVICES PAGE
# ==============================

@app.route("/services")
def services():
    return render_template("services.html")


# ==============================
# ABOUT PAGE
# ==============================

@app.route("/about")
def about():
    return render_template("about.html")


# ==============================
# CONTACT PAGE
# ==============================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        # Collect form data
        name = request.form.get("name", "").strip()
        customer_email = request.form.get("email", "").strip()
        service = request.form.get("service", "").strip()
        budget = request.form.get("budget", "").strip()
        message = request.form.get("message", "").strip()

        # Validate required fields
        if not all([name, customer_email, service, message]):
            return redirect(
                url_for("contact", status="missing_fields")
            )

        # Validate input lengths and email header safety
        if (
            len(name) > 120
            or len(customer_email) > 254
            or len(service) > 120
            or len(budget) > 120
            or len(message) > 10000
            or "\r" in customer_email
            or "\n" in customer_email
            or "@" not in customer_email
        ):
            return redirect(
                url_for("contact", status="invalid_input")
            )

        # Check email configuration
        resend_api_key = os.environ.get(
            "RESEND_API_KEY", ""
        ).strip()

        if not BUSINESS_EMAIL or not resend_api_key:
            app.logger.error(
                "Contact form Resend configuration is incomplete."
            )
            return redirect(
                url_for(
                    "contact",
                    status="email_not_configured"
                )
            )

        # Send email through Resend
        try:
            resend.api_key = resend_api_key

            email_result = resend.Emails.send({
    "from": f"MIF Digital Solutions <{os.getenv('FROM_EMAIL')}>",
    "to": [BUSINESS_EMAIL],
    "reply_to": customer_email,
    "subject": f"New Project Enquiry: {service}",
    "text": (
        "New project enquiry received.\n\n"
        "From the MIF Digital Solutions website.\n\n"
        "CUSTOMER DETAILS\n"
        "------------------------\n"
        f"Name: {name}\n"
        f"Email: {customer_email}\n"
        f"Service: {service}\n"
        f"Budget: {budget}\n\n"
        "MESSAGE\n"
        f"{message}\n"
    )
})

            app.logger.info(
                "Contact enquiry sent through Resend. "
                "Email ID: %s",
                email_result.get("id", "unknown")
            )

        except Exception as error:
            app.logger.exception(
                "Failed to send contact enquiry through Resend. "
                "Error type: %s | Error: %s",
                type(error).__name__,
                error
            )
            return redirect(
                url_for("contact", status="send_failed")
            )

        # Redirect after successful submission
        return redirect(
            url_for("contact", status="success")
        )

    # Display contact page and status messages
    return render_template(
        "contact.html",
        status=request.args.get("status", "")
    )



# ============================================================
# PAYSTACK PAYMENT CONFIGURATION
# ============================================================

import uuid
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")

# =====================================================
# MIF DIGITAL SOLUTIONS - OFFICIAL PAYMENT PACKAGES
# =====================================================

PAYMENT_PACKAGES = {
    "business_starter_website": {
        "name": "Business Starter Website",
        "amount_naira": 150000
    },

    "business_automation_starter": {
        "name": "Business Automation Starter",
        "amount_naira": 100000
    },

    "google_business_profile_guidance": {
        "name": "Google Business Profile Guidance",
        "amount_naira": 30000
    }
}
@app.route("/payment/start", methods=["POST"])
def start_payment():

    # Check Paystack configuration
    if not PAYSTACK_SECRET_KEY or not PAYSTACK_SECRET_KEY.startswith("sk_test_"):
        return "Paystack test key is missing or invalid.", 500

    # Get customer email
    customer_email = request.form.get("email", "").strip()

    if not customer_email or "@" not in customer_email:
        return "Please provide a valid email address.", 400

    # Get selected package
    package_id = request.form.get("package_id", "").strip()

    # Find official server-side price
    package = PAYMENT_PACKAGES.get(package_id)

    if not package:
        return "Invalid service package selected.", 400

    # Convert naira to kobo
    amount_kobo = int(package["amount_naira"] * 100)

    # Generate unique reference
    reference = uuid.uuid4().hex

    try:
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",

            headers={
                "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            },

            json={
                "email": customer_email,
                "amount": amount_kobo,
                "currency": "NGN",
                "reference": reference,

                "callback_url": url_for(
                    "verify_payment",
                    _external=True
                ),

                "metadata": {
                    "package_id": package_id,
                    "service": package["name"]
                }
            },

            timeout=20
        )

        result = response.json()

        authorization_url = result.get(
            "data", {}
        ).get("authorization_url")

        if response.ok and result.get("status") and authorization_url:
            return redirect(authorization_url)

        app.logger.error(
            "Paystack initialization failed: %s",
            result.get("message", "Unknown error")
        )

        return "Unable to start payment. Please try again.", 502

    except (requests.RequestException, ValueError):
        app.logger.exception("Paystack connection failed.")
        return "Payment service is temporarily unavailable.", 502

@app.route("/payment/verify")
def verify_payment():
    reference = request.args.get("reference", "").strip()

    if not reference or len(reference) > 200:
        return "<h1>Invalid payment reference</h1>", 400

    if not PAYSTACK_SECRET_KEY:
        app.logger.error("Paystack secret key is missing.")
        return "<h1>Payment verification is not configured.</h1>", 500

    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={
                "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                "Accept": "application/json",
            },
            timeout=20,
        )

        result = response.json()
        data = result.get("data", {})
        metadata = data.get("metadata", {})

        package_id = metadata.get("package_id")
        package = PAYMENT_PACKAGES.get(package_id)

        expected_amount = (
                int(package["amount_naira"]) * 100
                if package else None
            )

        if (
            response.ok
            and result.get("status") is True
            and data.get("status") == "success"
            and data.get("reference") == reference
            and data.get("currency") == "NGN"
            and expected_amount is not None
            and data.get("amount") == expected_amount
        ):
            return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Successful | MIF Digital Solutions</title>
</head>
<body>
    <h1>Payment Successful!</h1>
    <p>Thank you for choosing MIF Digital Solutions.</p>
    <p>Your payment has been verified successfully.</p>
    <a href="/">Return to Homepage</a>
</body>
</html>
"""

        return (
            "<h1>Payment not confirmed</h1>"
            "<p>Please contact MIF Digital Solutions if you believe this is an error.</p>",
            400,
        )


    except requests.RequestException:
        app.logger.exception("Paystack payment verification failed.")
        return (
            "<h1>Unable to verify payment</h1>"
            "<p>Please try again later.</p>",
            502,
        )

    except ValueError:
        app.logger.exception("Invalid response received from Paystack.")
        return "<h1>Invalid payment response</h1>", 502
# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":
    app.run(debug=False)