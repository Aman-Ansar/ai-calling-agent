import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
DUTY_MANAGER_PHONE = os.getenv("DUTY_MANAGER_PHONE", "")
PERSONAL_PHONE = os.getenv("PERSONAL_PHONE", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NGROK_URL = os.getenv("NGROK_URL", "")

MONGODB_URI = os.getenv("MONGODB_URI", "")

# --- LLM Provider switch: "openai" or "qwen" ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

# Qwen / Alibaba Cloud Model Studio (DashScope) settings — only used if LLM_PROVIDER=qwen
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID_EN = os.getenv("ELEVENLABS_VOICE_ID_EN", "")
ELEVENLABS_VOICE_ID_AR = os.getenv("ELEVENLABS_VOICE_ID_AR", "")

# Backend teams — where new leads / complaints get forwarded to
LEASING_TEAM_EMAIL = os.getenv("LEASING_TEAM_EMAIL", "")
LEASING_TEAM_PHONE = os.getenv("LEASING_TEAM_PHONE", "")     # WhatsApp-capable number, E.164 format
OPERATIONS_TEAM_EMAIL = os.getenv("OPERATIONS_TEAM_EMAIL", "")
OPERATIONS_TEAM_PHONE = os.getenv("OPERATIONS_TEAM_PHONE", "")

# SMTP (for email notifications)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "A5 Mall AI Assistant")


FLASK_APP='app.py'
FLASK_ENV='development'
