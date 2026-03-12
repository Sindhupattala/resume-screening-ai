import os
import json
import requests
import logging

logger = logging.getLogger(__name__)

class ResumeInfoExtractor:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.endpoint = os.getenv("ENDPOINT")
        self.deployment = os.getenv("DEPLOYMENT")
        self.api_version = "2024-02-15-preview"

        if not all([self.api_key, self.endpoint, self.deployment]):
            logger.error("Azure OpenAI credentials are not set properly.")

    def extract_info(self, resume_text: str, candidate_name: str) -> dict:
        prompt = f"""
        Extract the following information from the candidate's resume:

        - Full Name
        - Email Address
        - Mobile Number 
            • Extract only numeric characters from any phone number found.
            • Remove any country codes (+91, 91) and formatting symbols (spaces, dashes, parentheses).
            • After cleaning, only take the last 10 digits **if and only if** the resulting number has at least 10 digits.
            • If the resulting number has fewer than 10 digits OR more than 10 digits that cannot be cleaned to exactly 10, return null.
            • Do not guess or pad missing digits.

        - Location / Address (City, State or full address)

        Resume:
        \"\"\"{resume_text}\"\"\"

        ⛔ Respond ONLY with a valid JSON object.
        ⛔ Do NOT include any explanation, headers, or notes.
        ⛔ The Mobile Number field must strictly contain **exactly 10 digits**, or null if a valid 10-digit number cannot be extracted.

        ✅ Example:
        {{
        "Full Name": "John Doe",
        "Email Address": "john.doe@example.com",
        "Mobile Number": "9876543210",
        "Location / Address": "Mumbai, India"
        }}
        """


        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

        body = {
            "messages": [
                {"role": "system", "content": "You are a resume data extraction expert."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 500
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()
            text = result['choices'][0]['message']['content'].strip()
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to extract personal info for {candidate_name}: {e}")
            return {
                "Full Name": None,
                "Email Address": None,
                "Mobile Number": None,

                "Location / Address": None
            }
