import os
import sys
from app import app
from src.site.socket import socketio

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)
