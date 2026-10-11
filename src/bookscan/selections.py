"""Pure invocation/selection rules; no source is opened during parsing."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from bookscan.results import Json, PreparationError

Role = Literal["front", "content", "back"]


@dataclass(frozen=True)
class Token:
    text: str
    exclude: bool
    start: int | None
    end: int | None


@dataclass(frozen=True)
class Selection:
    source: Path
    expression: str
    role: Role
    tokens: tuple[Token, ...] = ()


@dataclass(frozen=True)
class Request:
    selections: tuple[Selection, ...]
    output: Path
    dry_run: bool
    json: bool


@dataclass(frozen=True)
class Occurrence:
    source: Path
    source_page: int
    role: Role


def invalid(message: str) -> PreparationError:
    return PreparationError(
        "INVALID_ARGUMENT",
        message,
        "Use --help for the exact options and quote paths with spaces.",
        2,
    )


def parse(args: list[str]) -> Request:
    selections: list[Selection] = []
    seen: set[str] = set()
    output: Path | None = None
    i = 0
    while i < len(args):
        option = args[i]
        i += 1
        if option not in {"--front", "--content", "--back", "--output", "--dry-run", "--json"}:
            raise invalid(f"Unknown option or positional argument: {option}")
        if option in {"--output", "--dry-run", "--json"}:
            if option in seen:
                raise invalid(f"Repeated singleton option: {option}")
            seen.add(option)
        values: list[str] = []
        while i < len(args) and (
            not args[i].startswith("-")
            or (
                option in {"--front", "--content", "--back"}
                and len(values) == 1
                and re.match(r"-[0-9]", args[i]) is not None
            )
        ):
            values.append(args[i])
            i += 1
        if option in {"--dry-run", "--json"}:
            if values:
                raise invalid(f"{option} takes no values.")
        elif option == "--output":
            if len(values) != 1:
                raise invalid("--output requires exactly one path.")
            output = Path(values[0]).absolute()
        else:
            if len(values) not in (1, 2):
                raise invalid(f"{option} requires PDF [PAGES].")
            role = cast(Role, option.removeprefix("--"))
            selections.append(
                Selection(
                    Path(values[0]).absolute(), values[1] if len(values) == 2 else "all", role
                )
            )
    if output is None:
        raise invalid("--output is required.")
    if not any(s.role == "content" for s in selections):
        raise PreparationError(
            "CONTENT_REQUIRED",
            "At least one content selection is required.",
            "Add --content PDF [PAGES].",
            2,
        )
    return Request(tuple(selections), output, "--dry-run" in seen, "--json" in seen)


def selection_error(
    code: str, selection: Selection, token: str, count: int | None = None
) -> PreparationError:
    context: dict[str, Json] = {
        "source": str(selection.source),
        "selection": selection.expression,
        "token": token,
        "page_count": count,
    }
    remedy = (
        "Use all, positive one-based N or inclusive A-B, comma-separated with no "
        "whitespace; exclusions are !N or !A-B. Single-quote ! expressions."
    )
    if count is not None:
        remedy = f"Use endpoints in 1-{count}; remove an unwanted entire selection."
    return PreparationError(
        code,
        f"{code}: {selection.source}: {selection.expression!r}, token {token!r}",
        remedy,
        2,
        context,
    )


def endpoint(text: str) -> int:
    # Arbitrarily long valid integers must reach bounds checking, not Python's
    # decimal-conversion digit limit. Short chunks keep that limit irrelevant.
    result = 0
    for index in range(0, len(text), 9):
        chunk = text[index : index + 9]
        result = result * (10 ** len(chunk)) + int(chunk)
    return result


def tokenize(selection: Selection) -> Selection:
    tokens: list[Token] = []
    for text in selection.expression.split(","):
        if text == "all":
            tokens.append(Token(text, False, None, None))
            continue
        match = re.fullmatch(r"(!?)([0-9]+)(?:-([0-9]+))?", text)
        if match is None:
            raise selection_error("INVALID_SELECTION", selection, text)
        start, end = endpoint(match[2]), endpoint(match[3] or match[2])
        if min(start, end) == 0:
            raise selection_error("INVALID_SELECTION", selection, text)
        tokens.append(Token(text, bool(match[1]), start, end))
    return Selection(selection.source, selection.expression, selection.role, tuple(tokens))


def resolve(selection: Selection, count: int) -> tuple[int, ...]:
    positive: list[int] = []
    excluded: set[int] = set()
    for token in selection.tokens:
        if token.start is None or token.end is None:
            values = range(1, count + 1)
        else:
            if max(token.start, token.end) > count:
                raise selection_error("PAGE_OUT_OF_RANGE", selection, token.text, count)
            values = range(
                token.start,
                token.end + (1 if token.end >= token.start else -1),
                1 if token.end >= token.start else -1,
            )
        if token.exclude:
            excluded.update(values)
        else:
            positive.extend(values)
    if all(t.exclude for t in selection.tokens):
        positive = list(range(1, count + 1))
    result = tuple(n for n in positive if n not in excluded)
    if not result:
        raise selection_error("EMPTY_SELECTION", selection, selection.expression, count)
    return result
