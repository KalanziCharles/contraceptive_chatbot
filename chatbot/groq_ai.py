import os
from dotenv import load_dotenv
from groq import Groq


load_dotenv() 
GROQ_API_KEY= os.getenv("GROQ_API_KEY")
client = Groq(api_key= GROQ_API_KEY)
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in environment variables")

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