"""Test-only binding of observed font selection, face creation and open descriptor."""

from pathlib import Path


def bind_loading(events: list[dict[str, object]], pid: int, font: Path) -> dict[str, object]:
    """Require a selected index, successful native face, and its opened file identity.

    This establishes named API/open use, not complete reads, glyph fidelity or
    absence of transient restored changes. The runner freezes bytes separately.
    """
    if type(pid) is not int or pid <= 0 or not events:
        raise ValueError("No valid renderer observation")
    identity = font.stat()
    matches: list[dict[str, object]] = []
    opens: list[dict[str, object]] = []
    faces: list[dict[str, object]] = []
    sequence = 0
    for event in events:
        kind = event.get("kind")
        extra = {
            "match": {"index", "api"},
            "open": {"call", "device", "inode", "size"},
            "face": {"call", "index", "error"},
        }.get(str(kind))
        if extra is None or set(event) != {"version", "pid", "sequence", "kind", "path"} | extra:
            raise ValueError("Unknown native font event")
        numbers = (extra - {"api"}) | {"version", "pid", "sequence"}
        if any(type(event[key]) is not int for key in numbers):
            raise ValueError("Malformed native font event")
        if event["version"] != 1 or event["pid"] != pid or event["path"] != str(font):
            raise ValueError("Foreign native font observation")
        current = event["sequence"]
        if not isinstance(current, int) or current <= sequence:
            raise ValueError("Unordered native font observation")
        sequence = current
        if kind == "match":
            if event["api"] not in ("FcFontMatch", "FcFontSort"):
                raise ValueError("Unknown native font selection API")
            matches.append(event)
        elif kind == "open":
            if (event["device"], event["inode"], event["size"]) != (
                identity.st_dev,
                identity.st_ino,
                identity.st_size,
            ):
                raise ValueError("Actual open descriptor names a different file")
            opens.append(event)
        else:
            faces.append(event)
    bound: set[int] = set()
    joined: set[int] = set()
    for face in faces:
        index, call, end = face["index"], face["call"], face["sequence"]
        if not isinstance(index, int) or not isinstance(call, int) or not isinstance(end, int):
            raise ValueError("Malformed face identity")
        if face["error"] != 0 or index < 0 or call <= 0:
            continue
        selected = [row for row in matches if row["index"] == index]
        opened = [row for row in opens if row["call"] == call]
        if any(
            isinstance(match["sequence"], int)
            and isinstance(row["sequence"], int)
            and match["sequence"] < row["sequence"] < end
            for match in selected
            for row in opened
        ):
            bound.add(index)
            joined.add(call)
    if not bound:
        raise ValueError("No selected successful face bound to its actual open descriptor")
    return {
        "font": str(font),
        "face_indexes": sorted(bound),
        "face_calls": sorted(joined),
        "open_count": len(opens),
        "selection_apis": sorted({str(row["api"]) for row in matches}),
        "runtime_resources_verified": False,
    }
