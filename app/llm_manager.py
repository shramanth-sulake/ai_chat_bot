# app/llm_manager.py  -- revised for openai>=1.0.0
import os
from typing import List
from dotenv import load_dotenv

# New OpenAI client
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment. Add it to .env")

# Create client instance
client = OpenAI(api_key=OPENAI_API_KEY)

# Model / settings
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

PROMPT_SYSTEM = (
    "You are an assistant that answers using ONLY the provided context. "
    #"If the answer cannot be found in the context, respond with: \"I don't know.\" "
    "Keep the answer concise and factual."
    "Do NOT repeat the context verbatim — instead, paraphrase the policy in 1-2 sentences."
)

PROMPT_USER_TEMPLATE = (
    "Context:\n\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)


def generate_answer(question: str, chunks: List[str]) -> str:
    """
    Generate an answer given a user question and a list of retrieved chunks.
    Uses the new OpenAI Python client (>=1.0.0).
    """
    context = "\n\n---\n\n".join(chunks)
    user_prompt = PROMPT_USER_TEMPLATE.format(context=context, question=question)

    messages = [
        {"role": "system", "content": PROMPT_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    # New client call
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=512,
        n=1,
        top_p=1.0,
    )

    # Extract the content (same idea as old SDK; response shape uses .choices[0].message.content)
    answer = resp.choices[0].message.content.strip()
    return answer
