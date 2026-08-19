from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, DUTY_MANAGER_PHONE,
    LEASING_TEAM_EMAIL, LEASING_TEAM_PHONE, OPERATIONS_TEAM_EMAIL, OPERATIONS_TEAM_PHONE,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME,
)

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# ------------------------------------------------------------------
# Low-level senders
# ------------------------------------------------------------------
def send_whatsapp_message(recipient, message):
    """
    Sends a WhatsApp message via Twilio. `recipient` should be a plain phone
    number in E.164 format, e.g. "+96512345678".
    """
    number = "whatsapp:" + recipient
    twilio_client.messages.create(
        body=message,
        from_="whatsapp:" + TWILIO_WHATSAPP_NUMBER,
        to=number
    )

def send_sms(recipient, message):
    """
    Sends a plain SMS via Twilio (fallback if WhatsApp isn't set up yet).
    """
    twilio_client.messages.create(
        body=message,
        from_=TWILIO_WHATSAPP_NUMBER,  # your Twilio SMS-capable number
        to=recipient
    )

def send_email(to_address, subject, body):
    """
    Sends a plain-text email via SMTP. Configure SMTP_HOST / SMTP_USER /
    SMTP_PASSWORD in .env first (e.g. Gmail App Password, Outlook SMTP,
    or your company mail server).
    """
    if not to_address or not SMTP_HOST:
        print("Email not sent — missing recipient or SMTP config.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_address

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [to_address], msg.as_string())


def send_email_with_attachment(to_address, subject, body, attachment_path):
    """
    Sends an email with a file attached (e.g. the running complaints_log.xlsx
    or leads_log.xlsx). This is how the team receives the actual shared file,
    not just a text summary.
    """
    if not to_address or not SMTP_HOST:
        print("Email not sent — missing recipient or SMTP config.")
        return
    if not os.path.exists(attachment_path):
        print(f"Email not sent — attachment not found at {attachment_path}")
        return

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_address
    msg.attach(MIMEText(body))

    with open(attachment_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
    msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [to_address], msg.as_string())


# ------------------------------------------------------------------
# High-level team notifications — this is what actually gets called
# by save_lead() / save_complaint() in agent_tools.py
# ------------------------------------------------------------------
def notify_leasing_team(lead_data, lead_id, log_file_path=None):
    """
    Sends the full lead details to the leasing team via email + WhatsApp
    as soon as a shop rental enquiry is saved. If log_file_path is given,
    the running leads_log.xlsx file is attached to the email — this is the
    actual shared file the team works from.
    """
    subject = f"New Shop Rental Lead — A5 Mall (ID: {lead_id})"
    body = (
        f"A new shop rental enquiry has been captured by the AI Voice Assistant.\n\n"
        f"Lead ID: {lead_id}\n"
        f"Mall: {lead_data.get('mall_id')}\n"
        f"Shop Number: {lead_data.get('shop_number')}\n\n"
        f"--- Customer Details ---\n"
        f"Name: {lead_data.get('full_name')}\n"
        f"Phone: {lead_data.get('phone')}\n"
        f"Email: {lead_data.get('email')}\n"
        f"Address: {lead_data.get('address')}\n\n"
        f"--- Business Details ---\n"
        f"Business Name: {lead_data.get('business_name')}\n"
        f"Business Type: {lead_data.get('business_type')}\n"
        f"Officially Registered: {lead_data.get('is_registered')}\n\n"
        f"The attached file contains the full, up-to-date leads log.\n"
        f"Please follow up with the customer as soon as possible."
    )

    try:
        if log_file_path:
            send_email_with_attachment(LEASING_TEAM_EMAIL, subject, body, log_file_path)
        else:
            send_email(LEASING_TEAM_EMAIL, subject, body)
    except Exception as e:
        print(f"Error sending lead email: {e}")

    try:
        if LEASING_TEAM_PHONE:
            send_whatsapp_message(LEASING_TEAM_PHONE, body)
    except Exception as e:
        print(f"Error sending lead WhatsApp message: {e}")


def notify_operations_team(complaint_data, complaint_id, log_file_path=None):
    """
    Sends complaint details to the operations team via email + WhatsApp as
    soon as a complaint is saved. If log_file_path is given, the running
    complaints_log.xlsx file is attached — this is the actual shared file
    the team works from, updated with every new complaint.
    """
    urgency_label = "URGENT" if complaint_data.get("is_urgent") else "Standard"
    subject = f"[{urgency_label}] New Complaint — A5 Mall (ID: {complaint_id})"
    body = (
        f"A new complaint has been logged by the AI Voice Assistant.\n\n"
        f"Complaint ID: {complaint_id}\n"
        f"Priority: {urgency_label}\n"
        f"Mall: {complaint_data.get('mall_id')}\n\n"
        f"--- Caller Details ---\n"
        f"Name: {complaint_data.get('full_name')}\n"
        f"Phone: {complaint_data.get('phone')}\n\n"
        f"--- Issue ---\n"
        f"{complaint_data.get('issue')}\n\n"
        f"The attached file contains the full, up-to-date complaints log.\n"
        f"Please follow up as soon as possible."
    )

    try:
        if log_file_path:
            send_email_with_attachment(OPERATIONS_TEAM_EMAIL, subject, body, log_file_path)
        else:
            send_email(OPERATIONS_TEAM_EMAIL, subject, body)
    except Exception as e:
        print(f"Error sending complaint email: {e}")

    try:
        if OPERATIONS_TEAM_PHONE:
            send_whatsapp_message(OPERATIONS_TEAM_PHONE, body)
    except Exception as e:
        print(f"Error sending complaint WhatsApp message: {e}")


def escalate_to_duty_manager(mall_id, caller_name, caller_phone, issue):
    """
    Sends an INSTANT alert to the duty manager when a complaint is marked
    urgent — separate from and faster than the standard operations team
    notification above. Tries WhatsApp first; falls back to SMS if WhatsApp fails.
    """
    alert_text = (
        f"URGENT COMPLAINT — {mall_id}\n"
        f"Caller: {caller_name}\n"
        f"Phone: {caller_phone}\n"
        f"Issue: {issue}\n"
        f"Please respond as soon as possible."
    )
    try:
        send_whatsapp_message(DUTY_MANAGER_PHONE, alert_text)
    except Exception as e:
        print(f"WhatsApp alert failed, falling back to SMS: {e}")
        try:
            send_sms(DUTY_MANAGER_PHONE, alert_text)
        except Exception as e2:
            print(f"SMS alert also failed: {e2}")


