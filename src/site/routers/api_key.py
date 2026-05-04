import json
from flask import Blueprint, jsonify, request
from src.site.routers.auth import token_required
from src.database.services.credential_services import add_credential, get_cred_by_name, update_credential, get_all_cred

api_key = Blueprint("api_key", __name__)


@api_key.route("/api/api-key-config/", methods=["POST"])
@token_required
def key_config(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400

        print(f"API Key Config called with data: {data}")
        key_id = data.get("keyId")
        key_value = data.get("key")
        if not key_id:
            return jsonify({"success": False, "message": "keyId is required. Please provide a name for the credential."}), 400

        if not key_value:
            return jsonify({"success": False, "message": "key is required. Please provide a value for the credential."}), 400

        if get_cred_by_name(key_id):
            update_credential(key_id, key_value)
        else:
            add_credential(key_id, key_value)
        return jsonify(data), 200
    except Exception as e:
        print(f"Error in API Key Config: {str(e)}")
        return jsonify({"message": f"Invalid request format: {str(e)}"}), 400


@api_key.route("/api/api-key-config/view/", methods=["GET"])
@token_required
def key_config_view(current_user):
    try:
        credentials = get_all_cred()
        if not credentials:
            return jsonify({"success": False, "message": "No credentials found"}), 404

        credentials_list = []
        for cred in credentials:
            credentials_list.append({"keyId": cred.name, "key": cred.value})

        return jsonify(credentials_list), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Error fetching credentials: {str(e)}"}), 500
