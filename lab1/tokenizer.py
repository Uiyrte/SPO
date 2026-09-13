from __future__ import annotations

import re
from dataclasses import dataclass

from operators import DEFAULT_REGISTRY, OpCategory, OperatorRegistry


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    category: OpCategory | None = None


def _build_pattern(registry: OperatorRegistry) -> re.Pattern[str]:
    symbols = "|".join(re.escape(t) for t in registry.symbol_tokens())
    return re.compile(
        r"""
        (?P<COMMENT_ML>/\*.*?\*/)
      | (?P<COMMENT_SL>//[^\n]*)
      | (?P<PREPROCESSOR>\#[^\n]*)
      | (?P<STRING_INTERP_VERBATIM>(?:\$@|@\$)"(?:[^"]|"")*")
      | (?P<STRING_VERBATIM>@"(?:[^"]|"")*")
      | (?P<STRING_INTERP>\$"(?:\\.|[^"\\])*")
      | (?P<STRING_REGULAR>"(?:\\.|[^"\\])*")
      | (?P<CHAR_LITERAL>'(?:\\.|[^'\\])*')
      | (?P<NUMBER>
            0[xX][0-9a-fA-F_]+[uUlL]*
          | 0[bB][01_]+[uUlL]*
          | \d[\d_]*(?:\.[\d_]+)?(?:[eE][+-]?\d+)?[fFdDmMuUlL]*
        )
      | (?P<IDENTIFIER>@?[^\W\d]\w*)
      | (?P<SYMBOL>""" + symbols + r""")
      | (?P<SKIP>\s+)
      | (?P<OTHER>.)
        """,
        re.VERBOSE | re.DOTALL,
    )


_LITERAL_GROUPS = frozenset(
    {
        "STRING_INTERP_VERBATIM",
        "STRING_VERBATIM",
        "STRING_INTERP",
        "STRING_REGULAR",
        "CHAR_LITERAL",
        "NUMBER",
    }
)
_IGNORED_GROUPS = frozenset({"COMMENT_ML", "COMMENT_SL", "PREPROCESSOR", "SKIP"})
_HEADER_KEYWORDS = frozenset(
    {"for", "while", "foreach", "if", "switch", "catch", "using", "lock", "when"}
)
_INTERPOLATED_GROUPS = frozenset({"STRING_INTERP", "STRING_INTERP_VERBATIM"})


def _strip_interpolation_specifiers(expr_text: str) -> str:
    depth = 0
    pending_ternary = 0
    i, n = 0, len(expr_text)
    while i < n:
        c = expr_text[i]
        if c in "{([":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif depth == 0:
            if c == "?" and expr_text[i + 1 : i + 2] in ("?", ".", "["):
                i += 2
                continue
            if c == "?":
                pending_ternary += 1
            elif c == ":":
                if pending_ternary > 0:
                    pending_ternary -= 1
                else:
                    return expr_text[:i]
            elif c == ",":
                return expr_text[:i]
        i += 1
    return expr_text


def _split_interpolated_string(literal: str) -> list[tuple[bool, str]]:
    body = literal[2:] if literal[:2] in ("$@", "@$") else literal[1:]
    body = body[1:-1]

    segments: list[tuple[bool, str]] = []
    buf: list[str] = []
    i, n = 0, len(body)
    while i < n:
        ch = body[i]
        if ch == "{" and i + 1 < n and body[i + 1] == "{":
            buf.append("{")
            i += 2
        elif ch == "}" and i + 1 < n and body[i + 1] == "}":
            buf.append("}")
            i += 2
        elif ch == "{":
            if buf:
                segments.append((False, "".join(buf)))
                buf = []
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                c = body[j]
                if c in "{([":
                    depth += 1
                elif c in "}])":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            segments.append((True, _strip_interpolation_specifiers(body[i + 1 : j])))
            i = j + 1
        else:
            buf.append(ch)
            i += 1
    if buf:
        segments.append((False, "".join(buf)))
    return segments


def _tokenize_interpolated_literal(literal: str, registry: OperatorRegistry) -> list[Token]:
    result: list[Token] = []
    for is_expr, text in _split_interpolated_string(literal):
        if is_expr:
            result.extend(tokenize(text, registry))
        elif text:
            result.append(Token("operand", f'"{text}"'))
    return result


def _find_header_suppressions(raw: list[tuple[str, str]]) -> tuple[set[int], dict[int, int]]:
    suppressed: set[int] = set()
    header_close: dict[int, int] = {}
    n = len(raw)
    for i, (kind, value) in enumerate(raw):
        if value not in _HEADER_KEYWORDS or i + 1 >= n or raw[i + 1] != ("SYMBOL", "("):
            continue

        open_idx = i + 1
        suppressed.add(open_idx)
        depth = 1
        j = open_idx + 1
        while j < n and depth > 0:
            tok_kind, tok_value = raw[j]
            if tok_kind == "SYMBOL" and tok_value == "(":
                depth += 1
            elif tok_kind == "SYMBOL" and tok_value == ")":
                depth -= 1
                if depth == 0:
                    suppressed.add(j)
                    header_close[i] = j
                    break
            elif value == "for" and depth == 1 and tok_kind == "SYMBOL" and tok_value == ";":
                suppressed.add(j)
            j += 1

    return suppressed, header_close


def _after_header(idx: int, header_close: dict[int, int]) -> int:
    return header_close[idx] + 1 if idx in header_close else idx + 1


def _after_optional_block(idx: int, raw: list[tuple[str, str]], open_to_close: dict[int, int]) -> int:
    if idx < len(raw) and raw[idx] == ("SYMBOL", "{"):
        return open_to_close.get(idx, idx) + 1
    return idx


_EMBEDDABLE_HEADER_KEYWORDS = frozenset({"if", "for", "while", "foreach", "lock", "using"})


def _skip_embedded_statement(
    idx: int,
    raw: list[tuple[str, str]],
    header_close: dict[int, int],
    open_to_close: dict[int, int],
) -> int:
    """Return the raw index right after the single embedded statement (braced
    block or brace-less single statement, e.g. `if (x) return;`) starting at idx."""
    n = len(raw)
    if idx >= n:
        return idx

    kind, value = raw[idx]

    if value == "{":
        return open_to_close.get(idx, idx) + 1

    if value in _EMBEDDABLE_HEADER_KEYWORDS and idx in header_close:
        return _skip_embedded_statement(header_close[idx] + 1, raw, header_close, open_to_close)

    if value == "do":
        after_body = _skip_embedded_statement(idx + 1, raw, header_close, open_to_close)
        if after_body < n and raw[after_body] == ("IDENTIFIER", "while") and after_body in header_close:
            after_while = header_close[after_body] + 1
            if after_while < n and raw[after_while] == ("SYMBOL", ";"):
                return after_while + 1
            return after_while
        return after_body

    depth = 0
    j = idx
    while j < n:
        k, v = raw[j]
        if k == "SYMBOL" and v in "{([":
            depth += 1
        elif k == "SYMBOL" and v in "}])":
            depth -= 1
        elif k == "SYMBOL" and v == ";" and depth == 0:
            return j + 1
        j += 1
    return n


def _find_compound_control_merges(
    raw: list[tuple[str, str]], header_close: dict[int, int], open_to_close: dict[int, int]
) -> tuple[dict[int, str], set[int]]:
    rename: dict[int, str] = {}
    suppressed: set[int] = set()
    n = len(raw)

    for i, (kind, value) in enumerate(raw):
        if value == "if" and i in header_close:
            body_start = header_close[i] + 1
            body_end = _skip_embedded_statement(body_start, raw, header_close, open_to_close)
            if body_end < n and raw[body_end] == ("IDENTIFIER", "else"):
                rename[i] = "if...else"
                suppressed.add(body_end)

        elif value == "do":
            body_end = _skip_embedded_statement(i + 1, raw, header_close, open_to_close)
            if body_end < n and raw[body_end] == ("IDENTIFIER", "while"):
                rename[i] = "do...while"
                suppressed.add(body_end)

        elif value == "try":
            j = _after_optional_block(i + 1, raw, open_to_close)
            has_catch = False
            has_finally = False
            to_suppress: list[int] = []
            while j < n and raw[j] == ("IDENTIFIER", "catch"):
                has_catch = True
                to_suppress.append(j)
                k = _after_header(j, header_close)
                if k < n and raw[k] == ("IDENTIFIER", "when"):
                    to_suppress.append(k)
                    k = _after_header(k, header_close)
                j = _after_optional_block(k, raw, open_to_close)
            if j < n and raw[j] == ("IDENTIFIER", "finally"):
                has_finally = True
                to_suppress.append(j)
                j = _after_optional_block(j + 1, raw, open_to_close)
            if has_catch or has_finally:
                label = "try"
                if has_catch:
                    label += "...catch"
                if has_finally:
                    label += "...finally"
                rename[i] = label
                suppressed.update(to_suppress)

    return rename, suppressed


def _find_switch_case_merges(
    raw: list[tuple[str, str]], header_close: dict[int, int], open_to_close: dict[int, int]
) -> tuple[dict[int, str], set[int]]:
    rename: dict[int, str] = {}
    suppressed: set[int] = set()

    for i, (kind, value) in enumerate(raw):
        if value != "switch" or i not in header_close:
            continue
        body_open = header_close[i] + 1
        if body_open >= len(raw) or raw[body_open] != ("SYMBOL", "{"):
            continue
        body_close = open_to_close.get(body_open)
        if body_close is None:
            continue

        found_case = False
        depth = 1
        j = body_open + 1
        while j < body_close:
            kind_j, value_j = raw[j]
            if kind_j == "SYMBOL" and value_j in "{([":
                depth += 1
            elif kind_j == "SYMBOL" and value_j in "}])":
                depth -= 1
            elif depth == 1 and value_j in ("case", "default"):
                found_case = True
                suppressed.add(j)
                colon_depth = 1
                m = j + 1
                while m < body_close:
                    kind_m, value_m = raw[m]
                    if kind_m == "SYMBOL" and value_m in "{([":
                        colon_depth += 1
                    elif kind_m == "SYMBOL" and value_m in "}])":
                        colon_depth -= 1
                    elif kind_m == "SYMBOL" and value_m == ":" and colon_depth == 1:
                        suppressed.add(m)
                        j = m
                        break
                    m += 1
                else:
                    j = m
            j += 1

        if found_case:
            rename[i] = "switch...case"

    return rename, suppressed


_GENERIC_CONTENT_SYMBOLS = frozenset({".", ",", "[", "]", "?"})
_GENERIC_FOLLOWERS = frozenset({"(", ")", ",", ";", "]", "[", ".", "?", "{", ":"})


def _find_generic_suppressions(raw: list[tuple[str, str]]) -> tuple[set[int], dict[int, int]]:
    suppressed: set[int] = set()
    span_end: dict[int, int] = {}
    n = len(raw)
    i = 0
    while i < n:
        kind, value = raw[i]
        if kind == "SYMBOL" and value == "<" and i > 0 and raw[i - 1][0] == "IDENTIFIER":
            depth = 1
            j = i + 1
            angle_indices = [i]
            valid = True
            while j < n and depth > 0:
                k, v = raw[j]
                if k == "SYMBOL" and v == "<":
                    depth += 1
                    angle_indices.append(j)
                elif k == "SYMBOL" and v in (">", ">>", ">>>"):
                    depth -= len(v)
                    angle_indices.append(j)
                elif k == "IDENTIFIER" or (k == "SYMBOL" and v in _GENERIC_CONTENT_SYMBOLS):
                    pass
                else:
                    valid = False
                    break
                j += 1

            if valid and depth == 0:
                after_kind, after_value = raw[j] if j < n else (None, None)
                if after_value in _GENERIC_FOLLOWERS or after_kind == "IDENTIFIER":
                    suppressed.update(angle_indices)
                    span_end[i] = j
                    i = j
                    continue
        i += 1

    return suppressed, span_end


_BRACKET_PAIRS = {"(": ")", "{": "}", "[": "]"}


def _find_bracket_pairs(
    raw: list[tuple[str, str]], header_suppressed: set[int]
) -> tuple[set[int], dict[int, str], dict[int, int]]:
    skip_opens: set[int] = set()
    merged_at_close: dict[int, str] = {}
    open_to_close: dict[int, int] = {}
    stacks: dict[str, list[int]] = {opener: [] for opener in _BRACKET_PAIRS}
    closers = {closer: opener for opener, closer in _BRACKET_PAIRS.items()}

    for i, (kind, value) in enumerate(raw):
        if i in header_suppressed or kind != "SYMBOL":
            continue
        if value in _BRACKET_PAIRS:
            stacks[value].append(i)
        elif value in closers:
            opener = closers[value]
            if stacks[opener]:
                open_idx = stacks[opener].pop()
                skip_opens.add(open_idx)
                open_to_close[open_idx] = i
                merged_at_close[i] = "( )" if opener == "(" else opener + value

    return skip_opens, merged_at_close, open_to_close


def _is_declaration_context(raw: list[tuple[str, str]], i: int, registry: OperatorRegistry) -> bool:
    if i == 0:
        return False
    prev_kind, prev_value = raw[i - 1]
    if prev_value in (".", "new"):
        return False
    if prev_kind == "SYMBOL" and prev_value in (">", ">>", ">>>"):
        return True
    if prev_kind == "IDENTIFIER":
        category = registry.category_of(prev_value)
        return category in (None, OpCategory.MODIFIER, OpCategory.TYPE_KEYWORD)
    return False


def _scan_to_top_level_semicolon(raw: list[tuple[str, str]], start: int) -> int:
    depth = 0
    n = len(raw)
    j = start
    while j < n:
        k, v = raw[j]
        if k == "SYMBOL" and v in "{([":
            depth += 1
        elif k == "SYMBOL" and v in "}])":
            depth -= 1
        elif k == "SYMBOL" and v == ";" and depth == 0:
            return j
        j += 1
    return n


def _scan_past_where_clause(raw: list[tuple[str, str]], start: int) -> int:
    n = len(raw)
    j = start
    while j < n:
        k, v = raw[j]
        if k == "SYMBOL" and v in ("{", ";"):
            return j
        if k == "IDENTIFIER" and v == "where" and j != start:
            return j
        j += 1
    return n


def _find_body_regions(
    raw: list[tuple[str, str]],
    open_to_close: dict[int, int],
    generic_span_end: dict[int, int],
    registry: OperatorRegistry,
) -> set[int]:
    included: set[int] = set()
    n = len(raw)

    for i, (kind, value) in enumerate(raw):
        if kind != "IDENTIFIER":
            continue
        category = registry.category_of(value)

        if category == OpCategory.ACCESSOR:
            j = i + 1
            if j < n and raw[j] == ("SYMBOL", "{"):
                close = open_to_close.get(j)
                if close is not None:
                    included.update(range(j + 1, close + 1))
            elif j < n and raw[j] == ("SYMBOL", "=>"):
                end = _scan_to_top_level_semicolon(raw, j + 1)
                included.update(range(j + 1, end + 1))
            continue

        if category is not None:
            continue

        next_idx = i + 1
        if next_idx < n and raw[next_idx] == ("SYMBOL", "<") and next_idx in generic_span_end:
            next_idx = generic_span_end[next_idx]

        if next_idx < n and raw[next_idx] == ("SYMBOL", "("):
            if not _is_declaration_context(raw, i, registry):
                continue
            close_paren = open_to_close.get(next_idx)
            if close_paren is None:
                continue
            after = close_paren + 1
            while after < n and raw[after] == ("IDENTIFIER", "where"):
                after = _scan_past_where_clause(raw, after)
            if after < n and raw[after] == ("SYMBOL", "{"):
                close = open_to_close.get(after)
                if close is not None:
                    included.update(range(after + 1, close + 1))
            elif after < n and raw[after] == ("SYMBOL", "=>"):
                end = _scan_to_top_level_semicolon(raw, after + 1)
                included.update(range(after + 1, end + 1))
            continue

        if (
            next_idx < n
            and raw[next_idx] == ("SYMBOL", "=>")
            and _is_declaration_context(raw, i, registry)
        ):
            end = _scan_to_top_level_semicolon(raw, next_idx + 1)
            included.update(range(next_idx + 1, end + 1))

    return included


def tokenize(
    source: str, registry: OperatorRegistry = DEFAULT_REGISTRY, scope: str = "all"
) -> list[Token]:
    pattern = _build_pattern(registry)
    raw: list[tuple[str, str]] = []

    for match in pattern.finditer(source):
        kind = match.lastgroup
        if kind in _IGNORED_GROUPS or kind == "OTHER":
            continue
        raw.append((kind, match.group()))

    header_suppressed, header_close = _find_header_suppressions(raw)
    skip_opens, merged_at_close, open_to_close = _find_bracket_pairs(raw, header_suppressed)
    control_rename, control_suppressed = _find_compound_control_merges(raw, header_close, open_to_close)
    switch_rename, switch_suppressed = _find_switch_case_merges(raw, header_close, open_to_close)
    generic_suppressed, generic_span_end = _find_generic_suppressions(raw)
    rename = {**control_rename, **switch_rename}
    suppressed = (
        header_suppressed | skip_opens | control_suppressed | switch_suppressed | generic_suppressed
    )
    call_consumed_closes: set[int] = set()
    goto_consumed: set[int] = set()

    body_included = (
        _find_body_regions(raw, open_to_close, generic_span_end, registry)
        if scope == "bodies"
        else None
    )

    tokens: list[Token] = []
    for i, (kind, value) in enumerate(raw):
        if i in suppressed or i in call_consumed_closes or i in goto_consumed:
            continue
        if body_included is not None and i not in body_included:
            continue

        if kind in _LITERAL_GROUPS:
            if kind in _INTERPOLATED_GROUPS:
                tokens.extend(_tokenize_interpolated_literal(value, registry))
            else:
                tokens.append(Token("operand", value))
            continue

        if kind == "IDENTIFIER":
            category = registry.category_of(value)
            if category is not None:
                if value == "goto" and i + 1 < len(raw):
                    label_kind, label_value = raw[i + 1]
                    if label_kind == "IDENTIFIER" and registry.category_of(label_value) is None:
                        goto_consumed.add(i + 1)
                        tokens.append(Token("operator", f"goto {label_value}", category))
                        continue
                tokens.append(Token("operator", rename.get(i, value), category))
            else:
                next_idx = i + 1
                if next_idx < len(raw) and raw[next_idx] == ("SYMBOL", "<") and next_idx in generic_span_end:
                    next_idx = generic_span_end[next_idx]
                if next_idx < len(raw) and raw[next_idx] == ("SYMBOL", "("):
                    is_decl = _is_declaration_context(raw, i, registry)
                    op_category = OpCategory.DECLARATION if is_decl else OpCategory.CALL
                    display = f"{value}(decl)" if is_decl else f"{value}( )"
                    close_idx = open_to_close.get(next_idx)
                    if close_idx is not None:
                        call_consumed_closes.add(close_idx)
                        tokens.append(Token("operator", display, op_category))
                    else:
                        tokens.append(Token("operator", value, op_category))
                else:
                    tokens.append(Token("operand", value))
            continue

        if kind == "SYMBOL":
            merged = merged_at_close.get(i)
            if merged is not None:
                tokens.append(Token("operator", merged, OpCategory.PUNCTUATION))
            else:
                tokens.append(Token("operator", value, registry.category_of(value)))
            continue

    return tokens
