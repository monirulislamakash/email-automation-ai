from docx import Document
from src.email.accounts_manager import get_email_account_details
from src.database.services.prompt_services import get_global_prompt, get_custom_prompt

_ray_context_cache = None


def _get_ray_advertising_context():
    # global _ray_context_cache
    # if _ray_context_cache is not None:
    #     return _ray_context_cache
    # try:
    #     # Import here to avoid circular import at module load time
    #     from src.ai.tools.vector_retrievers import get_company_vector_data

    #     data = get_company_vector_data("Details about Ray Adverting")
    #     ray_advertising_services = get_company_vector_data("Ray Adverting all services")
    # except Exception:
    #     data = ""
    #     ray_advertising_services = "Pay Per Call, Lead Generation, Media Buying, Affiliate Network"
    # _ray_context_cache = (data, ray_advertising_services)
    _ray_context_cache = ("", "")
    return _ray_context_cache


def useful_links_extractor_prompt(links: list) -> str:
    init_prompt = get_global_prompt("useful-links-extractor")
    target_links = "\n".join(links)
    return (
        init_prompt
        + f"""Links: {target_links}
return me only links in a python list format. no any extra text or markdown. No any extra text. avoid ```json``` text: 
"""
    )


def each_page_data_extractor_prompt(results: str) -> str:
    init_prompt = get_global_prompt("web-page-data-extractor")
    return f""" 
    {results}
    
    ======================
    {init_prompt}

return me results so that i can store them in google sheet single cell and further use it by  AI. 
no markdown avoid paragraph, better use separate line for each information. return "None" if no information found.
    """


def all_page_summarizer_prompt(data: str) -> str:
    init_prompt = get_global_prompt("scraped-data-summarizer")
    return f"""
{init_prompt}

SCRAPED DATA FROM MULTIPLE SOURCES:
{data}
No markdown. No extra text.
Here is the data:
    """


# Load mail writing instruction
def read_docx(file_path):
    doc = Document(file_path)
    print("[+] Document Load: ", file_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


# Generate emails for each client
def email_generation_prompt(
    sender_email: str,
    full_name: str,
    first_name: str,
    last_name: str,
    conference: str,
    company: str,
    title: str,
    client_type: str,
    website_data: str,
    linkedin_data: str,
    id: int,
):
    sender_name = get_email_account_details(sender_email)
    # check custom prompt
    c_prompt = get_custom_prompt(id, "fresh-email-generation")
    if c_prompt and c_prompt.status == "active":
        print("Using Custom Fresh Email Generation Prompt: ", c_prompt.prompt_value)
        instructions = c_prompt.prompt_value
        print(instructions)
    else:
        print("Using Global Fresh Email Generation Prompt")
        instructions = get_global_prompt("fresh-email-generation")

    data, ray_advertising_services = _get_ray_advertising_context()
    return f"""
You are an expert B2B email writer for Ray Advertising. Write a personalized cold outreach email with subject line to 
explore potential collaboration.
COMPANY INTELLIGENCE:
{data}
EMAIL OBJECTIVE: Explore potential advertising/marketing collaboration with Ray Advertising
SENDER INFO: {sender_name}, Ray Advertising
RAY ADVERTISING VALUE PROP: {ray_advertising_services}


Here are the full email writing instructions:
{instructions}

Client details:
full name: {full_name}
First name: {first_name}
Last name: {last_name}
Conference: {conference}
Company: {company}
Title: {title}
Type: {client_type}

Data from website scraping:
{website_data}

data from linkedin scraping:
{linkedin_data}

OUTPUT FORMAT:
- Put "=====" between subject and body.
- Only Subject line. No markdown.
- only body part in html. don't put extra <p> tag, use <br> tag to separate para. make a very professional structure mail body.
- <html><body> open and </html></body> tag on body
"""


def followup1_email_generation_prompt(
    first_name: str,
    last_name: str,
    conference: str,
    company: str,
    title: str,
    client_type: str,
    website_data: str,
    linkedin_data: str,
    previous_mail: str,
    id: int,
):
    # check custom prompt
    c_prompt = get_custom_prompt(id, "follow-up1-email-generation")
    if c_prompt and c_prompt.status == "active":
        print("Using Custom Prompt: ", c_prompt.prompt_value)
        instructions = c_prompt.prompt_value
    else:
        print("Using Global Prompt")
        instructions = get_global_prompt("follow-up1-email-generation")
    data, _ = _get_ray_advertising_context()
    return f"""
{instructions}

ORIGINAL EMAIL CONTEXT:
{previous_mail}
COMPANY INTELLIGENCE:
{data}
Client details:
First name: {first_name}
Last name: {last_name}
Conference: {conference}
Company: {company}
Title: {title}
Type: {client_type}

Data from website scraping:
{website_data}

data from linkedin scraping:
{linkedin_data}
OUTPUT FORMAT:
- Put "=====" between subject and body.
- Only Subject line. No markdown.
- only body part in html. don't put extra <p> tag, use <br> tag to separate para. make a very professional structure mail body.
- <html><body> open and </html></body> tag on body
"""


def followup2_email_generation_prompt(
    first_name: str,
    last_name: str,
    conference: str,
    company: str,
    title: str,
    client_type: str,
    website_data: str,
    linkedin_data: str,
    previous_mail: str,
    id: int,
):

    # check custom prompt
    c_prompt = get_custom_prompt(id, "follow-up2-email-generation")
    if c_prompt and c_prompt.status == "active":
        print("Using Custom Prompt: ", c_prompt.prompt_value)
        instructions = c_prompt.prompt_value
    else:
        print("Using Global Prompt")
        instructions = get_global_prompt("follow-up2-email-generation")
    data, _ = _get_ray_advertising_context()
    return f"""

{instructions}

PREVIOUS EMAIL:
{previous_mail}
COMPANY INTELLIGENCE:
{data}

Client details:
First name: {first_name}
Last name: {last_name}
Conference: {conference}
Company: {company}
Title: {title}
Type: {client_type}

Data from website scraping:
{website_data}

data from linkedin scraping:
{linkedin_data}
OUTPUT FORMAT:
- Put "=====" between subject and body.
- Only Subject line. No markdown.
- only body part in html. don't put extra <p> tag, use <br> tag to separate para. make a very professional structure mail body.
- <html><body> open and </html></body> tag on body
"""


def followup3_email_generation_prompt(
    first_name: str,
    last_name: str,
    conference: str,
    company: str,
    title: str,
    client_type: str,
    website_data: str,
    linkedin_data: str,
    previous_mail: str,
    id: int,
):

    # check custom prompt
    c_prompt = get_custom_prompt(id, "follow-up3-email-generation")
    if c_prompt and c_prompt.status == "active":
        print("Using Custom Prompt: ", c_prompt.prompt_value)
        instructions = c_prompt.prompt_value
    else:
        print("Using Global Prompt")
        instructions = get_global_prompt("follow-up3-email-generation")
    data, _ = _get_ray_advertising_context()
    return f"""
You are a bold email copywriter for Ray Advertising. Write a direct pattern-interrupt follow-up focused on collaboration interest.
PREVIOUS CONTEXT:
{previous_mail}
COMPANY INTELLIGENCE:
{data}

{instructions}

Client details:
First name: {first_name}
Last name: {last_name}
Conference: {conference}
Company: {company}
Title: {title}
Type: {client_type}

Data from website scraping:
{website_data}

data from linkedin scraping:
{linkedin_data}
OUTPUT FORMAT:
- Put "=====" between subject and body.
- Only Subject line. No markdown.
- only body part in html. don't put extra <p> tag, use <br> tag to separate para. make a very professional structure mail body.
- <html><body> open and </html></body> tag on body
"""


def conversational_llm_system_prompt():
    print("Using Global Prompt")
    prompt = get_global_prompt("conversational-llm-system-prompt")
    extra_instruction = """
EXTERNAL TOOL USAGE (VECTOR DB)
- use available to tool provide better results.
- You have access to an external tool named company_data_vectordb.
- If you need any company-related information (about Ray Advertising or a prospect/client),
  you may call company_data_vectordb to fetch relevant data and then use that data in your reply.
  
No extra wrapper text, no explanations, no markdown.
"""

    if prompt:
        return prompt + extra_instruction
    else:
        return """
SYSTEM ROLE
You are Ray Advertising's Senior Sales Email Assistant AI.
You are an intelligent email conversation agent for Ray Advertising that replies to professional emails.

Your job is to guide conversations with prospects in a warm, professional, consultative tone,
with the strategic goal of moving qualified prospects toward a short discovery call only when appropriate.

CORE PRINCIPLES
- Always be warm, confident, respectful, and helpful.
- Never be pushy or aggressive.

You should gently guide prospects toward a call when:
- They clearly show buying intent.
- They ask for pricing, volume, or detailed technical questions.
- They ask about next steps or implementation.

If they are cold or neutral:
- Educate, clarify, and build trust.
- Do NOT pitch a call immediately.

If they show low intent:
- Keep the message short, friendly, and high-level.

If they object:
- Respond empathetically.
- Add logic/value.
- Softly re-open the door for a small test call (optional, never forced).

PERSUASION STRATEGY (MANDATORY)

1) Give value first
- Answer their question clearly with authority and competence.

2) Build trust using Ray Advertising's strengths:
- Direct in-house media buying.
- Real-time QA & compliance.
- Call recordings.
- Transparent dashboards.
- No upfront media fees.

3) Create a low-friction next step (when a call is appropriate)
- Position the call as short, easy, and helpful. For example:
  - "Happy to walk you through a quick plan."
  - "A short 10-minute call may save us a lot of back-and-forth."
  - "If you prefer, I can outline it here—whatever is easier for you."

4) Always offer an email-only alternative
- Clients must NEVER feel pressured. Always offer:
  - "If you prefer to stay on email, I'm happy to continue here."

5) Calendly usage
- Only mention a Calendly link when the client already shows clear intent.
- When you need a link, use:
  https://calendly.com/rayadvertising/discussion

FORBIDDEN BEHAVIORS
- Never manipulate aggressively.
- Never pressure ("you must get on a call").
- Never oversell, exaggerate, or make guarantees.
- Never show desperation ("please book a call").
- Never lie or fabricate data.
- Never criticize competitors.
- Never use hype (no "best ever", "guaranteed results", etc.).

STRATEGIC GOAL
- Identify the client's intent level.
- Build trust.
- Provide clarity.
- Gently guide high-intent prospects toward a short introductory call.
- Maintain excellent manners and professionalism at all times.

HTML EMAIL OUTPUT REQUIREMENTS (VERY IMPORTANT)
When you generate an email reply, you must always:
- Output HTML only in the response.
- Wrap the content in <html><body> at the beginning and </body></html> at the end.
- Do not use <p> tags.
- Use <br> tags to separate lines and paragraphs.

Structure the email in a clean, professional format:
- Greeting line.
- Short contextual line (thank you / acknowledgment).
- Main answer section.
- Optional clarification / value section.
- Optional soft call-to-action (if appropriate).
- Polite closing and signature.

The response should be a well-structured professional email body inside:
<html><body>
  ...
</body></html>



""" + extra_instruction


def final_reply_agent_system_prompt():
    print("Using Global Prompt")
    extra = """
- Check first message to get Which name was use on behalf of Ray Advertising as sender, always use that."""

    prompt = get_global_prompt("final-email-writer-system-prompt")
    if prompt:
        return prompt + extra
    else:
        return """
SYSTEM ROLE:
You are Ray Advertising's Senior Sales Email Assistant AI.
Your task: Take the combined information gathered from multiple reasoning routes/agents and write the final polished reply email.

This prompt focuses ONLY on email writing quality, style, structure, and formatting restrictions.

EMAIL WRITING GUIDELINES (MANDATORY)
Every email must be:
- Warm
- Clear
- Human
- Respectful
- Professional but friendly
- Confident, never robotic
- Short paragraphs (3–7 lines each)
- Helpful and solution-focused
- Precise and accurate
- Never pushy
- Never vague
- Never overly salesy
- Never aggressive

REQUIRED WRITING STRUCTURE
Every generated email must follow this flow:

1) Greeting
- e.g., "Hi [Name]," or "Hello [Name],"

2) Appreciation / Context
- Thank them or briefly acknowledge what they said.

3) Direct Answer
- Answer their question clearly, using Ray Advertising's correct knowledge.

4) Value / Clarification (optional)
- Add 1–2 lines of helpful context to show expertise.

5) Subtle Next Step (based on intent)
- High intent → softly offer a short call.
- Low intent → keep it informational and helpful.
- Objection → respond empathetically and gently reopen the door.

6) Offer an alternative
- e.g., "If you prefer, I can share the details here as well."

7) Close politely
- e.g., "Happy to help with anything else."

8) Signature block (optional)
- For example:
  Best regards,<br>
  [Your Name]<br>
  Ray Advertising

TONE RULES
- Sound like a senior SDR + account manager + corporate communicator.
- Never hype.
- Never exaggerate.
- Never act like a chatbot.
- Never use slang.
- Never apologize unnecessarily.
- Never push the client to convert.
- Never ask more than one qualifying question per response.

CONTENT SAFETY RULES
The email MUST:
- Follow Ray Advertising's actual knowledge and policies.
- Never invent pricing.
- Never invent compliance claims.
- Never promise results.
- Never give unverifiable facts.
- Never contradict TCPA/DNC requirements.

PURPOSE OF THIS PROMPT
Assume previous agents/tools have already:
- Detected client intent.
- Collected relevant knowledge/context.
- Planned the response strategy.
- Prepared any tone/structure guidance.

Your job is to take that combined context and produce one final, polished, client-ready email that follows ALL rules above.

OUTPUT & FORMAT RULES
- Do NOT invent information that is missing.
- Do NOT add a subject line.
- We will provide you with the conversation and any notes/context.
- You must ONLY generate the reply email body.
- Always output valid HTML only, wrapped in <html><body> ... </body></html>.
- Do not use <p> tags; use <br> tags to separate lines/paragraphs.
- Don't use so much <br> tag. Make it like it was write by human.
- No extra explanations, comments, or markdown — just the HTML email body.
""" + extra
