from src.site import create_app
from flask import request
import logging
import os
from colorama import Fore, init

init(autoreset=True)

app = create_app()


# ----------------------------------------
# REQUEST LOGGER
# ----------------------------------------
@app.before_request
def log_request_info():
    print("\n" + Fore.CYAN + "====== NEW REQUEST ======" + Fore.RESET)
    print(
        Fore.YELLOW + "URL:" + Fore.RESET,
        Fore.GREEN + request.method + Fore.RESET,
        request.url,
    )


# ----------------------------------------
# RESPONSE LOGGER
# ----------------------------------------
@app.after_request
def log_response_info(response):
    print("RESPONSE Status:", Fore.YELLOW + str(response.status) + Fore.RESET)
    print(Fore.MAGENTA + "----------------------\n" + Fore.RESET)
    return response


if __name__ == "__main__":
    from src.site.socket import socketio
    use_reloader = os.getenv("USE_RELOADER", "false").lower() == "true"
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    socketio.run(app, host="0.0.0.0", port=8000, debug=debug_mode, use_reloader=use_reloader)
