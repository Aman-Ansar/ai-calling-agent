from flask import Flask, request, url_for
from modules.twilio_api import handle_incoming_call
from modules.twilio_api import initiate_call
from flask import jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN , NGROK_URL
from twilio.rest import Client
from modules.chatbot import get_chatbot_response_agent, get_chatbot_response
from modules.tts import synthesize_speech
from modules.mongodb import set_user_language, get_user_language
import os
from datetime import datetime
from flask_cors import cross_origin
from flask_cors import CORS
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
static_dir = os.path.join(os.getcwd(), './static')

app = Flask(__name__)
ngrok_url=NGROK_URL
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Authorization", "Content-Type"]}})

@app.route('/', methods=['GET'])
def index():
    response_data = {
        "message": "Welcome to the AI calling agent Bot API Ver-1.2.2",
        "status": "success",
    }
    return jsonify(response_data)

@app.route('/voice', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])

def voice():
    return handle_incoming_call(request.values)

@app.route('/select_language', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def select_language():
    """
    Handles the caller's language choice (1 = Arabic, 2 = English), captured via
    DTMF (key press) or speech, and stores it against their phone number BEFORE
    the main conversation starts. All later turns look this up via get_user_language().
    """
    request_body = request.values
    caller_phone = request_body.get('From') or request_body.get('To')
    digit_choice = request_body.get('Digits')       # if caller pressed a key
    speech_choice = request_body.get('SpeechResult')  # if caller said it

    language = "en"  # default fallback
    if digit_choice == "1" or (speech_choice and "arabic" in speech_choice.lower()) or (speech_choice and "عربي" in speech_choice):
        language = "ar"
    elif digit_choice == "2" or (speech_choice and "english" in speech_choice.lower()):
        language = "en"

    set_user_language(caller_phone, language)

    response = VoiceResponse()
    gather = Gather(input='dtmf speech', numDigits=1, timeout=8, speechTimeout='auto',
                     action=f'https://{ngrok_url}/handle_speech1')
    if language == "ar":
        gather.say("مرحباً بكم في مجمع A5. هل يمكنني معرفة اسمكم الكريم؟", voice='Polly.Hala-Neural', language='ar-AE')
    else:
        gather.say("Welcome to A5 Mall. Can I know your good name, please?", voice='Polly.Joanna-Generative')
    response.append(gather)
    return str(response)

@app.route('/response_audio', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])

def response_audio():
    response = VoiceResponse()
    _play_url = f"https://{ngrok_url}/static/response.mp3"
    print(f"[AUDIO URL] {_play_url}")
    response.play(_play_url)
    return str(response)

@app.route('/make_call', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])

def make_call():
    phone_number = request.args.get('phone_number')
    if phone_number:
        call_status = initiate_call(phone_number)
        return jsonify({"message": "Call initiated to " + phone_number, "status": call_status})
    else:
        return jsonify({"error": "Phone number is required"}), 400

@app.route('/handle_speech', methods=['POST','GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def handle_speech():
    request_body = request.values
    response = VoiceResponse()
    if 'SpeechResult' in request_body:
        user_speech = request_body['SpeechResult']
        user_phone = request_body.get('To')
        language = get_user_language(user_phone)
        # Use the agent version so it can call check_shop_availability / save_lead / save_complaint
        _t0 = datetime.now()
        chat_response = get_chatbot_response_agent(user_speech, user_phone)
        print(f"[TIMING] LLM response took {(datetime.now() - _t0).total_seconds():.2f}s")

        # Speak the response using ElevenLabs (premium voice quality).
        # If ElevenLabs fails for any reason, automatically fall back to
        # Twilio's built-in voice so the call is never silent.
        _t1 = datetime.now()
        audio_filename = synthesize_speech(chat_response, f"response_{datetime.now().timestamp()}", language=language)
        print(f"[TIMING] TTS took {(datetime.now() - _t1).total_seconds():.2f}s")
        print(f"[TIMING] TOTAL so far: {(datetime.now() - _t0).total_seconds():.2f}s")
        if audio_filename:
            _play_url = f"https://{ngrok_url}/static/{audio_filename}.mp3"
            print(f"[AUDIO URL] {_play_url}")
            response.play(_play_url)
        else:
            print("[TTS FALLBACK] ElevenLabs failed — using Twilio voice instead.")
            if language == "ar":
                response.say(chat_response, voice='Polly.Hala-Neural', language='ar-AE')
            else:
                response.say(chat_response, voice='Polly.Joanna-Generative')

        if 'goodbye' in user_speech.lower():
            # If the user says "goodbye," end the call
            response.say("Thank you for using us. Goodbye!")
            response.hangup()

        gather = Gather(input='speech', action=f'https://{ngrok_url}/handle_speech', timeout=10, speechTimeout='auto')
        response.append(gather)

    return str(response)

@app.route('/handle_speech1', methods=['POST','GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def handle_speech1():
    request_body = request.values
    response = VoiceResponse()
    if 'SpeechResult' in request_body:
        user_speech = request_body['SpeechResult']
        user_phone = request_body.get('From')
        language = get_user_language(user_phone)
        # Use the agent version so it can call check_shop_availability / save_lead / save_complaint
        _t0 = datetime.now()
        chat_response = get_chatbot_response_agent(user_speech, user_phone)
        print(f"[TIMING] LLM response took {(datetime.now() - _t0).total_seconds():.2f}s")

        # Speak the response using ElevenLabs (premium voice quality).
        # If ElevenLabs fails for any reason, automatically fall back to
        # Twilio's built-in voice so the call is never silent.
        _t1 = datetime.now()
        audio_filename = synthesize_speech(chat_response, f"response_{datetime.now().timestamp()}", language=language)
        print(f"[TIMING] TTS took {(datetime.now() - _t1).total_seconds():.2f}s")
        print(f"[TIMING] TOTAL so far: {(datetime.now() - _t0).total_seconds():.2f}s")
        if audio_filename:
            _play_url = f"https://{ngrok_url}/static/{audio_filename}.mp3"
            print(f"[AUDIO URL] {_play_url}")
            response.play(_play_url)
        else:
            print("[TTS FALLBACK] ElevenLabs failed — using Twilio voice instead.")
            if language == "ar":
                response.say(chat_response, voice='Polly.Hala-Neural', language='ar-AE')
            else:
                response.say(chat_response, voice='Polly.Joanna-Generative')

        if 'goodbye' in user_speech.lower():
            # If the user says "goodbye," end the call
            response.say("Thank you for using us. Goodbye!")
            response.hangup()

        gather = Gather(input='speech', action=f'https://{ngrok_url}/handle_speech1', timeout=10, speechTimeout='auto')
        response.append(gather)

    return str(response)

@app.route('/browser_test', methods=['GET'])
def browser_test():
    """
    A simple in-browser test page — lets you type messages and hear the AI's
    real ElevenLabs voice reply, using the exact same chatbot + TTS pipeline
    as real calls. No Twilio, no phone number, no tunnel needed — just run
    the app locally and open http://localhost:5000/browser_test
    """
    return """
<!DOCTYPE html>
<html>
<head>
  <title>A5 Mall Assistant - Browser Test</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; }
    #chat { border: 1px solid #ccc; border-radius: 8px; padding: 15px; min-height: 300px; margin-bottom: 15px; overflow-y: auto; max-height: 500px; }
    .msg { margin-bottom: 12px; }
    .you { color: #1a73e8; font-weight: bold; }
    .bot { color: #188038; font-weight: bold; }
    input, select, button { font-size: 15px; padding: 8px; }
    #textInput { width: 60%; }
    #status { color: #999; font-size: 13px; margin-top: 8px; }
  </style>
</head>
<body>
  <h2>A5 Mall AI Assistant — Browser Test (no phone needed)</h2>
  <p>Language: <select id="lang"><option value="en">English</option><option value="ar">Arabic</option></select></p>
  <div id="chat"></div>
  <input id="textInput" type="text" placeholder="Type your message..." onkeydown="if(event.key==='Enter') send()">
  <button onclick="send()">Send</button>
  <div id="status"></div>

  <script>
    const chat = document.getElementById('chat');
    const status = document.getElementById('status');

    function addMsg(who, text) {
      const div = document.createElement('div');
      div.className = 'msg';
      div.innerHTML = '<span class="' + (who === 'You' ? 'you' : 'bot') + '">' + who + ':</span> ' + text;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    async function send() {
      const input = document.getElementById('textInput');
      const message = input.value.trim();
      if (!message) return;
      const language = document.getElementById('lang').value;
      addMsg('You', message);
      input.value = '';
      status.textContent = 'Thinking...';

      try {
        const res = await fetch('/browser_test_chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, language })
        });
        const data = await res.json();
        status.textContent = '';
        if (data.error) {
          addMsg('Assistant', '(error: ' + data.error + ')');
          return;
        }
        addMsg('Assistant', data.reply);
        if (data.audio_url) {
          const audio = new Audio(data.audio_url);
          audio.play();
        }
      } catch (e) {
        status.textContent = '';
        addMsg('Assistant', '(request failed: ' + e + ')');
      }
    }
  </script>
</body>
</html>
"""


@app.route('/browser_test_chat', methods=['POST'])
def browser_test_chat():
    """
    Backend for /browser_test. Runs the exact same chatbot + TTS pipeline as
    a real call, but returns a same-origin static file path (not the ngrok/
    tunnel URL), since this is meant to be opened directly in a local
    browser at http://localhost:5000/browser_test.
    """
    data = request.get_json(force=True) or {}
    message = (data.get('message') or '').strip()
    language = data.get('language') or 'en'
    test_phone = "+96500000099"  # fixed dummy "caller" for browser testing

    if not message:
        return jsonify({"error": "message is required"}), 400

    set_user_language(test_phone, language)

    try:
        chat_response = get_chatbot_response_agent(message, test_phone)
    except Exception as e:
        return jsonify({"error": f"chatbot error: {e}"}), 500

    audio_url = None
    try:
        audio_filename = synthesize_speech(chat_response, f"browsertest_{datetime.now().timestamp()}", language=language)
        if audio_filename:
            audio_url = f"/static/{audio_filename}.mp3"
    except Exception as e:
        print(f"[BROWSER TEST TTS ERROR] {e}")

    return jsonify({"reply": chat_response, "audio_url": audio_url})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True, use_reloader=False)
