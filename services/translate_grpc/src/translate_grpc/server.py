import asyncio
import logging

import grpc
from translate_proto import translator_pb2, translator_pb2_grpc
from translate_proto.languages import language_name
from translate_grpc.translation import translate_text


class Translator(translator_pb2_grpc.TranslationServicer):
    async def Translate(
        self,
        request: translator_pb2.TranslateRequest,
        context: grpc.aio.ServicerContext,
    ) -> translator_pb2.TranslateResponse:
        if (request.language == translator_pb2.LANGUAGE_UNSPECIFIED
                or request.language not in translator_pb2.Language.values()):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                                "language must be set to a supported value")
        language = language_name(request.language)
        translated_text = translate_text(request.text, language)
        logging.info("%s translated to [%s] %s",
                     request.text, language, translated_text)
        return translator_pb2.TranslateResponse(translated_text=translated_text)


async def serve() -> None:
    server = grpc.aio.server()
    translator_pb2_grpc.add_TranslationServicer_to_server(Translator(), server)
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
