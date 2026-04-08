import os
from dotenv import load_dotenv
from groq import Groq


load_dotenv() 
client = Groq(
    api_key=os.getenv("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"
))

def get_ai_response(user_message, context, history):

     prompt = f"""
You are a professional reproductive health assistant.

Use ONLY the information below to answer the question.

CONTRACEPTIVE DATA:
{context}

USER QUESTION:
{user_message}

Provide a clear, accurate, and helpful answer.
"""

    
     completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a reproductive health assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

     return completion.choices[0].message.content