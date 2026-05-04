import os
import re
import time
import jwt
from functools import wraps
from datetime import timedelta
from flask import Blueprint, jsonify, request, current_app
from types import SimpleNamespace
from werkzeug.security import generate_password_hash, check_password_hash
from src.database.services.user_services import (
    add_user,
    delete_user_by_id,
    get_user_by_id,
    get_user_by_username,
    list_users_public_payload,
    update_user_profile,
)


auth = Blueprint("auth", __name__)
JWT_EXPIRATION_DELTA = timedelta(days=90)

_BEARER_HEADER_RE = re.compile(r"^\s*Bearer\s+(\S+)", re.IGNORECASE)


def _jwt_secret():
    """Prefer SECRET_KEY from env so sign/verify match even if Config changes app.config."""
    env = os.getenv("SECRET_KEY")
    if env:
        return env
    try:
        cfg = current_app.config.get("SECRET_KEY")
        if cfg:
            return str(cfg)
    except RuntimeError:
        pass
    return "dev-alamin-secret"


def extract_bearer_token(header_value):
    """Parse Authorization header; avoids split(' ') breaking on 'Bearer  <jwt>' or extra spaces."""
    if header_value is None:
        return _normalize_jwt_string(None)
    raw = str(header_value).strip()
    m = _BEARER_HEADER_RE.match(raw)
    if m:
        return _normalize_jwt_string(m.group(1))
    return _normalize_jwt_string(raw)


def _normalize_jwt_string(raw):
    if raw is None:
        return None
    text = str(raw).strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()
    return text or None


# Cookie names used by the Next.js app when the browser does not send Authorization to Flask.
_AUTH_COOKIE_NAMES = ("email_automation_token",)


def get_auth_token_from_request():
    """Prefer Authorization Bearer; fall back to auth cookies (BFF / same-site proxy)."""
    auth_hdr = request.headers.get("Authorization")
    if auth_hdr:
        tok = extract_bearer_token(auth_hdr)
        if tok:
            return tok
    for name in _AUTH_COOKIE_NAMES:
        tok = _normalize_jwt_string(request.cookies.get(name))
        if tok:
            return tok
    return None


_PUBLIC_USER_FIELDS = (
    "id",
    "username",
    "first_name",
    "last_name",
    "email",
    "phone",
    "linkedin",
    "country",
    "language",
    "timezone",
    "role",
    "status",
)


def user_to_public_dict(user):
    """Build API user payload; supports minimal Users model or extended profile columns."""
    if user is None:
        return {}
    return {field: getattr(user, field, None) for field in _PUBLIC_USER_FIELDS}


def generate_token(user_id, username):
    try:
        now = int(time.time())
        exp = now + int(JWT_EXPIRATION_DELTA.total_seconds())
        payload = {
            "user_id": user_id,
            "username": username,
            "exp": exp,
            "iat": now,
        }

        token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token
    except Exception as e:
        print(f"Error generating token: {str(e)}")
        return None


def verify_token(token):
    text = _normalize_jwt_string(token)
    if not text:
        return None
    try:
        try:
            return jwt.decode(
                text,
                _jwt_secret(),
                algorithms=["HS256"],
                leeway=120,
                options={"verify_signature": True, "verify_iat": False},
            )
        except TypeError:
            return jwt.decode(text, _jwt_secret(), algorithms=["HS256"], leeway=120)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_disabled = current_app.config.get("AUTH_DISABLED")
        if auth_disabled is None:
            auth_disabled = os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes", "on"}
        if auth_disabled:
            # Keep route signatures compatible while bypassing auth in local/dev mode.
            guest_user = SimpleNamespace(
                id=None,
                username="guest",
                first_name="Guest",
                last_name="User",
                email=None,
                phone=None,
                linkedin=None,
                country=None,
                language=None,
                timezone=None,
                role="guest",
                status="active",
            )
            return f(guest_user, *args, **kwargs)

        token = get_auth_token_from_request()
        if not token:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Token is missing. Send Authorization: Bearer <token> or the session cookie.",
                    }
                ),
                401,
            )

        payload = verify_token(token)
        if not payload:
            return jsonify({"success": False, "message": "Token is invalid or expired. Please login again."}), 401

        try:
            current_user = get_user_by_id(payload["user_id"])
        except Exception as db_err:
            print("token_required DB error:", db_err)
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Database temporarily unavailable. Retry shortly, or reduce concurrent access to the SQLite file.",
                    }
                ),
                503,
            )

        if not current_user:
            return jsonify({"success": False, "message": "User not found."}), 401

        if current_user.status != "active":
            return jsonify({"success": False, "message": "User account is not active. Please contact administrator."}), 403

        return f(current_user, *args, **kwargs)

    return decorated


@auth.route("/api/auth/register/", methods=["POST"])
def register():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Missing JSON data"}), 400

        username = data.get("username")
        password = data.get("password")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")

        if not username:
            return jsonify({"success": False, "message": "username is required"}), 400

        if not password:
            return jsonify({"success": False, "message": "password is required"}), 400

        if not first_name:
            return jsonify({"success": False, "message": "first_name is required"}), 400

        if not last_name:
            return jsonify({"success": False, "message": "last_name is required"}), 400

        existing_user = get_user_by_username(username=username)
        if existing_user:
            return (
                jsonify({"success": False, "message": f"Username '{username}' already exists. Please choose a different username."}),
                400,
            )

        hashed_password = generate_password_hash(password)

        add_user(first_name=first_name, last_name=last_name, username=username, email=email, password=hashed_password)
        new_user = get_user_by_username(username=username)
        print(new_user.id, new_user.username)
        token = generate_token(new_user.id, new_user.username)

        reg_payload = user_to_public_dict(new_user)
        if reg_payload.get("email") is None and email:
            reg_payload["email"] = email

        return (
            jsonify(
                {
                    "success": True,
                    "message": "User registered successfully",
                    "data": reg_payload,
                    "token": token,
                }
            ),
            201,
        )

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error registering user: {str(e)}"}), 500


@auth.route("/api/auth/user-list/", methods=["GET"])
@token_required
def list_users_api(current_user):
    """List all users (same payload shape as other list APIs)."""
    try:
        data = list_users_public_payload()
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error listing users: {str(e)}"}), 500


@auth.route("/api/auth/users/", methods=["POST"])
@token_required
def users_collection(current_user):
    """Create another user account while authenticated (does not issue a token for the new user)."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Missing JSON data"}), 400

        username = data.get("username")
        password = data.get("password")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        status = data.get("status") or "active"

        if not username:
            return jsonify({"success": False, "message": "username is required"}), 400
        if not password:
            return jsonify({"success": False, "message": "password is required"}), 400
        if not first_name:
            return jsonify({"success": False, "message": "first_name is required"}), 400
        if not last_name:
            return jsonify({"success": False, "message": "last_name is required"}), 400

        if status not in {"active", "inactive"}:
            return jsonify({"success": False, "message": "status must be 'active' or 'inactive'"}), 400

        existing_user = get_user_by_username(username=username)
        if existing_user:
            return (
                jsonify({"success": False, "message": f"Username '{username}' already exists."}),
                400,
            )

        hashed_password = generate_password_hash(password)
        created = add_user(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password=hashed_password,
            status=status,
        )
        if not created:
            return jsonify({"success": False, "message": "Could not create user (username may already exist)."}), 400

        new_user = get_user_by_username(username=username)
        if not new_user:
            return jsonify({"success": False, "message": "User was created but could not be loaded."}), 500

        return (
            jsonify(
                {
                    "success": True,
                    "message": "User created successfully",
                    "data": user_to_public_dict(new_user),
                }
            ),
            201,
        )
    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error creating user: {str(e)}"}), 500


@auth.route("/api/auth/users/<int:user_id>/", methods=["DELETE"])
@token_required
def delete_user_api(current_user, user_id):
    try:
        if current_user.id is not None and int(current_user.id) == int(user_id):
            return jsonify({"success": False, "message": "You cannot delete your own account."}), 400

        target = get_user_by_id(user_id)
        if not target:
            return jsonify({"success": False, "message": "User not found."}), 404

        if not delete_user_by_id(user_id):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Could not delete user. The account may be referenced elsewhere or already removed.",
                    }
                ),
                400,
            )

        return jsonify({"success": True, "message": "User deleted successfully."}), 200
    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error deleting user: {str(e)}"}), 500


@auth.route("/api/auth/login/", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Missing JSON data"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username:
            return jsonify({"success": False, "message": "username is required"}), 400

        if not password:
            return jsonify({"success": False, "message": "password is required"}), 400

        user = get_user_by_username(username=username)

        if not user:
            return jsonify({"success": False, "message": "Invalid username or password"}), 401

        if not check_password_hash(user.password, password):
            return jsonify({"success": False, "message": "Invalid username or password"}), 401

        if user.status != "active":
            return jsonify({"success": False, "message": "User account is not active. Please contact administrator."}), 403

        token = generate_token(user.id, user.username)

        if not token:
            return jsonify({"success": False, "message": "Error generating token. Please try again."}), 500

        login_payload = user_to_public_dict(user)
        if login_payload.get("email") is None and user.username and "@" in str(user.username):
            login_payload["email"] = user.username

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Login successful",
                    "data": login_payload,
                    "token": token,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"Error during login: {str(e)}"}), 500


@auth.route("/api/auth/me/", methods=["GET"])
@token_required
def get_current_user(current_user):
    try:
        return jsonify({"success": True, "data": user_to_public_dict(current_user)}), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching user data: {str(e)}"}), 500


@auth.route("/api/auth/me/", methods=["PUT"])
@token_required
def update_current_user(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Missing JSON data"}), 400

        updated_user = update_user_profile(
            user_id=current_user.id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            linkedin=data.get("linkedin"),
            country=data.get("country"),
            language=data.get("language"),
            timezone=data.get("timezone"),
            role=data.get("role"),
        )
        if not updated_user:
            return jsonify({"success": False, "message": "Failed to update user profile"}), 400

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Profile updated successfully",
                    "data": user_to_public_dict(updated_user),
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating user data: {str(e)}"}), 500


@auth.route("/api/auth/verify-token/", methods=["POST"])
@token_required
def verify_token_endpoint(current_user):
    try:
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Token is valid",
                    "data": user_to_public_dict(current_user),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"success": False, "message": f"Error verifying token: {str(e)}"}), 500


@auth.route("/")
@token_required
def index(current_user):
    return jsonify({"success": True, "message": "Welcome to the API"}), 200
