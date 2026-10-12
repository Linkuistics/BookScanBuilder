"""Declared loader graphs challenge dependency accounting without using its resolver as truth."""

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from bookscan import dependencies
from bookscan.skew import NativeError


def commands(path: Path, *items: tuple[str, str]) -> str:
    body: list[str] = []
    for index, (kind, value) in enumerate(items):
        field = "path" if kind == "LC_RPATH" else "name"
        body.append(f"Load command {index}\n cmd {kind}\n cmdsize 64\n {field} {value} (offset 24)")
    return f"{path}:\n" + "\n".join(body) + "\n"


@pytest.fixture
def graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[Path, str]:
    outputs: dict[Path, str] = {}

    def checked(argv: list[str], *, check_cancel: Callable[[], None]) -> str:
        check_cancel()
        if argv[0] == "/usr/bin/sw_vers":
            return "test-build"
        assert argv[1:4] == ["-arch", "arm64", "-l"]
        return outputs[Path(argv[4])]

    monkeypatch.setattr(dependencies, "checked", checked)

    def tool_path(name: str) -> Path:
        return tmp_path / name

    monkeypatch.setattr(dependencies, "tool", tool_path)
    monkeypatch.setattr(dependencies.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dependencies.platform, "machine", lambda: "arm64")
    return outputs


def file(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(name.encode())
    return path


def records(report: dict[str, object]) -> dict[str, dict[str, object]]:
    return cast(dict[str, dict[str, object]], report["files"])


@pytest.mark.parametrize(
    "kind",
    [
        "LC_LOAD_DYLIB",
        "LC_LOAD_WEAK_DYLIB",
        "LC_REEXPORT_DYLIB",
        "LC_LOAD_UPWARD_DYLIB",
        "LC_LAZY_LOAD_DYLIB",
    ],
)
def test_load_kinds_follow_transitive_cycle_and_ignore_install_id(
    tmp_path: Path, graph: dict[Path, str], kind: str
) -> None:
    root, child = file(tmp_path, "program"), file(tmp_path, "lib/a.dylib")
    graph[root] = commands(root, (kind, "@loader_path/lib/a.dylib"))
    graph[child] = commands(child, ("LC_ID_DYLIB", "/not-a-dependency"), (kind, str(root)))
    report = dependencies.linked_identity(root)
    assert set(records(report)) == {str(root), str(child)}
    assert records(report)[str(child)]["sha256"] == hashlib.sha256(child.read_bytes()).hexdigest()
    assert report["runtime_resources_verified"] is False


def test_inherited_rpath_and_executable_path(tmp_path: Path, graph: dict[Path, str]) -> None:
    root = file(tmp_path, "bin/program")
    first, second = file(tmp_path, "lib/a.dylib"), file(tmp_path, "lib/b.dylib")
    graph[root] = commands(
        root, ("LC_RPATH", "@executable_path/../lib"), ("LC_LOAD_DYLIB", "@rpath/a.dylib")
    )
    graph[first] = commands(first, ("LC_LOAD_DYLIB", "@rpath/b.dylib"))
    graph[second] = commands(second, ("LC_ID_DYLIB", str(second)))
    assert set(records(dependencies.linked_identity(root))) == {str(root), str(first), str(second)}


def test_extension_executable_path_means_interpreter_not_extension(
    tmp_path: Path, graph: dict[Path, str]
) -> None:
    extension = file(tmp_path, "packages/module.so")
    interpreter = file(tmp_path, "python/bin/python")
    library = file(tmp_path, "python/lib/runtime.dylib")
    graph[extension] = commands(
        extension, ("LC_LOAD_DYLIB", "@executable_path/../lib/runtime.dylib")
    )
    graph[library] = commands(library, ("LC_ID_DYLIB", str(library)))
    report = dependencies.linked_identity(extension, executable_context=interpreter)
    assert set(records(report)) == {str(extension), str(library)}


def test_system_references_have_os_identity_without_fake_disk_hash(
    tmp_path: Path, graph: dict[Path, str]
) -> None:
    root = file(tmp_path, "program")
    graph[root] = commands(root, ("LC_LOAD_DYLIB", "/usr/lib/libSystem.B.dylib"))
    report = dependencies.linked_identity(root)
    assert set(records(report)) == {str(root)}
    assert report["os_build"] == "test-build"
    assert report["system_references"] == ["/usr/lib/libSystem.B.dylib"]


def test_system_prefix_cannot_hide_parent_escape(tmp_path: Path, graph: dict[Path, str]) -> None:
    root = file(tmp_path, "program")
    graph[root] = commands(root, ("LC_LOAD_DYLIB", "/usr/lib/../../private/unverified.dylib"))
    with pytest.raises(NativeError):
        dependencies.linked_identity(root)


def test_missing_os_build_identity_is_unavailable(
    tmp_path: Path, graph: dict[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = file(tmp_path, "program")
    original = dependencies.checked

    def empty(argv: list[str], *, check_cancel: Callable[[], None]) -> str:
        return "" if argv[0] == "/usr/bin/sw_vers" else original(argv, check_cancel=check_cancel)

    monkeypatch.setattr(dependencies, "checked", empty)
    with pytest.raises(NativeError, match="build"):
        dependencies.linked_identity(root)


@pytest.mark.parametrize(
    "reference",
    ["@rpath/missing", "@loader_path/missing", "relative.dylib", "@unknown/a", "/missing/a"],
)
def test_missing_or_unrecognized_dependency_is_explicit(
    tmp_path: Path, graph: dict[Path, str], reference: str
) -> None:
    root = file(tmp_path, "program")
    graph[root] = commands(root, ("LC_LOAD_DYLIB", reference))
    with pytest.raises(NativeError) as caught:
        dependencies.linked_identity(root)
    assert caught.value.exit_code == 5
    assert reference in str(caught.value)


def test_multiple_distinct_rpath_candidates_are_not_guessed(
    tmp_path: Path, graph: dict[Path, str]
) -> None:
    root = file(tmp_path, "program")
    file(tmp_path, "a/lib.dylib")
    file(tmp_path, "b/lib.dylib")
    graph[root] = commands(
        root,
        ("LC_RPATH", str(tmp_path / "a")),
        ("LC_RPATH", str(tmp_path / "b")),
        ("LC_LOAD_DYLIB", "@rpath/lib.dylib"),
    )
    with pytest.raises(NativeError, match="Ambiguous"):
        dependencies.linked_identity(root)


def test_one_library_cannot_resolve_differently_on_two_load_chains(
    tmp_path: Path, graph: dict[Path, str]
) -> None:
    root, a, b, shared = (file(tmp_path, name) for name in ("program", "a", "b", "shared"))
    first, second = file(tmp_path, "first/leaf"), file(tmp_path, "second/leaf")
    graph[root] = commands(root, ("LC_LOAD_DYLIB", str(a)), ("LC_LOAD_DYLIB", str(b)))
    graph[a] = commands(a, ("LC_RPATH", str(first.parent)), ("LC_LOAD_DYLIB", str(shared)))
    graph[b] = commands(b, ("LC_RPATH", str(second.parent)), ("LC_LOAD_DYLIB", str(shared)))
    graph[shared] = commands(shared, ("LC_LOAD_DYLIB", "@rpath/leaf"))
    graph[first] = commands(first, ("LC_ID_DYLIB", str(first)))
    graph[second] = commands(second, ("LC_ID_DYLIB", str(second)))
    with pytest.raises(NativeError, match="Context-dependent"):
        dependencies.linked_identity(root)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not an object file",
        "Load command 0\ncmd LC_RPATH\n",
        "Load command 0\ncmd LC_LOAD_DYLIB\n",
        "Load command 0\ncmd LC_FUTURE_DYLIB\n",
    ],
)
def test_malformed_tool_output_cannot_be_an_empty_closure(
    tmp_path: Path, graph: dict[Path, str], text: str
) -> None:
    root = file(tmp_path, "program")
    graph[root] = text
    with pytest.raises(NativeError):
        dependencies.linked_identity(root)


def test_file_changed_during_load_command_read_is_rejected(
    tmp_path: Path, graph: dict[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = file(tmp_path, "program")
    graph[root] = commands(root, ("LC_LOAD_DYLIB", "/usr/lib/libSystem.B.dylib"))
    original = dependencies.checked

    def changed(argv: list[str], *, check_cancel: Callable[[], None]) -> str:
        value = original(argv, check_cancel=check_cancel)
        if "-l" in argv:
            root.write_bytes(b"changed")
        return value

    monkeypatch.setattr(dependencies, "checked", changed)
    with pytest.raises(NativeError, match="changed"):
        dependencies.linked_identity(root)


def test_transitive_file_replaced_later_in_traversal_is_rejected(
    tmp_path: Path, graph: dict[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, child = file(tmp_path, "program"), file(tmp_path, "child")
    graph[root] = commands(root, ("LC_LOAD_DYLIB", str(child)))
    graph[child] = commands(child, ("LC_ID_DYLIB", str(child)))
    original = dependencies.checked

    def changed(argv: list[str], *, check_cancel: Callable[[], None]) -> str:
        value = original(argv, check_cancel=check_cancel)
        if str(child) in argv:
            root.write_bytes(b"changed after its first check")
        return value

    monkeypatch.setattr(dependencies, "checked", changed)
    with pytest.raises(NativeError, match="changed"):
        dependencies.linked_identity(root)


def test_owner_cancellation_is_not_wrapped(tmp_path: Path, graph: dict[Path, str]) -> None:
    root = file(tmp_path, "program")
    marker = RuntimeError("owner cancellation")

    def cancel() -> None:
        raise marker

    with pytest.raises(RuntimeError) as caught:
        dependencies.linked_identity(root, check_cancel=cancel)
    assert caught.value is marker


def test_combined_preflight_checks_actual_renderer_without_changing_helper_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper: dict[str, object] = {"controls": "existing complete controls"}
    cairo = tmp_path / "pdftocairo"
    calls: list[Path] = []

    def checked_helper(cache: Path, *, check_cancel: Callable[[], None]) -> dict[str, object]:
        check_cancel()
        assert cache == tmp_path
        return helper

    def renderer(*, check_cancel: Callable[[], None]) -> Path:
        check_cancel()
        return cairo

    def linked(
        path: Path, *, executable_context: Path, check_cancel: Callable[[], None]
    ) -> dict[str, object]:
        check_cancel()
        assert executable_context == (cairo if path == cairo else Path(dependencies.sys.executable))
        calls.append(path)
        return {"root": str(path)}

    monkeypatch.setattr(dependencies, "helper_preflight", checked_helper)
    monkeypatch.setattr(dependencies, "renderer_path", renderer)
    monkeypatch.setattr(dependencies, "linked_identity", linked)
    monkeypatch.setattr(
        dependencies,
        "extension_roots",
        lambda: {"PIL._imaging": tmp_path / "imaging", "pikepdf._core": tmp_path / "core"},
    )
    report = dependencies.preflight(tmp_path)
    assert report["helper"] is helper
    assert calls == [cairo, tmp_path / "imaging", tmp_path / "core"]
    assert report["runtime_resources_verified"] is False


def test_combined_preflight_preserves_renderer_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def helper(cache: Path, *, check_cancel: Callable[[], None]) -> dict[str, object]:
        check_cancel()
        return {}

    monkeypatch.setattr(dependencies, "helper_preflight", helper)
    marker = NativeError("Missing pdftocairo")

    def unavailable(**kwargs: object) -> Path:
        raise marker

    monkeypatch.setattr(dependencies, "renderer_path", unavailable)
    with pytest.raises(NativeError) as caught:
        dependencies.preflight(tmp_path)
    assert caught.value is marker
