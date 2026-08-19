"""
Tools available to the AI voice assistant agent. Each function's docstring is
used by the LLM to decide WHEN and HOW to call it, so keep the docstrings
precise — they behave like mini-prompts.
"""
import datetime
from .mongodb import (
    get_userid_by_phone, get_chat_history, set_chat_history, update_chat_history,
    get_user, add_user, update_user, add_session_log, get_session_logs,
    add_therapy_progress, get_therapy_progress, update_therapy_progress,
    book_appointment, get_appointments, update_appointment, delete_appointment,
    find_available_shops, find_shop_by_number, set_shop_status,
    insert_lead, insert_complaint, get_mall_info,
)
from .sender import escalate_to_duty_manager, notify_leasing_team, notify_operations_team
from .file_logger import log_complaint_to_file, log_lead_to_file

DEFAULT_MALL_ID = "A5"  # pilot scope — only A5 Mall for now


# ------------------------------------------------------------------
# Legacy helpers (kept from the original project, used elsewhere)
# ------------------------------------------------------------------
def get_history(user_phone):
    """Retrieves the chat history for a specific user."""
    user_id = get_userid_by_phone(user_phone)
    return get_chat_history(user_id)

def set_history(user_phone, message_data):
    """Creates a new chat history record or updates an existing one for a user."""
    user_id = get_userid_by_phone(user_phone)
    set_chat_history(user_id, message_data)

def booking(user_phone, user_message, appointment_time):
    """Creates a booking record (legacy helper, kept for compatibility)."""
    user_id = get_userid_by_phone(user_phone)
    appointment_data = {
        "user_id": user_id,
        "location": user_message,
        "date": datetime.datetime.now(),
        "status": "pending",
        "appointment_time": appointment_time
    }
    book_appointment(user_id, appointment_data)


# ------------------------------------------------------------------
# A5 MALL CRM TOOLS — these are the ones referenced in the system prompt
# ------------------------------------------------------------------

def check_shop_availability(business_type: str = None, shop_number: str = None) -> dict:
    """
    Use this tool to check REAL, LIVE shop availability in A5 Mall. Call this
    BEFORE telling the caller anything about whether a shop is available — you
    have no availability information in memory, only this tool has current data.

    - If shop_number is provided (e.g. "G-19"), returns the exact status, size,
      and floor of that specific shop.
    - If only business_type is provided (no shop_number), returns a list of
      currently AVAILABLE shops that match that business category, so you can
      report general availability or suggest one to the caller.

    Never guess or fabricate shop numbers, sizes, or availability status —
    always rely on this tool's returned data.
    """
    mall_id = DEFAULT_MALL_ID
    if shop_number:
        shop = find_shop_by_number(mall_id, shop_number)
        if not shop:
            return {"found": False, "message": f"No shop numbered {shop_number} was found in A5 Mall."}
        return {"found": True, "shop": shop}

    matches = find_available_shops(mall_id, business_type=business_type, limit=5)
    return {
        "found": len(matches) > 0,
        "count": len(matches),
        "shops": matches,
    }


def save_lead(full_name: str, address: str, phone: str, email: str,
              business_name: str, business_type: str, is_registered: bool,
              shop_number: str = None) -> str:
    """
    Use this tool ONLY after the caller has confirmed a shop and provided all of:
    full name, address, phone number, email, business name, business type, and
    registration status. This writes the lead to the backend system and notifies
    the leasing team. Do not call this tool with incomplete information — ask the
    caller for any missing field first.
    """
    lead_data = {
        "mall_id": DEFAULT_MALL_ID,
        "shop_number": shop_number,
        "full_name": full_name,
        "address": address,
        "phone": phone,
        "email": email,
        "business_name": business_name,
        "business_type": business_type,
        "is_registered": is_registered,
    }
    lead_id = insert_lead(lead_data)

    # Mark the shop as tentatively reserved so it doesn't get double-booked
    if shop_number:
        set_shop_status(DEFAULT_MALL_ID, shop_number, "Pending Lease")

    # Append this lead to the shared Excel log file (leads_log.xlsx)
    try:
        log_path = log_lead_to_file(lead_data, lead_id)
    except Exception as e:
        print(f"Error writing lead to file log: {e}")
        log_path = None

    # Send the updated file to the leasing team — this is the actual
    # "send to backend team" step, with the real file attached
    try:
        notify_leasing_team(lead_data, lead_id, log_file_path=log_path)
    except Exception as e:
        print(f"Error notifying leasing team: {e}")

    return f"Lead saved successfully (ID: {lead_id}). The leasing team has been notified."


def save_complaint(full_name: str, phone: str, issue: str, is_urgent: bool) -> str:
    """
    Use this tool once the caller has described their complaint, provided a
    phone number, and confirmed whether it is urgent. This logs the complaint
    and, if is_urgent is True, automatically triggers an instant alert to the
    duty manager. Do not call this tool until urgency has been explicitly
    asked and answered.
    """
    complaint_data = {
        "mall_id": DEFAULT_MALL_ID,
        "full_name": full_name,
        "phone": phone,
        "issue": issue,
        "is_urgent": is_urgent,
    }
    complaint_id = insert_complaint(complaint_data)

    # Append this complaint to the shared Excel log file (complaints_log.xlsx)
    try:
        log_path = log_complaint_to_file(complaint_data, complaint_id)
    except Exception as e:
        print(f"Error writing complaint to file log: {e}")
        log_path = None

    # Send the updated file to the operations team — this is the actual
    # "send to backend team" step, with the real file attached
    try:
        notify_operations_team(complaint_data, complaint_id, log_file_path=log_path)
    except Exception as e:
        print(f"Error notifying operations team: {e}")

    # Urgent complaints ALSO get an instant, separate alert to the duty manager
    if is_urgent:
        try:
            escalate_to_duty_manager(DEFAULT_MALL_ID, full_name, phone, issue)
        except Exception as e:
            print(f"Error escalating urgent complaint to duty manager: {e}")

    return f"Complaint saved successfully (ID: {complaint_id})."


def get_general_mall_info() -> dict:
    """
    Use this tool if the caller asks a general question about the mall itself —
    such as address, opening hours, parking, or contact details — rather than
    about renting a shop or filing a complaint. Returns the mall's reference
    information. Never fabricate mall details; use only what this tool returns.
    """
    info = get_mall_info(DEFAULT_MALL_ID)
    if not info:
        return {"found": False, "message": "Mall information is not available right now."}
    return {"found": True, "info": info}
