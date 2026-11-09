import os
import string

import grpc
import grpc.aio
import pytest

from translate_grpc.deep_translator_provider import DeepTranslatorProvider
from translate_grpc.translation_provider import TranslationProvider
from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub


# Nothing here calls this by name: it overrides conftest.py's translation_provider, which
# translate_grpc_server_address asks for, so this file's server uses the real provider.
@pytest.fixture
def translation_provider() -> TranslationProvider:
    """Translate with the real provider, which calls OpenAI, instead of the mock."""
    return DeepTranslatorProvider(api_key=os.environ["OPENAI_API_KEY"])


@pytest.mark.live
@pytest.mark.skipif("OPENAI_API_KEY" not in os.environ, reason="OPENAI_API_KEY not configured")
async def test_live_translate_hello_to_italian(translate_grpc_channel: grpc.aio.Channel) -> None:
    stub = TranslationStub(translate_grpc_channel)  # type: ignore[no-untyped-call]
    response = await stub.Translate(TranslateRequest(text="Hello", language=LANGUAGE_ITALIAN))

    # The model may add punctuation or capitalisation ("Ciao!"), so normalise first.
    assert response.translated_text.strip(string.punctuation + " ").casefold() == "ciao"
