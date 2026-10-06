import os

from deep_translator import ChatGptTranslator
from dotenv import load_dotenv

load_dotenv()
apikey = os.environ["OPENAI_API_KEY"]


def translate_text(text: str, language: str = "english") -> str:
    translated = ChatGptTranslator(api_key=apikey, source='english', target=language).translate(text=text).strip()
    # ChatGPT sometimes wraps its answer in quotes; drop them unless the input was quoted too
    if not text.strip().startswith('"') and len(translated) >= 2 and translated[0] == translated[-1] == '"':
        translated = translated[1:-1]
    return translated
