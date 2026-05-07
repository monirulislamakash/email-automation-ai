import json
import os
from threading import Thread
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
import requests
from src.ai.reply_agent import call_reply_agent
from src.database.services.lead_services import update_lead, get_leads_by_campaign
from src.database.services.notification_services import get_all_notifications, add_notification
from src.email.accounts_manager import get_email_accounts
from src.site.socket import socketio
from src.site.routers.auth import token_required


webhook = Blueprint("webhook", __name__)


class Bot:
    def __init__(self):
        API_KEY = "8262260235:AAGwKrxwVc9YtdxR4vySAX6JwUOZ_JK9S_A"
        self.ROOT_URL = "https://api.telegram.org/bot" + API_KEY
        self.chat_id = "-1002627769853"

    def send_message(self, message: str) -> dict:
        send_message = self.ROOT_URL + "/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        response = requests.post(send_message, json=payload)
        return response.json()


bot = Bot()
connected_clients = []


@socketio.on("connect")
def handle_connect():
    connected_clients.append(request.sid)
    print(f"Client connected. Total clients: {len(connected_clients)}")


# @socketio.on("disconnect")
# def handle_disconnect():
#     if request.sid in connected_clients:
#         connected_clients.remove(request.sid)
#     print(f"Client disconnected. Total clients: {len(connected_clients)}")


def send_to_all_clients(event_type: str, message: dict, data: dict = None):
    message = {
        "event_type": event_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "test_data": data,
    }

    socketio.emit("webhook_event", message, skip_sid=True)


def handle_reply_generation(campaign_id: str, email_id: str, client_reply: str, thread_id: str):
    try:
        estimated_human_time, reply_mail = call_reply_agent(client_reply=client_reply, thread_id=thread_id)
        next_reply_date = datetime.now() + timedelta(minutes=int(estimated_human_time))
        lead_id = get_leads_by_campaign(campaign_id).lead_id
        update_lead(lead_id=lead_id, email_id=email_id, next_reply_date=next_reply_date, reply_mail=reply_mail)
        send_to_all_clients("reply generated", f"Reply Generated | Reply mail: {reply_mail}", {})
    except Exception as e:
        print(e)


@webhook.post("/instantly-webhook")
def instantly_webhook():
    data = request.json
    if data:
        print("Webhook received:", data)

        event_type = data["event_type"]
        campaign_id = data["campaign_id"]
        campaign_name = data["campaign_name"]
        lead_name = data["firstName"] + " " + data["lastName"]
        lead_email = data["lead_email"]
        email_account = data["email_account"]
        timestamp = data["timestamp"]

        try:
            add_notification(data)
        except Exception as e:
            print("Failed to store notification data on database.", e)

        if event_type == "email_sent":
            print("📤 Email Sent Successfully ✅")
            send_to_all_clients(event_type, f"📤 Email Sent Successfully | Lead: {lead_name}", data)
            bot.send_message(str(data))

        elif event_type == "email_opened":
            print("📩 Email Opened!!! 🎉")
            send_to_all_clients(event_type, f"📩 Email Opened!!! | Lead: {lead_name}", data)
            bot.send_message(str(data))

        elif event_type == "reply_received":
            bot.send_message(str(data))
            send_to_all_clients(event_type, f"💬 New Reply Received | Lead: {lead_name}", data)
            try:
                email_id = data["email_id"]
                print(f"💬 New Reply Received 📥 | 🧾 Subject: {data.get('reply_subject')}")
                client_reply = data.get("reply_text_snippet")
                t = Thread(
                    target=handle_reply_generation,
                    args=(
                        campaign_id,
                        email_id,
                        client_reply,
                        lead_email,
                    ),
                )
                t.start()
            except Exception as e:
                print(f"Error in reply block: \n{e}")

        elif event_type == "lead_unsubscribed":
            bot.send_message(str(data))
            print("🚫 Lead Unsubscribed")

        else:
            print(f"⚠️ Unknown event type: {event_type}")
            print(str(data))
        return {"status": "ok"}

    return {"status": "None"}


@webhook.route("/api/notification/", methods=["GET"])
def notification():
    try:
        notifications = get_all_notifications()

        notifications_list = []
        for notification in notifications:
            notification_data = {
                "id": notification.id,
                "notification": notification.notification,
                "date": notification.date.isoformat() if notification.date else None,
            }
            notifications_list.append(notification_data)

        return jsonify(notifications_list), 200
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": f"Error fetching notifications: {str(e)}"}), 500


@webhook.route("/api/emails/", methods=["GET"])
@token_required
def get_emails(current_user):
    try:
        email_list = get_email_accounts()
        return jsonify(email_list), 200
    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": f"Error fetching emails: {str(e)}"}), 500


@webhook.route("/api/playground/", methods=["POST"])
@token_required
def playground(current_user):
    try:
        if request.is_json:
            get_data = request.get_json()
        else:
            get_data = request.form.to_dict() if request.form else {}

        print("Playground request data:", get_data)
        print(request.files)
        thread_id = (get_data.get("thread_id") or "").strip()
        reply_text = (get_data.get("reply_text") or "").strip()
        if not thread_id or not reply_text:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "thread_id and reply_text are required",
                        "thread_id": thread_id or None,
                        "data": None,
                    }
                ),
                400,
            )
        estimated_human_time, reply_mail = call_reply_agent(client_reply=reply_text, thread_id=thread_id)
        return (
            jsonify(
                {
                    "success": "True",
                    "message": "mail generated successfully",
                    "thread_id": thread_id,
                    "data": {"estimated_time": str(estimated_human_time), "generated_content": reply_mail},
                }
            ),
            200,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Failed to process playground request: {str(e)}",
                    "thread_id": None,
                    "data": None,
                }
            ),
            500,
        )
