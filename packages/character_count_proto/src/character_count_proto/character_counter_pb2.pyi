from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CountCharactersRequest(_message.Message):
    __slots__ = ("text_to_count",)
    TEXT_TO_COUNT_FIELD_NUMBER: _ClassVar[int]
    text_to_count: str
    def __init__(self, text_to_count: _Optional[str] = ...) -> None: ...

class CountCharactersResponse(_message.Message):
    __slots__ = ("character_count",)
    CHARACTER_COUNT_FIELD_NUMBER: _ClassVar[int]
    character_count: int
    def __init__(self, character_count: _Optional[int] = ...) -> None: ...
