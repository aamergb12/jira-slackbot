from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv
from base64 import b64encode
from openai import OpenAI

# 🌱 Load environment variables from .env
load_dotenv()

# 🌐 Flask App
app = Flask(__name__)

# 🔐 Environment Variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🧠 Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔐 Jira Basic Auth Header
def get_jira_auth_header():
    token = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    return {
        "Authorization": f"Basic {b64encode(token.encode()).decode()}",
        "Content-Type": "application/json"
    }

# ✅ Send a message back to Slack
def send_slack_message(channel_id, message):
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": channel_id, "text": message}
    )

# 📥 Slack Events Endpoint
@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()

    # ✅ Handle Slack's URL verification
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]}), 200, {'Content-Type': 'application/json'}

    event = data.get("event", {})
    user_msg = event.get("text", "")
    channel_id = event.get("channel")

    # 🛑 Skip if message is from a bot or empty
    if not user_msg or "bot_id" in event:
        return jsonify({"ok": True})

    # 🤖 Use OpenAI to extract a Jira summary
    try:
        gpt_resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Extract a short Jira task summary."},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=20
        )
        summary = gpt_resp.choices[0].message.content.strip()
    except Exception as e:
        send_slack_message(channel_id, f"❌ GPT error: {str(e)}")
        return jsonify({"ok": False}), 500

    # 🧱 Create Jira issue payload
    jira_payload = {
        "fields": {
            "project": {"key": "SCRUM"},  # Change if your project key differs
            "summary": summary,
            "issuetype": {"name": "Task"}
        }
    }

    # 📬 Call Jira API to create the issue
    jira_resp = requests.post(
        f"{JIRA_BASE_URL}/rest/api/3/issue",
        headers=get_jira_auth_header(),
        json=jira_payload
    )

    # 💬 Respond in Slack
    if jira_resp.status_code == 201:
        issue_key = jira_resp.json().get("key")
        send_slack_message(channel_id, f"✅ Created Jira issue *{issue_key}*: {summary}")
    else:
        send_slack_message(channel_id, f"❌ Failed to create Jira issue.\n{jira_resp.text}")

    return jsonify({"ok": True})

# 🚀 Start Flask
if __name__ == "__main__":
    app.run(port=8000)
