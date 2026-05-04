from src.database.session import get_session
from src.database.models.users import Users
from sqlalchemy.exc import IntegrityError

# Keep aligned with `auth._PUBLIC_USER_FIELDS` for API list payloads.
_USER_PUBLIC_KEYS = (
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


def list_users_public_payload():
    with get_session() as session:
        rows = session.query(Users).order_by(Users.id.asc()).all()
        return [{key: getattr(row, key, None) for key in _USER_PUBLIC_KEYS} for row in rows]


def delete_user_by_id(user_id: int) -> bool:
    with get_session() as session:
        user = session.query(Users).filter_by(id=user_id).first()
        if not user:
            return False
        try:
            session.delete(user)
            session.commit()
            return True
        except IntegrityError as e:
            session.rollback()
            print("delete_user_by_id:", e)
            return False
        except Exception as e:
            session.rollback()
            print("delete_user_by_id:", e)
            return False


def add_user(first_name: str, last_name: str, username: str, password: str, email: str = None, status: str = "active") -> bool:
    with get_session() as session:
        existing = session.query(Users).filter_by(username=username).first()
        if existing:
            print(f"User '{username}' already exists.")
            return False

        user_kwargs = {
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "password": password,
            "status": status or "active",
        }
        if email is not None and hasattr(Users, "email"):
            user_kwargs["email"] = email
        user = Users(**user_kwargs)
        try:
            session.add(user)
            session.commit()
            print(f"User '{username}' added successfully.")
            return user
        except IntegrityError as e:
            session.rollback()
            print("Error:", e)
            return False


def get_user_by_id(user_id):
    with get_session() as session:
        user = session.query(Users).filter_by(id=user_id).first()
        return user or None


def get_user_by_username(username):
    with get_session() as session:
        user = session.query(Users).filter_by(username=username).first()
        print(user)
        return user or None


def update_user_profile(
    user_id,
    first_name=None,
    last_name=None,
    email=None,
    phone=None,
    linkedin=None,
    country=None,
    language=None,
    timezone=None,
    role=None,
):
    with get_session() as session:
        user = session.query(Users).filter_by(id=user_id).first()
        if not user:
            return None

        updates = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "country": country,
            "language": language,
            "timezone": timezone,
            "role": role,
        }

        for field, value in updates.items():
            if value is not None and hasattr(user, field):
                setattr(user, field, value)

        try:
            session.commit()
            session.refresh(user)
            return user
        except Exception as e:
            session.rollback()
            print("Error:", e)
            return None
