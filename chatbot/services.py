from groq import Groq

client = Groq(
    api_key="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"
)

SYSTEM_PROMPT = """
You are Careergize Assistant.

You are a professional counselor representing Careergize.

You help users with:

1. Web & Mobile Development
2. AI/ML Training
3. Admissions
4. Internships & Placement

Speak naturally and professionally.
Always guide users toward Careergize services.
Ask follow-up questions.
"""


def generate_response(user_message, history=None):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if history:
        messages.extend(history)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
        max_tokens=1024
    )

    return response.choices[0].message.content