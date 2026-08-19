"""
Entry point required by cPanel's "Setup Python App" (Passenger/WSGI) hosting.
cPanel looks for a module-level variable called `application` here — it does
NOT run app.run() directly like a normal local Python script.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application
