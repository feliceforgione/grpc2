import os
import string

import grpc
import pytest

from translate_proto.translator_pb2 import LANGUAGE_ITALIAN, TranslateRequest
from translate_proto.translator_pb2_grpc import TranslationStub


@pytest.mark.live
@pytest.mark.skipif(
    os.environ["OPENAI_API_KEY"] == "test-key", reason="OPENAI_API_KEY not configured"
)
async def test_live_translate_hello_to_italian(channel: grpc.aio.Channel) -> None:
    stub = TranslationStub(channel)  # type: ignore[no-untyped-call]
    response = await stub.Translate(TranslateRequest(text="Hello", language=LANGUAGE_ITALIAN))

    # The model may add punctuation or capitalisation ("Ciao!"), so normalise first.
    assert response.translated_text.strip(string.punctuation + " ").casefold() == "ciao"
