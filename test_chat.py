"""
Test the AI assistant directly in the terminal — no phone call, no Twilio,
no ngrok needed. This talks straight to the same conversation engine that
handles real calls, so it tests everything except the actual voice/audio part.

Usage: python test_chat.py
"""
from modules.chatbot import get_chatbot_response_agent
from modules.mongodb import set_user_language

TEST_PHONE = "+96500000001"  # any dummy number, used as your "caller ID" for this test

def main():
    print("=" * 60)
    print("A5 Mall AI Assistant — Terminal Test (no phone needed)")
    print("=" * 60)

    lang = input("Choose language — type 'ar' for Arabic or 'en' for English: ").strip().lower()
    if lang not in ("ar", "en"):
        lang = "en"
    set_user_language(TEST_PHONE, lang)

    print("\nType your messages as if you were the caller.")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue

        response = get_chatbot_response_agent(user_input, TEST_PHONE)
        print(f"Assistant: {response}\n")

if __name__ == "__main__":
    main()
