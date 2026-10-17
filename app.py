import os
import smtplib
import resend 
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

# ==============================
# EMAIL CONFIGURATION
# ==============================

BUSINESS_EMAIL = os.environ.get(
    "BUSINESS_EMAIL",
    "mifdigitalsolutions@gmail.com"
)

SMTP_EMAIL = os.environ.get("SMTP_EMAIL", BUSINESS_EMAIL)
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "")


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

        # Basic input-length validation
        if (
            len(name) > 120
            or len(customer_email) > 254
            or len(service) > 120
            or len(budget) > 120
            or len(message) > 10000
            or "\r" in customer_email
            or "\n" in customer_email
        ):
            return redirect(
                url_for("contact", status="invalid_input")
            )

        # Ensure Gmail configuration exists
        if not SMTP_EMAIL or not BUSINESS_EMAIL or not SMTP_APP_PASSWORD:
            app.logger.error(
                "Contact form email configuration is incomplete."
            )
            return redirect(
                url_for("contact", status="email_not_configured")
            )

        # Create the email
        email_message = EmailMessage()

        email_message["Subject"] = (
            f"New Project Enquiry: {service}"
        )

        email_message["From"] = SMTP_EMAIL
        email_message["To"] = BUSINESS_EMAIL
        email_message["Reply-To"] = customer_email

        email_message.set_content(
            f"""New project enquiry received from the MIF Digital Solutions website.

CUSTOMER DETAILS
----------------
Name: {name}
Email: {customer_email}
Service Requested: {service}
Budget: {budget or "Not specified"}

PROJECT MESSAGE
---------------
{message}
"""
        )

# Send email through Resend
        try:
            resend_api_key = os.environ.get(
                "RESEND_API_KEY", ""
            ).strip()

            if not resend_api_key:
                app.logger.error(
                    "RESEND_API_KEY is not configured."
                )
                return redirect(
                    url_for(
                        "contact",
                        status="email_not_configured"
                    )
                )

            resend.api_key = resend_api_key

            email_result = resend.Emails.send({
                "from": "MIF Digital Solutions <onboarding@resend.dev>",
                "to": [BUSINESS_EMAIL],
                "reply_to": customer_email,
                "subject": (
                    f"New Project Enquiry: "
                    f"{service or 'General Enquiry'}"
                ),
                "text": (
                    "New project enquiry received.\n\n"
                    f"Name: {name}\n"
                    f"Customer email: {customer_email}\n"
                    f"Requested service: "
                    f"{service or 'Not specified'}\n"
                    f"Budget: {budget or 'Not specified'}\n\n"
                    f"Message:\n{message}\n"
                ),
            })

            app.logger.info(
                "Contact form enquiry sent via Resend. "
                "Email ID: %s",
                email_result.get("id", "unknown")
            )

        except Exception as error:
            app.logger.exception(
                "Failed to send contact form enquiry "
                "through Resend. Error type: %s | Error: %s",
                type(error)._name_,
                error
            )
            return redirect(
                url_for("contact", status="send_failed")
            )

    # Display contact page and status messages
    return render_template(
        "contact.html",
        status=request.args.get("status", "")
    )


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":
    app.run(debug=False)