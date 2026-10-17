import os

import resend
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for

load_dotenv()

app = Flask(__name__)

# ==============================
# EMAIL CONFIGURATION
# ==============================

BUSINESS_EMAIL = os.environ.get(
    "BUSINESS_EMAIL",
    "mifdigitalsolutions@gmail.com"
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
                "from": (
                    "MIF Digital Solutions "
                    "<onboarding@resend.dev>"
                ),
                "to": [BUSINESS_EMAIL],
                "reply_to": customer_email,
                "subject": (
                    f"New Project Enquiry: {service}"
                ),
                "text": (
                    "New project enquiry received "
                    "from the MIF Digital Solutions website.\n\n"
                    "CUSTOMER DETAILS\n"
                    "----------------\n"
                    f"Name: {name}\n"
                    f"Email: {customer_email}\n"
                    f"Service Requested: {service}\n"
                    f"Budget: {budget or 'Not specified'}\n\n"
                    "PROJECT MESSAGE\n"
                    "----------------\n"
                    f"{message}\n"
                ),
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
                type(error)._name_,
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


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":
    app.run(debug=False)