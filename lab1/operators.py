from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class OpCategory(Enum):
    ARITHMETIC = auto()
    ASSIGNMENT = auto()
    RELATIONAL = auto()
    LOGICAL = auto()
    BITWISE = auto()
    NULL_COALESCING = auto()
    LAMBDA = auto()
    MEMBER_ACCESS = auto()
    PUNCTUATION = auto()
    KEYWORD_OPERATOR = auto()
    CONTROL_FLOW = auto()
    OOP_STRUCTURAL = auto()
    MODIFIER = auto()
    LINQ = auto()
    PATTERN_MATCHING = auto()
    ACCESSOR = auto()
    TYPE_KEYWORD = auto()
    CALL = auto()
    DECLARATION = auto()


@dataclass(frozen=True)
class OperatorSpec:
    token: str
    category: OpCategory
    is_word: bool = False  



_ARITHMETIC = [
    OperatorSpec(t, OpCategory.ARITHMETIC) for t in ("++", "--", "+", "-", "*", "/", "%")
]

_ASSIGNMENT = [
    OperatorSpec(t, OpCategory.ASSIGNMENT)
    for t in (
        "??=", ">>>=", "<<=", ">>=", "+=", "-=", "*=", "/=", "%=",
        "&=", "|=", "^=", "=",
    )
]

_RELATIONAL = [
    OperatorSpec(t, OpCategory.RELATIONAL) for t in ("==", "!=", "<=", ">=", "<", ">")
]

_LOGICAL = [
    OperatorSpec(t, OpCategory.LOGICAL) for t in ("&&", "||", "!")
]

_BITWISE = [
    OperatorSpec(t, OpCategory.BITWISE) for t in (">>>", "<<", ">>", "&", "|", "^", "~")
]

_NULL_COALESCING = [
    OperatorSpec(t, OpCategory.NULL_COALESCING) for t in ("??", "?.", "?")
]

_LAMBDA = [OperatorSpec("=>", OpCategory.LAMBDA)]

_MEMBER_ACCESS = [
    OperatorSpec(t, OpCategory.MEMBER_ACCESS) for t in ("::", "->", ".")
]

_PUNCTUATION = [
    OperatorSpec(t, OpCategory.PUNCTUATION)
    for t in ("(", ")", "{", "}", "[", "]", ",", ";", ":")
]

_SYMBOL_SPECS = (
    _ARITHMETIC + _ASSIGNMENT + _RELATIONAL + _LOGICAL + _BITWISE
    + _NULL_COALESCING + _LAMBDA + _MEMBER_ACCESS + _PUNCTUATION
)


_KEYWORD_OPERATORS = [
    OperatorSpec(t, OpCategory.KEYWORD_OPERATOR, is_word=True)
    for t in (
        "new", "is", "as", "typeof", "sizeof", "nameof", "checked",
        "unchecked", "default", "await", "yield", "throw", "stackalloc",
    )
]

_CONTROL_FLOW = [
    OperatorSpec(t, OpCategory.CONTROL_FLOW, is_word=True)
    for t in (
        "if", "else", "for", "foreach", "while", "do", "switch", "case",
        "break", "continue", "return", "try", "catch", "finally", "goto",
        "lock",
    )
]

_OOP_STRUCTURAL = [
    OperatorSpec(t, OpCategory.OOP_STRUCTURAL, is_word=True)
    for t in (
        "class", "interface", "struct", "enum", "namespace", "using",
        "delegate", "event", "base", "this", "record",
    )
]

_MODIFIERS = [
    OperatorSpec(t, OpCategory.MODIFIER, is_word=True)
    for t in (
        "public", "private", "protected", "internal", "static", "virtual",
        "override", "abstract", "sealed", "partial", "readonly", "const",
        "async", "extern", "unsafe", "volatile", "ref", "out", "in",
        "params", "required",
    )
]

_LINQ = [
    OperatorSpec(t, OpCategory.LINQ, is_word=True)
    for t in (
        "from", "where", "select", "orderby", "group", "into", "join",
        "let", "ascending", "descending", "on", "equals", "by",
    )
]

_PATTERN_MATCHING = [
    OperatorSpec(t, OpCategory.PATTERN_MATCHING, is_word=True)
    for t in ("when", "and", "or", "not")
]

_ACCESSORS = [
    OperatorSpec(t, OpCategory.ACCESSOR, is_word=True)
    for t in ("get", "set", "add", "remove", "value")
]

_TYPE_KEYWORDS = [
    OperatorSpec(t, OpCategory.TYPE_KEYWORD, is_word=True)
    for t in (
        "int", "uint", "long", "ulong", "short", "ushort", "byte", "sbyte",
        "float", "double", "decimal", "bool", "char", "string", "object",
        "void", "var", "dynamic",
    )
]

_KEYWORD_SPECS = (
    _KEYWORD_OPERATORS + _CONTROL_FLOW + _OOP_STRUCTURAL + _MODIFIERS
    + _LINQ + _PATTERN_MATCHING + _ACCESSORS + _TYPE_KEYWORDS
)

ALL_OPERATOR_SPECS: tuple[OperatorSpec, ...] = tuple(_SYMBOL_SPECS + _KEYWORD_SPECS)


class OperatorRegistry:

    def __init__(self, specs: tuple[OperatorSpec, ...] = ALL_OPERATOR_SPECS):
        by_token: dict[str, OperatorSpec] = {}
        for spec in specs:
            by_token[spec.token] = spec 
        self._by_token = by_token

        self._symbol_tokens_sorted = sorted(
            (s.token for s in by_token.values() if not s.is_word),
            key=len,
            reverse=True,
        )
        self._keyword_tokens = frozenset(
            s.token for s in by_token.values() if s.is_word
        )

    def is_operator(self, token: str) -> bool:
        return token in self._by_token

    def category_of(self, token: str) -> OpCategory | None:
        spec = self._by_token.get(token)
        return spec.category if spec else None

    def symbol_tokens(self) -> list[str]:
        return list(self._symbol_tokens_sorted)

    def keyword_tokens(self) -> frozenset[str]:
        return self._keyword_tokens

    def symbol_regex(self) -> re.Pattern[str]:
        alternatives = "|".join(re.escape(t) for t in self._symbol_tokens_sorted)
        return re.compile(alternatives)

    def keyword_regex(self) -> re.Pattern[str]:
        alternatives = "|".join(re.escape(t) for t in sorted(self._keyword_tokens, key=len, reverse=True))
        return re.compile(rf"\b(?:{alternatives})\b")


DEFAULT_REGISTRY = OperatorRegistry()
