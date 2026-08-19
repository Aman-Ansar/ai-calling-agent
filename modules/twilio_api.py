from twilio.twiml.voice_response import VoiceResponse, Gather
from .mongodb import has_interacted_before
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from twilio.rest import Client
from config import TWILIO_PHONE_NUMBER,NGROK_URL
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
from flask import Flask, request, url_for
ngrok_url = NGROK_URL
import os
# static_dir = os.path.join(os.getcwd(), './static')

def handle_incoming_call(request_body):
    response = VoiceResponse()

    # Ask for language choice FIRST, before anything else.
    # 1 = Arabic, 2 = English (spoken or key press, either works)
    _action_url = f'https://{ngrok_url}/select_language'
    print(f"[VOICE ACTION URL] {_action_url}")
    gather = Gather(input='dtmf speech', numDigits=1, timeout=8, speechTimeout='auto',
                     action=_action_url)
    gather.say("Welcome to A5 Mall. For Arabic, say or press 1. For English, say or press 2.",
                voice='Polly.Joanna-Generative')
    gather.say("مرحباً بكم في مجمع A5. للغة العربية قولوا أو اضغطوا 1، وللغة الإنجليزية قولوا أو اضغطوا 2.",
                voice='Polly.Hala-Neural', language="ar-AE")
    response.append(gather)
    return str(response)

def initiate_call(phone_number):
    to_number = phone_number

    stat_url=url_for('static', filename=f'response.mp3', _external=True)
    # Initiate the call with correct TwiML
    call = twilio_client.calls.create(
        twiml=f'<Response><Play>https://{ngrok_url}/static/response.mp3</Play><Gather action="https://{ngrok_url}/handle_speech" input="speech" timeout="10" speechTimeout="auto"></Gather></Response>',
        to=to_number,
        from_=TWILIO_PHONE_NUMBER
    )

    return "Call initiated."



