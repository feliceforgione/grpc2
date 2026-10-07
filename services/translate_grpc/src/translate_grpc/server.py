import asyncio
import logging

import grpc
from translate_proto.translator_pb2_grpc import TranslationServicer, add_TranslationServicer_to_server
from translate_proto.translator_pb2 import LANGUAGE_UNSPECIFIED, Language, TranslateRequest, TranslateResponse
from translate_proto.languages import format_language_name
from translate_grpc.translation import translate_text


class Translator(TranslationServicer):
    async def Translate(
        self,
        request: TranslateRequest,
        context: grpc.aio.ServicerContext[TranslateRequest, TranslateResponse],
    ) -> TranslateResponse:
        if (request.language == LANGUAGE_UNSPECIFIED
                or request.language not in Language.values()):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                                "language must be set to a supported value")
        language = format_language_name(request.language)
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
