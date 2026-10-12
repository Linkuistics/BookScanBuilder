"""Unambiguous UTF-8 private object records, before semantic/version validation."""

import json
import math
from dataclasses import dataclass
from typing import NoReturn, cast


@dataclass
class RecordError(Exception):
    message: str
    code: str = "INVALID_PROJECT"
    exit_code: int = 3

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate saved-record key.")
        result[key] = value
    return result


def _constant(value: str) -> NoReturn:
    raise ValueError("Nonfinite saved-record number.")


def _float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Overflowed saved-record number.")
    return result


def _unicode(value: object) -> None:
    # The decoder accepts escaped lone surrogates; they cannot be saved as UTF-8.
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            item.encode("utf-8", errors="strict")
        elif isinstance(item, dict):
            data = cast(dict[str, object], item)
            pending.extend(data)
            pending.extend(data.values())
        elif isinstance(item, list):
            pending.extend(cast(list[object], item))


def decode(raw: bytes) -> dict[str, object]:
    """Reject ambiguous/non-UTF-8 records without reads, writes or coercion.

    This verifies JSON grammar only. The owning reader checks format, capabilities,
    field meaning and referenced asset digests before using the returned object.
    """
    try:
        # Hooks preserve duplicate pairs and reject JSON's nonfinite extensions:
        # https://docs.python.org/3.12/library/json.html#json.load
        value: object = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_object,
            parse_constant=_constant,
            parse_float=_float,
        )
        if not isinstance(value, dict):
            raise ValueError("Saved record is not an object.")
        _unicode(cast(dict[str, object], value))
    except (ValueError, RecursionError) as error:
        # Unicode errors and JSONDecodeError are ValueError subclasses.
        raise RecordError("Invalid private JSON record.") from error
    return cast(dict[str, object], value)
