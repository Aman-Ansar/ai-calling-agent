from pymongo import MongoClient
from datetime import datetime
from config import MONGODB_URI

if not MONGODB_URI:
    raise RuntimeError(
        "MONGODB_URI is not set. Add it to your .env file, e.g.\n"
        'MONGODB_URI="mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority"\n'
        "Get this from MongoDB Atlas: Database > Connect > Drivers > Python."
    )

client = MongoClient(MONGODB_URI)
db = client.Cluster0
# Collection Definitions
users_collection = db.users
session_logs_collection = db.session_logs
therapy_progress_collection = db.therapy_progress
appointments_collection = db.appointments
chat_history_collection = db.chat_history

# A5 Mall CRM collections
malls_collection = db.malls
shops_collection = db.shops
leads_collection = db.leads
complaints_collection = db.complaints

# User operations
def add_user(user_data):
    return users_collection.insert_one(user_data).inserted_id

def get_user(user_id):
    return users_collection.find_one({"_id": user_id})

def update_user(user_id, update_data):
    users_collection.update_one({"_id": user_id}, {"$set": update_data})

def get_userid_by_phone(phone):
    return users_collection.find_one({"phone": phone})['_id']

def verify_user(phone):
    return users_collection.find_one({"phone": phone}) is not None

def has_interacted_before(phone):
    user = users_collection.find_one({"phone": phone})
    if user is not None:
        return user.get('has_interacted_before', False)
    return False

def set_interacted_before(phone):
    users_collection.update_one({"phone": phone}, {"$set": {"has_interacted_before": True}})
    return True


# Session logs operations
def add_session_log(session_data):
    return session_logs_collection.insert_one(session_data).inserted_id

def get_session_logs(user_id):
    return list(session_logs_collection.find({"user_id": user_id}))

# Therapy progress operations
def add_therapy_progress(progress_data):
    return therapy_progress_collection.insert_one(progress_data).inserted_id

def get_therapy_progress(user_id):
    return list(therapy_progress_collection.find({"user_id": user_id}))

def update_therapy_progress(progress_id, update_data):
    therapy_progress_collection.update_one({"_id": progress_id}, {"$set": update_data})

# Appointment operations
def book_appointment(userid,appointment_data):
    return appointments_collection.insert_one({"user_id":userid},{"appointment_data":appointment_data})

def get_appointments(user_id):
    return list(appointments_collection.find({"user_id": user_id}))

def update_appointment(appointment_id, update_data):
    appointments_collection.update_one({"_id": appointment_id}, {"$set": update_data})

def delete_appointment(appointment_id):
    appointments_collection.delete_one({"_id": appointment_id})

# Language preference operations
def set_user_language(phone, language):
    """
    Stores the caller's language choice ("ar" or "en") against their phone number,
    so every subsequent turn in the same call uses the same prompt.
    """
    users_collection.update_one(
        {"phone": phone},
        {"$set": {"language": language}},
        upsert=True
    )

def get_user_language(phone):
    """
    Retrieves the caller's stored language choice. Defaults to English if not set.
    """
    user = users_collection.find_one({"phone": phone})
    if user is not None:
        return user.get("language", "en")
    return "en"

def set_chat_history(user_id, message_data):
    """
    Creates a new chat history record or updates an existing one for a user.
    """
    chat_history_collection.update_one(
        {"user_id": user_id},
        {"$push": {"messages": {"$each": message_data}}},  # Using $each to add all elements
        upsert=True
    )

def get_chat_history(user_id):
    """
    Retrieves the chat history for a specific user.
    """
    return chat_history_collection.find_one({"user_id": user_id})

def update_chat_history(user_id, update_data):
    """
    Updates the chat history record for a specific user.
    """
    chat_history_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )


# ============================================================
# A5 MALL CRM — shop availability, leads, complaints
# ============================================================

# ---------- Shops ----------
def find_available_shops(mall_id, business_type=None, limit=5):
    """
    Returns available shops in a mall, optionally filtered by business category.
    If business_type is given, tries an exact category match first; if none found,
    falls back to any available shop in that mall (better to suggest something
    than nothing).
    """
    query = {"mall_id": mall_id, "status": "Available"}
    if business_type:
        query["category"] = {"$regex": business_type, "$options": "i"}
        results = list(shops_collection.find(query, {"_id": 0}).limit(limit))
        if results:
            return results
        # fallback: no exact category match, return any available shop
        fallback_query = {"mall_id": mall_id, "status": "Available"}
        return list(shops_collection.find(fallback_query, {"_id": 0}).limit(limit))
    return list(shops_collection.find(query, {"_id": 0}).limit(limit))

def find_shop_by_number(mall_id, shop_number):
    """
    Returns the real, current record for one specific shop number in a mall,
    including its live status (Available / Rented), size, and floor.
    """
    return shops_collection.find_one(
        {"mall_id": mall_id, "shop_number": shop_number},
        {"_id": 0}
    )

def set_shop_status(mall_id, shop_number, status):
    """
    Updates a shop's status (e.g. to "Rented" once a lease is finalized).
    """
    shops_collection.update_one(
        {"mall_id": mall_id, "shop_number": shop_number},
        {"$set": {"status": status}}
    )

def seed_shops(shop_records):
    """
    Bulk-loads shop inventory records (used once, to import the demo/real data).
    Each record should look like:
    {"mall_id": "A5", "shop_number": "G-01", "floor": "Ground", "size_sqft": 300,
     "category": "Fashion & Apparel", "status": "Available", "rent_kwd": 750}
    """
    if not shop_records:
        return 0
    result = shops_collection.insert_many(shop_records)
    return len(result.inserted_ids)


# ---------- Leads (shop rental enquiries) ----------
def insert_lead(lead_data):
    """
    Saves a completed shop-rental lead record to the database and returns its ID.
    """
    lead_data["created_at"] = datetime.utcnow()
    lead_data["status"] = "New"
    return str(leads_collection.insert_one(lead_data).inserted_id)

def get_leads(mall_id=None):
    query = {"mall_id": mall_id} if mall_id else {}
    return list(leads_collection.find(query, {"_id": 0}))


# ---------- Complaints ----------
def insert_complaint(complaint_data):
    """
    Saves a complaint record to the database and returns its ID.
    """
    complaint_data["created_at"] = datetime.utcnow()
    complaint_data["status"] = "Open"
    return str(complaints_collection.insert_one(complaint_data).inserted_id)

def get_complaints(mall_id=None, urgent_only=False):
    query = {}
    if mall_id:
        query["mall_id"] = mall_id
    if urgent_only:
        query["is_urgent"] = True
    return list(complaints_collection.find(query, {"_id": 0}))


# ---------- Malls ----------
def get_mall_info(mall_id):
    """
    Returns general mall details (address, timings, contacts) used to answer
    general caller questions about the mall itself.
    """
    return malls_collection.find_one({"mall_id": mall_id}, {"_id": 0})

def seed_mall(mall_data):
    malls_collection.update_one(
        {"mall_id": mall_data["mall_id"]},
        {"$set": mall_data},
        upsert=True
    )