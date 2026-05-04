import base64
from io import BytesIO
import os
import re
import uuid
from docx import Document
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from src.site.routers.auth import token_required
from src.database.services.campaign_services import get_campaign
from src.database.services.prompt_services import (
    get_global_prompt,
    add_global_prompt,
    get_all_global_prompts,
    get_all_custom_prompts,
    update_global_prompt,
    update_global_prompt_status,
    delete_global_prompt,
    # custom prompt section
    add_custom_prompt,
    update_custom_prompt,
    change_custom_prompt_status,
    delete_custom_prompt,
)


prompt = Blueprint("prompt", __name__)


@prompt.route("/api/add/prompt/", methods=["POST"])
@token_required
def add_prompt(current_user):
    print("Adding prompt request received")
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400
        print(data)
        prompt_type = data.get("prompt_type") or data.get("prompt_name")
        file_content = data.get('file_content')
        file_name = data.get('file_name')
        file_type = data.get('file_type')
        if file_content and file_name:
            print(f"File received: {file_name} (type: {file_type})")
            # print(f"File content: {file_content[:50]}....")
            base64_str = re.sub("^data:.*;base64,", "", file_content)
            file_bytes = base64.b64decode(base64_str)
            doc = Document(BytesIO(file_bytes))
            prompt_content = "\n".join([para.text for para in doc.paragraphs])
        else:
            print("No file uploaded. Text data received.")
            prompt_content = data.get("prompt_content") or data.get("prompt_value")

        campaign_id = data.get("campaign_id")
        if campaign_id is None or campaign_id == "":
            campaign_id = ""
        else:
            campaign_id = str(campaign_id).strip()

        if not prompt_type:
            return jsonify({"message": "prompt_type or prompt_name is required"}), 400

        if not prompt_content:
            return jsonify({"message": "prompt_content or prompt_value is required"}), 400

        if not campaign_id:
            existing_global_prompt = get_global_prompt(prompt_type)
            if existing_global_prompt:
                return jsonify({"success": False, "message": f"A global prompt with the name '{prompt_type}' already exists"}), 400

            new_global_prompt = add_global_prompt(prompt_type, prompt_content)
            response_data = {
                "id": new_global_prompt.id,
                "prompt_name": new_global_prompt.prompt_name,
                "prompt_value": new_global_prompt.prompt_value,
            }

            if hasattr(new_global_prompt, "status") and new_global_prompt.status is not None:
                response_data["status"] = new_global_prompt.status

            return jsonify({"success": True, "message": "Global prompt created successfully", "data": response_data}), 201

        else:
            campaign = get_campaign(campaign_id=str(campaign_id))
            if not campaign:
                return jsonify({"success": False, "message": f"Campaign with campaign_id '{campaign_id}' does not exist"}), 404

            new_custom_prompt = add_custom_prompt(campaign_pk=campaign.id, campaign_id=str(campaign_id), prompt_name=prompt_type, prompt_value=prompt_content)
            if not new_custom_prompt:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"A custom prompt with the name '{prompt_type}' already exists for campaign_id '{campaign_id}",
                        }
                    ),
                    500,
                )

            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Custom prompt created successfully",
                        "data": {
                            "id": new_custom_prompt.id,
                            "campaign_id": new_custom_prompt.campaign_id,
                            "prompt_name": new_custom_prompt.prompt_name,
                            "prompt_value": new_custom_prompt.prompt_value,
                            "status": new_custom_prompt.status,
                        },
                    }
                ),
                201,
            )

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error adding prompt: {str(e)}"}), 500


@prompt.route("/api/prompt/list/", methods=["GET"])
@token_required
def prompt_list(current_user):
    try:
        all_prompts_list = []
        all_global_prompts = get_all_global_prompts()
        for prompt in all_global_prompts:
            prompt_data = {
                "id": prompt.id,
                "prompt_name": prompt.prompt_name,
                "prompt_value": prompt.prompt_value,
                "prompt_type": prompt.prompt_name,
                "campaign_id": "",
                "status": getattr(prompt, "status", "inactive"),
            }

            all_prompts_list.append(prompt_data)

        all_custom_prompts = get_all_custom_prompts()
        for prompt in all_custom_prompts:
            prompt_data = {
                "id": prompt.id,
                "prompt_name": prompt.prompt_name,
                "prompt_value": prompt.prompt_value,
                "prompt_type": prompt.prompt_name,
                "campaign_id": prompt.campaign_id,
                "status": getattr(prompt, "status", "active"),
            }

            all_prompts_list.append(prompt_data)

        total_count = len(all_prompts_list)
        return jsonify({"success": True, "count": total_count, "data": all_prompts_list}), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Error fetching prompts: {str(e)}"}), 500


@prompt.route("/api/prompt/update/", methods=["PUT"])
@token_required
def prompt_update(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Missing JSON data"}), 400
        print(data)
        prompt_type = data.get("prompt_type") or data.get("prompt_name")
        if "file_content" in data.keys():
            file_content = data["file_content"]
            print("Received prompt as file: ", data["file_name"])
            base64_str = re.sub("^data:.*;base64,", "", file_content)
            file_bytes = base64.b64decode(base64_str)
            doc = Document(BytesIO(file_bytes))
            prompt_content = "\n".join([para.text for para in doc.paragraphs])
        else:
            prompt_content = data.get("prompt_content") or data.get("prompt_value")

        campaign_id = data.get("campaign_id")
        if campaign_id is None or campaign_id == "":
            campaign_id = ""
        else:
            campaign_id = str(campaign_id).strip()

        if not prompt_type:
            return jsonify({"success": False, "message": "prompt_type or prompt_name is required"}), 400

        if not prompt_content:
            return jsonify({"success": False, "message": "prompt_content or prompt_value is required"}), 400

        if not campaign_id:
            prompt_to_update = update_global_prompt(prompt_name=prompt_type, prompt_value=prompt_content)
            if not prompt_to_update:
                return jsonify({"success": False, "message": f"Global prompt with name '{prompt_type}' not found"}), 404

            if "status" in data:
                new_status = data.get("status")
                prompt_to_update = update_global_prompt_status(prompt_name=prompt_type, status=new_status)

            response_data = {
                "id": prompt_to_update.id,
                "prompt_name": prompt_to_update.prompt_name,
                "prompt_value": prompt_to_update.prompt_value,
            }

            if hasattr(prompt_to_update, "status") and prompt_to_update.status is not None:
                response_data["status"] = prompt_to_update.status

            return jsonify({"success": True, "message": "Global prompt updated successfully", "data": response_data}), 200

        else:
            campaign = get_campaign(campaign_id=str(campaign_id))
            if not campaign:
                return jsonify({"success": False, "message": f"Campaign with campaign_id '{campaign_id}' does not exist"}), 404

            prompt_to_update = update_custom_prompt(campaign_id=str(campaign_id), prompt_name=prompt_type, prompt_value=prompt_content)
            if not prompt_to_update:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"A custom prompt with the name '{prompt_type}' already exists for campaign_id '{campaign_id}'",
                        }
                    ),
                    400,
                )

            if "status" in data:
                prompt_to_update = change_custom_prompt_status(
                    campaign_id=str(campaign_id), prompt_name=prompt_type, status=data.get("status")
                )

            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Custom prompt updated successfully",
                        "data": {
                            "id": prompt_to_update.id,
                            "campaign_id": prompt_to_update.campaign_id,
                            "prompt_name": prompt_to_update.prompt_name,
                            "prompt_value": prompt_to_update.prompt_value,
                            "status": prompt_to_update.status,
                        },
                    }
                ),
                200,
            )

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error updating prompt: {str(e)}"}), 500


@prompt.route("/api/prompt/delete/", methods=["DELETE"])
@token_required
def prompt_delete(current_user):
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Missing JSON data"}), 400
        print(data)
        prompt_id = data.get("id")

        campaign_id = data.get("campaign_id")
        if campaign_id is None or campaign_id == "":
            campaign_id = ""
        else:
            campaign_id = str(campaign_id).strip()

        if not prompt_id:
            return jsonify({"success": False, "message": "id is required to delete a prompt"}), 400

        if not campaign_id:
            prompt_to_delete = delete_global_prompt(prompt_name=data.get("prompt_name"))
            if not prompt_to_delete:
                return jsonify({"success": False, "message": f"Global prompt with name '{data.get('prompt_name')}' not found"}), 404

            return (
                jsonify(
                    {"success": True, "message": f"Global prompt '{data.get('prompt_name')}' (id: {prompt_id}) deleted successfully"}
                ),
                200,
            )

        else:
            campaign = get_campaign(campaign_id=str(campaign_id))
            if not campaign:
                return jsonify({"success": False, "message": f"Campaign with campaign_id '{campaign_id}' does not exist"}), 404

            prompt_to_delete = delete_custom_prompt(campaign_id=str(campaign_id), prompt_name=data.get("prompt_name"))
            if not prompt_to_delete:
                return jsonify({"success": False, "message": f"Custom prompt with id '{prompt_id}' not found"}), 404

            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Custom prompt '{data.get('prompt_name')}' (id: {prompt_id}) from campaign \
'{campaign_id}' deleted successfully",
                    }
                ),
                200,
            )

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error deleting prompt: {str(e)}"}), 500
