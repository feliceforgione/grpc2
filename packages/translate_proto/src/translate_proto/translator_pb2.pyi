from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Language(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LANGUAGE_UNSPECIFIED: _ClassVar[Language]
    LANGUAGE_ENGLISH: _ClassVar[Language]
    LANGUAGE_ITALIAN: _ClassVar[Language]
    LANGUAGE_SPANISH: _ClassVar[Language]
    LANGUAGE_HUNGARIAN: _ClassVar[Language]
    LANGUAGE_POLISH: _ClassVar[Language]
    LANGUAGE_FRENCH: _ClassVar[Language]
LANGUAGE_UNSPECIFIED: Language
LANGUAGE_ENGLISH: Language
LANGUAGE_ITALIAN: Language
LANGUAGE_SPANISH: Language
LANGUAGE_HUNGARIAN: Language
LANGUAGE_POLISH: Language
LANGUAGE_FRENCH: Language

class TranslateRequest(_message.Message):
    __slots__ = ("text", "language")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    text: str
    language: Language
    def __init__(self, text: _Optional[str] = ..., language: _Optional[_Union[Language, str]] = ...) -> None: ...

class TranslateResponse(_message.Message):
    __slots__ = ("translated_text",)
    TRANSLATED_TEXT_FIELD_NUMBER: _ClassVar[int]
    translated_text: str
    def __init__(self, translated_text: _Optional[str] = ...) -> None: ...
