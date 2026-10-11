"""Stable command records, independent of PDF and filesystem representation."""

from dataclasses import dataclass, field

type Json = str | int | bool | None | list[Json] | dict[str, Json]


@dataclass
class PreparationError(Exception):
    code: str
    message: str
    remediation: str
    exit_code: int
    context: dict[str, Json] = field(default_factory=lambda: dict[str, Json]())

    def record(self, output: str | None) -> dict[str, Json]:
        result: dict[str, Json] = {
            "schema_version": 1,
            "status": "error",
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
            "warnings": [],
        }
        if output is not None:
            result["output"] = output
        result.update(self.context)
        return result
