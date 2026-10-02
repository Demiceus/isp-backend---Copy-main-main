# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:demi@localhost:5432/isp"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AI_API_KEY = os.environ.get("AI_API_KEY")
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "anthropic")  # anthropic | openai | ollama

    # Lazy staleness threshold — checked when relevant, not on a timer
    SESSION_STALE_MINUTES = int(os.environ.get("SESSION_STALE_MINUTES", 15))

    # Bounded chat history sent to the AI API per call
    MAX_HISTORY_MESSAGES = int(os.environ.get("MAX_HISTORY_MESSAGES", 12))