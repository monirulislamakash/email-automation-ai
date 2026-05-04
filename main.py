import time
from threading import Thread
from datetime import date, datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from src.scrapers.website_scraper import scrape_website_data
from src.scrapers.linkedin_scraper import get_linkedin_data

from src.ai.content_generator_agent import generate_content
from src.ai.prompts.user_prompts import email_generation_prompt
from src.ai.reply_agent import call_reply_agent
from src.ai.prompts.user_prompts import (
    followup1_email_generation_prompt,
    followup2_email_generation_prompt,
    followup3_email_generation_prompt,
)

from src.email.campaign_manager import get_campaign, update_campaign, activate_campaign, create_campaign, delete_campaign
from src.email.lead_manager import get_lead_info, create_lead
from src.email.emails_manager import send_reply

from src.database.models.leads import Leads
from src.database.services.lead_services import get_all_leads, update_lead, get_lead_by_lead_id, update_lead_null, change_lead_id
from src.database.services.campaign_services import get_campaign as get_db_campaign, change_campaign_id, get_campaign_db_id
from src.database.services.campaign_services import (
    get_campaign_senders,
    update_db_campaign,
    get_campaign_leads,
    update_db_campaign_status,
)

from src.utils.logger import write_campaign_log, write_agent_log

FOLLOW_UP_MAP = {
    "Fresh": 3,  # Send follow up 1 after 3 days on Fresh mail sent
    "Follow Up 1": 6,
    "Follow Up 2": 10,
    "Follow Up 3": 99,
}


def send_reply_mail(lead_id: str, send_email_account: str):
    """check and send reply mail"""
    lead = get_lead_by_lead_id(lead_id)
    lead_id = lead.lead_id
    email_id = lead.email_id
    next_reply_datetime = lead.next_reply_date
    reply_mail = lead.reply_mail
    if next_reply_datetime:
        if next_reply_datetime <= datetime.now():
            print("Next reply due!")
            response = send_reply(sender_email=send_email_account, reply_uuid=email_id, body={"html": reply_mail})
            if response.get("id"):
                print(f"AI Reply Sent With Mail Body: \n{reply_mail}")
                if not update_lead_null(lead_id=lead_id):
                    write_campaign_log(campaign_id=lead.campaign_pk, message=f"Failed to update lead {lead_id}")

            else:
                print("Failed to send reply mail.")
                write_campaign_log(campaign_id=lead.campaign_pk, message=f"Failed to send reply mail. Response: {str(response)}")
        else:
            print("Not yet to send reply mail.")
    else:
        print("No reply schedule found")


def save_init_mail(full_name: str, company: str, title: str, lead_email: str, generated_mail: str):
    message = f"""
    This is an initial message. We are ray advertising. We just sent this below mail to this client. 
    Just remember the information in your memory. No, Need to generate any reply message now.

    Details:
    -------------------------------
    client name: {full_name}
    client email: {lead_email}
    client company: {company}
    client title: {title}

    Fresh Email we just sent: 
    ------------------------
    {generated_mail}"""
    try:
        call_reply_agent(client_reply=message, thread_id=lead_email)
    except Exception as e:
        print(e)
        write_agent_log(message=f"Failed generate reply mail. Error: {str(e)}")


def get_next_follow_up_type(campaign_type: str):
    if campaign_type == "Fresh":
        return "Follow Up 1"
    elif campaign_type == "Follow Up 1":
        return "Follow Up 2"
    elif campaign_type == "Follow Up 2":
        return "Follow Up 3"
    else:
        return "Fresh"


def get_follow_up_prompt(lead: Leads, next_follow_up: str, db_campaign_id: int):
    if next_follow_up == "Follow Up 1":
        return followup1_email_generation_prompt(
            first_name=lead.first_name,
            last_name=lead.last_name,
            conference=lead.conference,
            company=lead.company,
            title=lead.title,
            client_type=lead.type,
            website_data=lead.website_data,
            linkedin_data=lead.linkedin_data,
            previous_mail=lead.generated_mail,
            id=db_campaign_id,
        )
    elif next_follow_up == "Follow Up 2":
        return followup2_email_generation_prompt(
            first_name=lead.first_name,
            last_name=lead.last_name,
            conference=lead.conference,
            company=lead.company,
            title=lead.title,
            client_type=lead.type,
            website_data=lead.website_data,
            linkedin_data=lead.linkedin_data,
            previous_mail=lead.generated_mail,
            id=db_campaign_id,
        )
    elif next_follow_up == "Follow Up 3":
        return followup3_email_generation_prompt(
            first_name=lead.first_name,
            last_name=lead.last_name,
            conference=lead.conference,
            company=lead.company,
            title=lead.title,
            client_type=lead.type,
            website_data=lead.website_data,
            linkedin_data=lead.linkedin_data,
            previous_mail=lead.generated_mail,
            id=db_campaign_id,
        )


def handle_follow_up(campaign_db_id, lead_id):
    db_campaign = get_campaign_db_id(campaign_db_id)
    db_lead = get_lead_by_lead_id(lead_id)
    campaign_type = db_lead.campaign_type
    no_respond_threshold = FOLLOW_UP_MAP[campaign_type.strip()]
    next_follow_up = get_next_follow_up_type(campaign_type)

    if db_lead.lead_processed_date:
        days_passed = (date.today() - db_lead.lead_processed_date).days
        if days_passed >= no_respond_threshold:
            print("[+] Threshold Respond Days Over. Sending Next Follow Up Mail....")
            prompt = get_follow_up_prompt(lead=db_lead, next_follow_up=next_follow_up, db_campaign_id=campaign_db_id)
            re_generated_mail = generate_content(prompt)

            delete_campaign(db_lead.campaign_id)
            # create new campaign for follow up
            campaign_response = create_campaign(
                campaign_name=db_campaign.campaign_name + " - " + next_follow_up,
                schedules=db_campaign.campaign_schedule,
                options_settings=db_campaign.options_settings,
            )
            new_campaign_id = campaign_response.get("id", None)
            if new_campaign_id:
                print("New follow up campaign created: ", new_campaign_id)
                try:
                    subj = re_generated_mail.split("=====")[0].replace("Subject: ", "").strip()
                except Exception as e:
                    print("Error: in getting email subject data", e)
                    subj = "Greeting"
                try:
                    mail_body = re_generated_mail.split("=====")[1].strip()
                except Exception as e:
                    print("Error: in getting email body data", e)
                    mail_body = ""
                campaign_response2 = update_campaign(
                    campaign_db_id=campaign_db_id, campaign_id=new_campaign_id, subject=subj, body=str(mail_body)
                )
                body = campaign_response2["sequences"][0]["steps"][0]["variants"][0]["body"]
                if body.strip() != "":
                    print("New mail updated to the follow up campaign")

                    # create lead under that follow up campaign
                    lead_response = create_lead(
                        campaign_id=new_campaign_id,
                        lead_email=db_lead.email,
                        first_name=db_lead.first_name,
                        last_name=db_lead.last_name,
                    )
                    new_lead_id = lead_response.get("id", None)
                    if new_lead_id:
                        change_lead_id(id=db_lead.id, new_lead_id=new_lead_id, new_campaign_id=new_campaign_id)
                        activate_campaign(campaign_id=new_campaign_id)
                        # cam: cam_id, cam_status, cam_type
                        # lead: generated_mail, campaign_id, lead_id, lead_status
                        update_db_campaign(campaign_id=db_campaign.campaign_id, campaign_status=1)
                        update_lead(lead_id=new_lead_id, generated_mail=re_generated_mail, lead_status=1, campaign_type=next_follow_up)
                        print("Follow up successfully set!!!")


def update_campaign_status(campaign_db_id: int):
    """Check all leads status under this campaign and update campaign status accordingly."""
    leads = get_campaign_leads(campaign_db_id)
    if leads is None:
        return

    campaign_completed = True
    for lead in leads:
        if lead.lead_status == 1:
            campaign_completed = False
            break
    if campaign_completed:
        update_db_campaign_status(id=campaign_db_id, status=3)
    time.sleep(2)


def main():
    leads = get_all_leads()
    print("Lead amount of current DB: ", len(leads))

    for lead in leads:
        try:
            # scrape website data
            full_name = f"{lead.first_name} {lead.last_name}"
            first_name = lead.first_name
            last_name = lead.last_name
            client_type = lead.type
            company = lead.company
            title = lead.title
            conference = lead.conference

            lead_email = lead.email
            linkedin_url = lead.linkedin
            website_url = lead.website

            campaign_id = lead.campaign_id
            lead_id = lead.lead_id
            lead_db_id = lead.id
            lead_processed_date = lead.lead_processed_date
            email_status = lead.email_status
            campaign_db_id = lead.campaign_pk

            def update_current_lead(**fields):
                """Update by external lead_id when present, otherwise fallback to DB id."""
                if lead_id:
                    return update_lead(lead_id=lead_id, **fields)
                return update_lead(db_id=lead_db_id, **fields)

            print(f"------Lead [{full_name}] Processing------")
            active_emails = get_campaign_senders(campaign_db_id)
            if not active_emails:
                print("No active emails found for campaign: ", campaign_db_id)
                write_campaign_log(campaign_id=campaign_db_id, message=f"No active emails found for campaign: {campaign_db_id}")
                continue

            website_data = lead.website_data
            # scrape website data (Crawl4AI / Playwright — often fails in Docker without Chromium in image)
            if website_data is None and website_url:
                print(f"[+] Scraping website data for {full_name} - {website_url}")
                try:
                    website_data = scrape_website_data(website_url.strip())
                    update_current_lead(website_data=website_data)
                except Exception as werr:
                    print(f"[ERROR] Website scrape failed for {full_name}: {werr}")
                    write_campaign_log(
                        campaign_id=campaign_db_id,
                        message=f"Website scrape failed for {full_name}: {str(werr)[:800]}",
                    )
                    continue

            # scrape linkedin data (Bright Data — network timeouts should not skip email generation)
            linkedin_data = lead.linkedin_data
            if linkedin_data is None and linkedin_url:
                print(f"[+] Scraping linkedin data for {full_name} - {linkedin_url}")
                try:
                    linkedin_data = get_linkedin_data(linkedin_url.strip())
                except Exception as li_err:
                    print(f"[ERROR] LinkedIn / Bright Data failed for {full_name}: {li_err}")
                    write_campaign_log(
                        campaign_id=campaign_db_id,
                        message=f"LinkedIn scrape error for {full_name}: {str(li_err)[:800]}",
                    )
                    linkedin_data = None

                if not linkedin_data:
                    print(f"No LinkedIn data returned for {full_name} - {linkedin_url}")
                    linkedin_final_data = ""
                else:
                    try:
                        profile = linkedin_data[0]
                    except (TypeError, IndexError, KeyError) as e:
                        print("Unexpected LinkedIn data format for", full_name, "-", e)
                        print("Raw linkedin_data:", str(linkedin_data)[:500])
                        linkedin_final_data = ""
                    else:
                        try:
                            activities = profile.get("activity", [])[:5]
                        except Exception:
                            activities = []
                        selected_data = {
                            "id": profile.get("id"),
                            "name": profile.get("name"),
                            "city": profile.get("city"),
                            "about": profile.get("about"),
                            "current_company": profile.get("current_company"),
                            "experience": profile.get("experience"),
                            "educations_details": profile.get("educations_details"),
                            "education": profile.get("education"),
                            "current_company_name": profile.get("current_company_name"),
                            "location": profile.get("location"),
                            "activity": activities,
                        }
                        linkedin_final_data = ""
                        for key, value in selected_data.items():
                            linkedin_final_data += f"{key}: {value}\n"
                        print("[+] Selected LinkedIn Data:\n", linkedin_final_data)
                        update_current_lead(linkedin_data=linkedin_final_data)
            else:
                linkedin_final_data = linkedin_data or ""

            # generate email
            generated_mail = lead.generated_mail
            if generated_mail is None or generated_mail == "":
                print(f"Generating email for {full_name} - {company}")
                prompt = email_generation_prompt(
                    active_emails[0],  # sender email
                    full_name,
                    first_name,
                    last_name,
                    conference,
                    company,
                    title,
                    client_type,
                    website_data,
                    linkedin_final_data,
                    campaign_db_id,
                )
                generated_mail = generate_content(prompt)
                update_current_lead(generated_mail=generated_mail)

                try:
                    subj = generated_mail.split("=====")[0].replace("Subject: ", "").strip()
                except Exception as e:
                    print("Error: in getting email subject data", e)
                    subj = "Greeting"
                try:
                    mail_body = generated_mail.split("=====")[1].strip()
                except Exception as e:
                    print("Error: in getting email body data", e)
                    mail_body = ""
                print("\n[+] Updating campaign sequence.")
                print("Subject: ", subj)
                print("Body: ", mail_body)
                update_campaign(campaign_db_id=campaign_db_id, campaign_id=lead.campaign_id, subject=subj, body=str(mail_body))

            time.sleep(1)
            campaign_response = get_campaign(lead.campaign_id)
            campaign_status = campaign_response.get("status")
            if campaign_response.get("id") and str(campaign_status) in {"0", "draft", "inactive"}:
                body = campaign_response["sequences"][0]["steps"][0]["variants"][0]["body"]
                db_campaign = get_campaign_db_id(campaign_db_id)
                if body.strip() != "" and db_campaign.campaign_status > 0:
                    activate_campaign(lead.campaign_id)
                    t = Thread(
                        target=save_init_mail,
                        args=(
                            full_name,
                            company,
                            title,
                            lead_email,
                            generated_mail,
                        ),
                    )
                    t.start()

            time.sleep(1)
            # Update lead status
            if not lead_id:
                # External lead id missing; keep local data saved and skip provider-dependent status checks.
                update_current_lead(email_status=email_status or "PROCESSING")
                update_campaign_status(campaign_db_id)
                continue

            lead_get_response = get_lead_info(lead_id=lead_id)
            lead_status = lead_get_response.get("status")
            if lead_status is None:
                print(f"Lead provider status missing for lead_id={lead_id}. Raw response: {lead_get_response}")
                update_current_lead(email_status=email_status or "PROCESSING")
                update_campaign_status(campaign_db_id)
                continue
            if str(lead_status) != "1" and lead_processed_date is None:  # lead was processed
                lead_processed_date = date.today()
                update_current_lead(lead_status=int(lead_status), lead_processed_date=lead_processed_date)

            # Check lead next action
            if str(lead_status) == "3":  # mail sent
                email_open_count = lead_get_response["email_open_count"]
                email_reply_count = lead_get_response["email_reply_count"]
                if int(float(email_open_count)) > 0:  # mail opened
                    print("[+] Mail Opened!")
                    if email_status == "Not Open Yet" or email_status is None:  # check have email opened value or not
                        update_current_lead(email_status="Email Opened")
                    if int(float(email_reply_count)) > 0:  # opened and reply
                        print("[+] Mail Replied!")
                        update_current_lead(email_status="Email Replied")
                        # check and send reply mail
                        send_reply_mail(lead_id=lead_id, send_email_account=active_emails[0])

                    else:  # open but no reply
                        print("[+] Mail Not Replied!")
                        handle_follow_up(campaign_db_id=campaign_db_id, lead_id=lead_id)

                else:  # mail not open yet
                    update_current_lead(email_status="Not Open Yet")
                    handle_follow_up(campaign_db_id=campaign_db_id, lead_id=lead_id) 

            else:  # mail not sent
                update_current_lead(email_status="NOT Yet Contacted")

            time.sleep(2)
            # update campaign status
            update_campaign_status(campaign_db_id)

            # print(f"------Lead [{full_name}] Done------")
        except Exception as e:
            print("Error with lead: ", lead.first_name, lead.last_name)
            print(e)
            write_campaign_log(
                campaign_id=lead.campaign_pk, message=f"Error with lead {lead.first_name} {lead.last_name}. Error: {str(e)}"
            )
            continue


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(
        main,
        "interval",
        minutes=2,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.start()
