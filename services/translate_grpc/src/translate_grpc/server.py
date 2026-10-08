import asyncio
import logging

import grpc
from translate_proto.translator_pb2_grpc import TranslationServicer, add_TranslationServicer_to_server
from translate_proto.translator_pb2 import TranslateRequest, TranslateResponse
from translate_proto.languages import convert_language_name, is_supported_language
from translate_grpc.translation import translate_text


async def _validate_request_language(
    language: int,
    context: grpc.aio.ServicerContext[TranslateRequest, TranslateResponse],
) -> None:
    if not is_supported_language(language):
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                            "language must be set to a supported value")


class Translator(TranslationServicer):
    async def Translate(
        self,
        request: TranslateRequest,
        context: grpc.aio.ServicerContext[TranslateRequest, TranslateResponse],
    ) -> TranslateResponse:
        await _validate_request_language(request.language, context)
        language = convert_language_name(request.language)
        translated_text = translate_text(request.text, language)
        logging.info("%s translated to [%s] %s",
                     request.text, language, translated_text)
        return TranslateResponse(translated_text=translated_text)


async def serve() -> None:
    server = grpc.aio.server()
    add_TranslationServicer_to_server(  # type: ignore[no-untyped-call]
        Translator(), server
    )
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())


if __name__ == "__main__":
    main()
