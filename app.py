import os
import smtplib

from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for


app = Flask(__name__)


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

        name = request.form.get("name", "").strip()
        customer_email = request.form.get("email", "").strip()
        service = request.form.get("service", "").strip()
        budget = request.form.get("budget", "").strip()
        message = request.form.get("message", "").strip()

        # Basic server-side validation
        if not all([name, customer_email, service, message]):
            return redirect(
                url_for("contact", status="missing_fields")
            )

        if (
            len(name) > 120
            or len(customer_email) > 254
            or len(service) > 120
            or len(message) > 10000
        ):
            return redirect(
                url_for("contact", status="invalid_input")
            )

        # Email delivery must be configured before submissions
        # can be delivered.
        if not SMTP_APP_PASSWORD:
            app.logger.error(
                "Contact form email is not configured."
            )

            return redirect(
                url_for("contact", status="email_not_configured")
            )

        # Construct the email
        email_message = EmailMessage()

        email_message["Subject"] = (
            f"New Project Enquiry: {service}"
        )

        email_message["From"] = SMTP_EMAIL
        email_message["To"] = BUSINESS_EMAIL
        email_message["Reply-To"] = customer_email

        email_message.set_content(
            f"""
NEW PROJECT ENQUIRY
MIF Digital Solutions
==============================

Customer Name: {name}
Customer Email: {customer_email}

Service Required: {service}
Estimated Budget: {budget or "Not specified"}

PROJECT DETAILS
---------------
{message}

==============================
Sent through the MIF Digital Solutions website.
"""
        )

        # Send the email through Gmail
        try:
            with smtplib.SMTP_SSL(
                "smtp.gmail.com",
                465,
                timeout=20
            ) as server:

                server.login(
                    SMTP_EMAIL,
                    SMTP_APP_PASSWORD
                )

                server.send_message(email_message)

            app.logger.info(
                "Contact enquiry email sent successfully."
            )

            return redirect(
                url_for("contact", status="success")
            )

        except Exception:
            # Log the technical error without exposing credentials
            # or SMTP details to website visitors.
            app.logger.exception(
                "Failed to send contact form enquiry."
            )

            return redirect(
                url_for("contact", status="send_failed")
            )

    return render_template(
        "contact.html",
        status=request.args.get("status", "")
    )


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":
    app.run(debug=False)