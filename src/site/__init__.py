from flask import Flask, jsonify, request
from dotenv import load_dotenv
import os
from datetime import timedelta
from src.site.socket import socketio 


def create_app() -> Flask:
    load_dotenv()
    # Import routers after env vars are loaded. Some router dependencies
    # initialize LLM/vector clients at import-time and may require optional
    # external keys. Keep core CRUD routes available even when those are absent.
    from src.site.routers.auth import auth, verify_token, get_auth_token_from_request
    from src.site.routers.lead import lead
    from src.site.routers.prompt import prompt
    from src.site.routers.campaign import campaign
    from src.site.routers.api_key import api_key
    from src.database.services.user_services import get_user_by_id

    app = Flask(
        __name__,
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-alamin-secret")
    app.config["JWT_EXPIRATION_DELTA"] = timedelta(days=90)
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000")
    try:
        app.config.from_object("config.Config")
    except Exception:
        pass

    # Keep Flask SECRET_KEY aligned with JWT signing (env wins over Config).
    if os.getenv("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # JWT auth on by default; set AUTH_DISABLED=true in .env for local open API.
    app.config["AUTH_DISABLED"] = os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes", "on"}

    try:
        from src.site.routers.webhook import webhook
    except Exception as e:
        webhook = None
        print(f"Webhook router disabled: {str(e)}")

    if webhook is not None:
        app.register_blueprint(webhook)
    app.register_blueprint(auth)
    app.register_blueprint(lead)
    app.register_blueprint(prompt)
    app.register_blueprint(campaign)
    app.register_blueprint(api_key)

    @app.before_request
    def require_auth_for_app_routes():
        if app.config.get("AUTH_DISABLED"):
            return None
        # Keep authentication endpoints open; protect everything else.
        if request.method == "OPTIONS":
            return None

        open_paths = {
            "/api/auth/login",
            "/api/auth/login/",
            "/api/auth/register",
            "/api/auth/register/",
            "/instantly-webhook",
            "/instantly-webhook/",
        }
        if request.path in open_paths:
            return None

        token = get_auth_token_from_request()

        if not token:
            return jsonify({"success": False, "message": "Authentication required. Please login first."}), 401

        payload = verify_token(token)
        if not payload:
            return jsonify({"success": False, "message": "Invalid or expired token. Please login again."}), 401

        try:
            user = get_user_by_id(payload.get("user_id"))
        except Exception as db_err:
            print("require_auth_for_app_routes DB error:", db_err)
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Database temporarily unavailable. If you use Docker with SQLite, avoid many processes writing the same database file at once.",
                    }
                ),
                503,
            )

        if not user:
            return jsonify({"success": False, "message": "User not found."}), 401
        if user.status != "active":
            return jsonify({"success": False, "message": "User account is not active."}), 403

        return None

    @app.after_request
    def add_cors_headers(response):
        allowed_origins = {"http://127.0.0.1:3000", "http://localhost:3000", frontend_origin}
        request_origin = request.headers.get("Origin")
        if request_origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = request_origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Cookie"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    socketio.init_app(app)

    return app
