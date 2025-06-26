from flask import Flask, request, jsonify
import os
import openai
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    user_msg = data.get("event", {}).get("text", "")
    
    if not user_msg:
        return jsonify({"ok": True})

    # Use GPT to extract intent
    prompt = f"Interpret this Jira command and return what the user wants to do:\n\n'{user_msg}'"
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=100
    )
    gpt_reply = response.choices[0].text.strip()

    # Return the GPT's interpretation to Slack
    slack_response = {
        "text": f"🤖 I understood: {gpt_reply}"
    }

    return jsonify(slack_response)

if __name__ == "__main__":
    app.run(port=8000)
