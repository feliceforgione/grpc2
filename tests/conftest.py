import os

from dotenv import load_dotenv

# translate_grpc.translation reads OPENAI_API_KEY at import time. Load the real key
# from .env first (for live tests), then fall back to a dummy so the offline tests
# can import the server without one; they patch the translator out.
load_dotenv()
os.environ.setdefault("OPENAI_API_KEY", "test-key")
