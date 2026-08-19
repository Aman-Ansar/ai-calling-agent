"""
Conversation engine for the A5 Mall AI Voice Assistant.

Uses the raw OpenAI-compatible SDK with manual function-calling (no LangChain
agent framework) — this works identically against OpenAI and Qwen/DashScope,
and avoids depending on LangChain's agent APIs, which have changed several
times across versions and can break unexpectedly.
"""
import json
import re
from openai import OpenAI

from .agent_tools import (
    booking, get_history, set_history,
    check_shop_availability, save_lead, save_complaint, get_general_mall_info,
)
from .prompts import get_system_prompt
from .mongodb import get_user_language, set_user_language
from config import (
    OPENAI_API_KEY, LLM_PROVIDER, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, QWEN_MODEL,
)

# Matches emoji and other pictographic symbols that sound wrong when read
# aloud by text-to-speech on a phone call.
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols & pictographs, emoticons, transport, supplemental
    "\U00002600-\U000027BF"  # misc symbols & dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicator symbols (flags)
    "\U00002190-\U000021FF"  # arrows
    "\U00002B00-\U00002BFF"  # misc symbols and arrows
    "\U0000FE0F"             # variation selector (emoji presentation)
    "]+",
    flags=re.UNICODE,
)


def clean_for_speech(text: str) -> str:
    """
    Strips emojis and similar symbols from AI-generated text before it's
    spoken on a call — these get read aloud awkwardly (or spelled out) by
    text-to-speech engines, which sounds unprofessional.
    """
    if not text:
        return text
    cleaned = EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned

client = OpenAI(
    api_key=DASHSCOPE_API_KEY if LLM_PROVIDER == "qwen" else OPENAI_API_KEY,
    base_url=DASHSCOPE_BASE_URL if LLM_PROVIDER == "qwen" else None,
)

MODEL_NAME = QWEN_MODEL if LLM_PROVIDER == "qwen" else "gpt-4o-mini"

# Map of tool name -> actual Python function, used to execute tool calls
AVAILABLE_TOOLS = {
    "check_shop_availability": check_shop_availability,
    "save_lead": save_lead,
    "save_complaint": save_complaint,
    "get_general_mall_info": get_general_mall_info,
}

# JSON schema definitions for each tool, in OpenAI/DashScope function-calling
# format. These, plus each function's docstring (used as "description"),
# are what the model uses to decide when and how to call each tool.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_shop_availability",
            "description": check_shop_availability.__doc__.strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "business_type": {"type": "string", "description": "The caller's business category, e.g. 'Cafe', 'Fashion'."},
                    "shop_number": {"type": "string", "description": "A specific shop number to check, e.g. 'G-19'."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_lead",
            "description": save_lead.__doc__.strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "address": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "business_name": {"type": "string"},
                    "business_type": {"type": "string"},
                    "is_registered": {"type": "boolean"},
                    "shop_number": {"type": "string"},
                },
                "required": ["full_name", "address", "phone", "email", "business_name", "business_type", "is_registered"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_complaint",
            "description": save_complaint.__doc__.strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "issue": {"type": "string"},
                    "is_urgent": {"type": "boolean"},
                },
                "required": ["full_name", "phone", "issue", "is_urgent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_general_mall_info",
            "description": get_general_mall_info.__doc__.strip(),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def book_appointment(user_phone: str, user_message: str, appointment_time: str) -> str:
    """Book an appointment for the user"""
    if not user_phone:
        return "Please provide your phone number"
    if not user_message:
        return "Please provide your location"
    booking(user_phone, user_message, appointment_time)
    return "Your appointment has been booked"


def _load_history_messages(user_phone, history):
    """Loads prior turns from MongoDB into plain OpenAI-format message dicts."""
    msg = []
    try:
        history_records = get_history(user_phone)
        if history_records and "messages" in history_records:
            for message_data in history_records["messages"]:
                msg.append({"role": message_data["role"], "content": message_data["content"]})
        else:
            starter_message = "Welcome to A5 Mall. How can I help you today?"
            msg.append({"role": "assistant", "content": starter_message})
            history["messages"].append({"role": "assistant", "content": starter_message})
    except Exception as e:
        history["messages"] = []
        starter_message = "Welcome to A5 Mall. How can I help you today?"
        msg.append({"role": "assistant", "content": starter_message})
        history["messages"].append({"role": "assistant", "content": starter_message})
        print(f"Error in getting chat history: {e}")
    return msg


def get_chatbot_response_agent(query, user_phone, history=None):
    """
    Main conversation entry point. Sends the query + history + tool
    definitions to the model, executes any tool calls it requests, and
    loops until the model returns a plain text reply.
    """
    if history is None:
        history = {"messages": []}

    prior_messages = _load_history_messages(user_phone, history)
    prior_messages.append({"role": "user", "content": query})
    history["messages"].append({"role": "user", "content": query})

    language = get_user_language(user_phone)  # returns "ar" or "en"
    system_prompt_text = get_system_prompt(language)

    messages = [{"role": "system", "content": system_prompt_text}] + prior_messages

    # Tool-calling loop: keep going until the model replies without requesting a tool call
    max_turns = 7
    final_text = ""
    save_tool_called = False  # tracks whether save_lead/save_complaint actually ran this turn
    COMPLETION_KEYWORDS = [
        "forwarded", "recorded", "logged", "registered your", "saved your",
        "leasing team will", "our team will", "has been saved", "has been logged",
    ]

    for turn_i in range(max_turns):
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=0.4,
                max_tokens=350,  # must be large enough for full save_lead/save_complaint JSON tool calls, not just short replies
                timeout=15,  # give up after 15s instead of hanging the call
            )
        except Exception as e:
            import traceback
            print(f"\n[LLM API ERROR] {type(e).__name__}: {e}")
            traceback.print_exc()
            final_text = "I'm sorry, I'm having a little trouble connecting right now. Let me have our team call you back shortly."
            break

        choice = completion.choices[0].message

        if not choice.tool_calls:
            final_text = choice.content or ""

            # Safety net: the model just claimed something was saved/forwarded,
            # but never actually called save_lead / save_complaint this turn.
            # Force it to make the real tool call before we trust the claim.
            if not save_tool_called and any(k in final_text.lower() for k in COMPLETION_KEYWORDS):
                print(f"\n[WARNING] Model claimed completion without calling a save tool. Forcing a retry.")
                messages.append({"role": "assistant", "content": final_text})
                messages.append({
                    "role": "system",
                    "content": (
                        "You just told the caller their information was saved/forwarded, "
                        "but you did NOT actually call the save_lead or save_complaint tool. "
                        "Call the correct tool right now, using all the details already "
                        "collected in this conversation, before saying anything else."
                    ),
                })
                continue

            break

        # The model wants to call one or more tools — execute each, then
        # feed the results back so the model can produce its final reply.
        messages.append({
            "role": "assistant",
            "content": choice.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.tool_calls
            ],
        })

        for tc in choice.tool_calls:
            func = AVAILABLE_TOOLS.get(tc.function.name)
            print(f"\n[TOOL CALL] {tc.function.name}({tc.function.arguments})")
            if tc.function.name in ("save_lead", "save_complaint"):
                save_tool_called = True
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                result = func(**args) if func else {"error": f"Unknown tool {tc.function.name}"}
                print(f"[TOOL RESULT] {result}\n")
            except Exception as e:
                result = {"error": str(e)}
                print(f"[TOOL ERROR] {e}\n")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })
    else:
        final_text = "I'm having trouble processing that right now — let me have our team follow up with you."

    final_text = clean_for_speech(final_text)

    history["messages"].append({"role": "assistant", "content": final_text})
    set_history(user_phone, history["messages"])

    return final_text


def get_chatbot_response(query, user_phone, history=[]):
    """Simple, tool-free fallback (used only if the agent path is unavailable)."""
    language = get_user_language(user_phone)
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": get_system_prompt(language)},
            {"role": "user", "content": query}
        ],
        max_tokens=200,
        temperature=0.5
    )
    return completion.choices[0].message.content
