"""Discover Fontconfig scopes and explicitly construct an owned import cache."""

from __future__ import annotations

import os
import re
import shutil
import stat
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import cast
from xml.parsers import expat
from xml.sax.saxutils import escape, quoteattr

from bookscan.dependencies import linked_identity
from bookscan.native_setup import digest, execute
from bookscan.owned_tree import OwnedTree
from bookscan.resources import ResourceBinding
from bookscan.skew import NativeError, json_object

FIELDS = (
    "config_files",
    "config_dirs",
    "font_dirs",
    "cache_dirs",
    "template_dirs",
    "parsed_files",
    "effective_font_dirs",
    "effective_cache_dirs",
)
LIMITATION = (
    "Fontconfig 2.18.3 configured scopes only, not the renderer's actual file opens or matches. "
    "Fresh configuration-only rediscovery and the verified build's scan-only template tree "
    "guard loaded/parsed inputs; complete candidate enumeration, Poppler CMaps/profiles, "
    "native codecs and "
    "transient restored changes remain unverified. Discovery itself builds no font "
    "database/cache; no glyph-fidelity claim."
)


@dataclass(frozen=True)
class ConfiguredScope:
    config_files: tuple[str, ...]
    config_dirs: tuple[str, ...]
    font_dirs: tuple[str, ...]
    cache_dirs: tuple[str, ...]
    template_dirs: tuple[str, ...]
    parsed_files: tuple[str, ...]
    effective_font_dirs: tuple[str, ...]
    effective_cache_dirs: tuple[str, ...]


@dataclass(frozen=True)
class FontconfigDiscovery:
    scope: ConfiguredScope
    binding: ResourceBinding
    linked: dict[str, object]
    cache_construction: dict[str, object] | None = None
    resource_snapshot: dict[str, object] | None = None

    def record(self) -> dict[str, object]:
        result: dict[str, object] = {
            "fontconfig_version": "2.18.3",
            "scope": asdict(self.scope),
            "binding": self.binding.record(),
            "linked": self.linked,
            "runtime_resources_verified": False,
            "limitation": LIMITATION,
        }
        if self.cache_construction is not None:
            result["cache_construction"] = self.cache_construction
        if self.resource_snapshot is not None:
            result["resource_snapshot"] = self.resource_snapshot
        return result


def _scope(text: str) -> ConfiguredScope:
    data = json_object(text)
    if (
        set(data) != {"schema", "version", "fontconfig_version", *FIELDS}
        or data["schema"] != "BookScanBuilderFontconfigScope"
        or type(data["version"]) is not int
        or data["version"] != 3
        or type(data["fontconfig_version"]) is not int
        or data["fontconfig_version"] != 21803
    ):
        raise NativeError("Unsupported Fontconfig discovery protocol/version.")
    values: list[tuple[str, ...]] = []
    for field in FIELDS:
        paths = data[field]
        if not isinstance(paths, list):
            raise NativeError(f"Incomplete Fontconfig {field} scope.")
        checked: set[str] = set()
        for path in cast(list[object], paths):
            if not isinstance(path, str) or "\x00" in path or not Path(path).is_absolute():
                raise NativeError(f"Invalid Fontconfig {field} path.")
            checked.add(path)
        values.append(tuple(sorted(checked)))
    if not values[0]:
        raise NativeError("No known configuration files; Fontconfig discovery is incomplete.")
    if not values[3] or not values[7]:
        raise NativeError(
            "No configured cache roots; automatic Fontconfig cache fallback unverified."
        )
    if len(values[4]) != 1 or not values[5]:
        raise NativeError("Incomplete Fontconfig template/parsed-file scope.")
    if values[2] and not values[6]:
        raise NativeError("Incomplete Fontconfig effective font-directory scope.")
    return ConfiguredScope(*values)


def _probe(
    library: Path, seed: ResourceBinding, check_cancel: Callable[[], None]
) -> ConfiguredScope:
    seed.verify(check_cancel=check_cancel)
    result = execute(
        # Isolated interpreter: no ambient Python module search or startup hooks.
        # https://docs.python.org/3.12/using/cmdline.html#cmdoption-I
        [sys.executable, "-I", str(Path(__file__).with_name("fontconfig_probe.py")), str(library)],
        environment=seed.environment(),
        directory=seed.directory,
        check_cancel=check_cancel,
    )
    if result.returncode or result.stderr.strip():
        # FcInitLoadConfig can fall back after a bad file: never silently accept
        # parser diagnostics, nor serialize native debug/environment contents.
        raise NativeError("Fontconfig configuration probe failed or reported diagnostics.")
    scope = _scope(result.stdout)
    seed.verify(check_cancel=check_cancel)
    return scope


@dataclass(frozen=True, kw_only=True)
class FontconfigBinding(ResourceBinding):
    """Bind reported trees and recheck configuration resolution for each native use."""

    library: Path
    _scope: ConfiguredScope

    @classmethod
    def guard(
        cls, subjects: ResourceBinding, library: Path, scope: ConfiguredScope
    ) -> FontconfigBinding:
        return cls(
            files=subjects.files,
            _environment=subjects._environment,
            directory=subjects.directory,
            _directory_identity=subjects._directory_identity,
            directories=subjects.directories,
            library=library,
            _scope=scope,
        )

    def verify(self, *, check_cancel: Callable[[], None] = lambda: None) -> None:
        # Use the plain bound subjects in the child probe to avoid recursively
        # invoking this rediscovery. Immutable fields retain the same identities.
        subjects = ResourceBinding(
            self.files,
            self._environment,
            self.directory,
            self._directory_identity,
            self.directories,
        )
        # 2.18.3 _FcConfigParse omits a missing optional include from configFiles.
        # Reparse before/after a render, under the captured child context, rather
        # than accepting unchanged known files as complete configuration currency.
        # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
        if _probe(self.library, subjects, check_cancel) != self._scope:
            raise NativeError("Fontconfig configured scope changed since discovery.")

    def record(self) -> dict[str, object]:
        result = super().record()
        result["fontconfig_scope_guard"] = {
            "version": 3,
            "scope": asdict(self._scope),
            "verification": "fresh-configuration-only-rediscovery",
            "limitation": LIMITATION,
        }
        return result


def discover_fontconfig(
    renderer: Path,
    *,
    environment: Mapping[str, str] | None = None,
    check_cancel: Callable[[], None] = lambda: None,
) -> FontconfigDiscovery:
    """Discover reported configured roots, bind them, then verify rediscovery.

    Native enumeration is isolated in a reaped child. This is a private import
    seam; no public route, accepted asset, runtime build or complete-use claim.
    """
    check_cancel()
    captured = dict(os.environ if environment is None else environment)
    linked = linked_identity(renderer, check_cancel=check_cancel)
    files = linked.get("files")
    if not isinstance(files, dict) or not files:
        raise NativeError("Incomplete renderer native-file discovery.")
    native: list[Path] = []
    for name in cast(dict[object, object], files):
        if not isinstance(name, str) or not Path(name).is_absolute():
            raise NativeError("Invalid renderer native-file identity.")
        native.append(Path(name))
    libraries = [
        path for path in native if re.fullmatch(r"libfontconfig(?:\.[0-9]+)*\.dylib", path.name)
    ]
    if len(libraries) != 1:
        raise NativeError("Renderer must have one verified Fontconfig library.")
    probe = Path(__file__).with_name("fontconfig_probe.py")
    native.extend([probe, Path(sys.executable)])
    seed = ResourceBinding.capture(native, environment=captured, check_cancel=check_cancel)
    scope = _probe(libraries[0], seed, check_cancel)
    # The actual 2.18.3 list includes parsed <include> directories too.
    # Bind those as complete trees; treating every entry as a file rejects
    # the ordinary default configuration, while omitting them misses growth.
    config_dirs: list[Path] = []
    config_files: list[Path] = []
    for name in scope.config_files:
        check_cancel()
        path = Path(name)
        (config_dirs if path.is_dir() else config_files).append(path)
    binding = ResourceBinding.capture(
        [*native, *config_files, *(Path(path) for path in scope.parsed_files)],
        directories=config_dirs,
        optional_directories=[
            Path(path)
            for path in (
                *scope.config_dirs,
                *scope.effective_font_dirs,
                *scope.effective_cache_dirs,
                *scope.template_dirs,
            )
        ],
        environment=captured,
        check_cancel=check_cancel,
    )
    if binding.directory != seed.directory or _probe(libraries[0], binding, check_cancel) != scope:
        raise NativeError("Fontconfig configured scope changed during discovery.")
    seed.verify(check_cancel=check_cancel)
    binding.verify(check_cancel=check_cancel)
    guarded = FontconfigBinding.guard(binding, libraries[0], scope)
    return FontconfigDiscovery(scope, guarded, linked)


def _cache_identity(root: Path, expected: tuple[int, int]) -> None:
    try:
        value = root.lstat()
    except OSError as error:
        raise NativeError(f"Cannot verify private Fontconfig cache reservation: {error}") from error
    if not stat.S_ISDIR(value.st_mode) or (value.st_dev, value.st_ino) != expected:
        raise NativeError(
            "Private Fontconfig cache reservation was replaced; leaving it untouched."
        )


def _cache_inputs(found: FontconfigDiscovery, root: Path) -> ResourceBinding:
    # Only the effective I/O roots may be writable. Logical getter values can
    # differ under sysroot. Do not exempt an overlapping font/config/template tree.
    scope = found.scope
    if not scope.effective_cache_dirs or any(
        Path(name).resolve(strict=False) != root for name in scope.effective_cache_dirs
    ):
        raise NativeError("Fontconfig cache roots must name only the new private reservation.")
    for name in (
        *scope.config_files,
        *scope.config_dirs,
        *scope.parsed_files,
        *scope.template_dirs,
        *scope.effective_font_dirs,
    ):
        path = Path(name).resolve(strict=False)
        if path.is_relative_to(root) or root.is_relative_to(path):
            raise NativeError("Fontconfig cache overlaps a configuration/font/template input.")
    binding = found.binding
    return replace(
        binding,
        directories=tuple(
            item for item in binding.directories if Path(item.path).resolve(strict=False) != root
        ),
    )


def _reserve_cache(cache_directory: Path) -> tuple[Path, tuple[int, int]]:
    try:
        root = cache_directory.parent.resolve(strict=True) / cache_directory.name
        root.mkdir(mode=0o700)
        identity = root.lstat()
    except (OSError, RuntimeError) as error:
        raise NativeError(f"Cannot reserve unused private Fontconfig cache: {error}") from error
    return root, (identity.st_dev, identity.st_ino)


def _cleanup_owned(tree: OwnedTree, label: str) -> None:
    try:
        tree.remove()
    except NativeError as error:
        raise NativeError(f"Cannot remove owned {label}: {error}") from error


@contextmanager
def _build_cache(
    renderer: Path,
    root: Path,
    expected: tuple[int, int],
    tree: OwnedTree,
    *,
    environment: Mapping[str, str] | None,
    check_cancel: Callable[[], None],
) -> Iterator[FontconfigDiscovery]:
    """Build into an already reserved root; the caller owns cleanup of ``tree``.

    ``tree`` must cover ``root``. It is captured only after this process's own
    reservation and again once the native build child is completed and reaped.
    """
    captured = dict(os.environ if environment is None else environment)
    cold = discover_fontconfig(renderer, environment=captured, check_cancel=check_cancel)
    inputs = _cache_inputs(cold, root)
    if not isinstance(cold.binding, FontconfigBinding):
        raise NativeError("Fontconfig discovery did not provide a scope guard.")
    cold.binding.verify(check_cancel=check_cancel)
    _cache_identity(root, expected)
    if any(root.iterdir()):
        raise NativeError("Configuration-only discovery changed the new private cache.")
    command = [
        sys.executable,
        "-I",
        str(Path(__file__).with_name("fontconfig_probe.py")),
        str(cold.binding.library),
        "--build-cache",
        str(root),
    ]
    try:
        result = execute(
            command,
            environment=inputs.environment(),
            directory=inputs.directory,
            check_cancel=check_cancel,
        )
    finally:
        # execute reaps its child on every exit, so the root's names now come only
        # from this owned child (the root was verified empty before launch).
        try:
            tree.capture()
        except NativeError as failure:
            selected = sys.exception()
            if selected is None:
                raise
            selected.add_note(str(failure))
    if result.returncode or result.stderr.strip() or _scope(result.stdout) != cold.scope:
        raise NativeError("Private Fontconfig cache construction failed or scope changed.")
    _cache_identity(root, expected)
    inputs.verify(check_cancel=check_cancel)
    warm = discover_fontconfig(renderer, environment=captured, check_cancel=check_cancel)
    if warm.scope != cold.scope:
        raise NativeError("Fontconfig configuration changed during cache construction.")
    inputs.verify(check_cancel=check_cancel)
    warm.binding.verify(check_cancel=check_cancel)
    yield FontconfigDiscovery(
        warm.scope,
        warm.binding,
        warm.linked,
        {
            "method": "FcConfigBuildFonts",
            "initially_empty": True,
            "cache_root": str(root),
            "command": command,
            "inputs": inputs.record(),
        },
    )
    warm.binding.verify(check_cancel=check_cancel)


@contextmanager
def prepared_fontconfig_cache(
    renderer: Path,
    cache_directory: Path,
    *,
    environment: Mapping[str, str] | None = None,
    check_cancel: Callable[[], None] = lambda: None,
    owner: OwnedTree | None = None,
) -> Iterator[FontconfigDiscovery]:
    """Build only a new owned cache, then bind it immutably for the import lifetime.

    The caller supplies a configuration whose effective cache roots all name this
    unused directory. This does not rewrite ordinary configuration or copy fonts.
    All other discovered subjects stay fixed during construction. No compilation,
    public route or accepted project is introduced. Exit removes only the exact
    entries captured when the native build was reaped; any changed, replaced or
    unknown entry retains the whole root. The caller must retain the record with
    pixels before ending the context. An ``owner`` tree already covering this
    directory's parent keeps the cache inside its single all-or-nothing cleanup.
    """
    check_cancel()
    root, expected = _reserve_cache(cache_directory)
    if owner is not None:
        owner.capture()  # our own reservation of the nested cache root
        with _build_cache(
            renderer,
            root,
            expected,
            owner,
            environment=environment,
            check_cancel=check_cancel,
        ) as found:
            yield found
        return
    try:
        tree = OwnedTree(root)
    except NativeError as failure:
        raise NativeError(f"Cannot own the new private Fontconfig cache: {failure}") from failure
    try:
        with _build_cache(
            renderer,
            root,
            expected,
            tree,
            environment=environment,
            check_cancel=check_cancel,
        ) as found:
            yield found
    except BaseException as error:
        # Cleanup must not replace the caller's selected cancellation/error.
        try:
            _cleanup_owned(tree, "private Fontconfig cache")
        except NativeError as failure:
            error.add_note(str(failure))
        raise
    else:
        _cleanup_owned(tree, "private Fontconfig cache")


SNAPSHOT_CACHE = "/bookscan-private-font-cache"

# Compile-time FONTCONFIG_PATH of the checksum-verified Mac build in
# fontconfig_probe._template_directory, also exposed as pkg-config confdir.
# https://github.com/fontconfig/fontconfig/blob/2.18.3/meson.build
DEFAULT_CONFIG_DIRECTORY = "/opt/homebrew/etc/fonts"


def _snapshot_path(root: Path, name: str) -> Path:
    path = Path(name)
    if not path.is_absolute() or ".." in path.parts:
        raise NativeError("Cannot mirror a noncanonical Fontconfig input path.")
    return root / name.lstrip("/")


def _snapshot_overlap(found: FontconfigDiscovery, root: Path) -> None:
    for name in (
        *found.scope.config_files,
        *found.scope.config_dirs,
        *found.scope.parsed_files,
        *found.scope.effective_font_dirs,
        *found.scope.effective_cache_dirs,
        *found.scope.template_dirs,
    ):
        path = Path(name).resolve(strict=False)
        if path.is_relative_to(root) or root.is_relative_to(path):
            raise NativeError("Fontconfig snapshot overlaps an original resource input.")


def _loaded_files(scope: ConfiguredScope) -> set[str]:
    # Scan-only built-in templates remain host-bound dependencies. A template
    # explicitly included in config_files is loaded configuration and is copied.
    return set(scope.config_files) | {
        name
        for name in scope.parsed_files
        if not any(Path(name).is_relative_to(Path(tree)) for tree in scope.template_dirs)
    }


def _font_paths(
    value: str, prefix: str | None, found: FontconfigDiscovery, configuration_file: Path
) -> tuple[str, ...]:
    # Exact 2.18.3 Unix rules: XDG expands home AND data dirs, relative uses
    # realpath(parse->name), cwd/default stay relative to captured child cwd;
    # FcStrCopyFilename expands '~' by concatenation, not user lookup.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcstr.c
    environment = found.binding.environment()
    home = environment.get("HOME", "")
    if not value or prefix not in {None, "cwd", "default", "relative", "xdg"}:
        raise NativeError("Unsupported Fontconfig font path/prefix.")
    if prefix == "xdg":
        data_home = environment.get("XDG_DATA_HOME", home + "/.local/share")
        data_dirs = environment.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
        parents = [data_home, *(p for p in data_dirs.split(":") if p)]
        values = [parent + "/" + value for parent in parents]
    elif prefix == "relative":
        values = [str(configuration_file.resolve(strict=True).parent) + "/" + value]
    else:
        values = [value]
    paths: list[str] = []
    for path in values:
        if path.startswith("~"):
            if "HOME" not in environment:
                raise NativeError("Fontconfig home-relative path lacks a captured home.")
            path = home + path[1:]
        if not Path(path).is_absolute():
            path = str(found.binding.directory) + "/" + path
        path = os.path.normpath(path)
        if path not in found.scope.font_dirs:
            raise NativeError("Expanded Fontconfig font path is outside the bound native scope.")
        if path not in paths:
            paths.append(path)
    return tuple(paths)


def _include_path(value: str, directory: Path) -> str:
    spelling = value if Path(value).is_absolute() else str(directory) + "/" + value
    normalized = os.path.normpath(spelling)
    if spelling != normalized:
        try:
            if Path(spelling).resolve(strict=False) != Path(normalized).resolve(strict=False):
                raise NativeError("Fontconfig include path normalization changes its target.")
        except (OSError, RuntimeError) as error:
            raise NativeError("Cannot verify Fontconfig include path normalization.") from error
    return normalized


def _include_search_roots(environment: Mapping[str, str], directory: Path) -> tuple[str, ...]:
    # FcConfigGetPath searches FONTCONFIG_PATH in order, then the build default.
    # An interior empty segment is ""; FcConfigFileExists joins it as /name.
    # The final empty segment is not visited. Relative roots use captured cwd.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c
    configured = environment.get("FONTCONFIG_PATH", "")
    parents = configured.split(":") if configured else []
    if configured.endswith(":"):
        parents.pop()
    parents.append(DEFAULT_CONFIG_DIRECTORY)
    return tuple(_include_path(parent, directory) if parent else "/" for parent in parents)


def _search_include(value: str, found: FontconfigDiscovery) -> str:
    candidates: list[str] = []
    for parent in _include_search_roots(found.binding.environment(), found.binding.directory):
        path = _include_path(parent + "/" + value, found.binding.directory)
        candidates.append(path)
        try:
            Path(path).lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise NativeError("Cannot verify Fontconfig include search candidate.") from error
        # Native resolution skips unreadable/dangling targets. The snapshot
        # refuses those dependencies instead of claiming absence.
        if not os.access(path, os.R_OK):
            raise NativeError("Fontconfig include search candidate is unreadable or dangling.")
        if path not in _loaded_files(found.scope):
            raise NativeError("Selected Fontconfig include lacks a bound loaded destination.")
        return path
    # No root selected an input. Preserve an optional boundary at the first
    # private mirrored candidate; the caller still verifies explicit optionality.
    return candidates[0]


def _redirect_paths(
    raw: bytes, found: FontconfigDiscovery, root: Path, configuration_file: Path
) -> bytes:
    # Fontconfig uses Expat without namespace processing: actual 48-guessfamily
    # templates contain xsi:nil without a namespace declaration. Preserve the
    # original bytes outside replaced path elements, including DTD/comments.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
    # https://docs.python.org/3.12/library/pyexpat.html#xml.parsers.expat.ParserCreate
    if b"\x00" in raw:
        raise NativeError("Non-UTF8 Fontconfig snapshot is unsupported.")
    parser = expat.ParserCreate()
    patches: list[tuple[int, int, bytes]] = []
    start: tuple[int, str, dict[str, str]] | None = None
    content: list[str] = []
    level = 0

    def begin(name: str, attributes: dict[str, str]) -> None:
        nonlocal start, level
        if level == 0 and name != "fontconfig":
            raise NativeError("Copied Fontconfig input has an unsupported root.")
        if start is not None:
            # Native children have separate string buffers; flattening their
            # text into the parent's path would select a different input.
            # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
            raise NativeError("Nested Fontconfig path content is unsupported.")
        if name in {"cachedir", "dir", "remap-dir", "include"}:
            if level != 1 or start is not None:
                raise NativeError("Nested Fontconfig path configuration is unsupported.")
            start = (parser.CurrentByteIndex, name, attributes)
            content.clear()
        level += 1

    def text(value: str) -> None:
        if start is not None:
            content.append(value)

    def end(name: str) -> None:
        nonlocal start, level
        level -= 1
        if name not in {"cachedir", "dir", "remap-dir", "include"}:
            return
        if start is None:
            raise NativeError("Copied Fontconfig path element lacks a start.")
        first, _, attributes = start
        if name == "cachedir":
            targets = [_snapshot_path(root, SNAPSHOT_CACHE)]
            attributes = {}
        else:
            # FcCharacterData retains boundary whitespace as filename data.
            # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
            value = "".join(content)
            prefix = attributes.get("prefix")
            if name in {"dir", "remap-dir"}:
                # remap-dir expands the physical directory just like dir. Its
                # as-path/salt identify the cache, not another font-read tree;
                # keep that logical key and rule order while copying the input.
                # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
                # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccache.c
                if name == "remap-dir" and "as-path" not in attributes:
                    raise NativeError("Fontconfig remap lacks its logical cache path.")
                targets = [
                    _snapshot_path(root, path)
                    for path in _font_paths(value, prefix, found, configuration_file)
                ]
            else:
                if not value:
                    raise NativeError("Empty Fontconfig include selection is unsupported.")
                if prefix == "xdg":
                    # Include uses XDG_CONFIG_HOME alone, unlike the multi-root
                    # font-dir expansion. It appends even a leading slash.
                    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
                    environment = found.binding.environment()
                    parent = environment.get(
                        "XDG_CONFIG_HOME", environment.get("HOME", "") + "/.config"
                    )
                    value = os.path.normpath(parent + "/" + value)
                    if not Path(value).is_absolute():
                        value = os.path.normpath(str(found.binding.directory) + "/" + value)
                # Only xdg changes native include resolution. Unlike dir,
                # relative uses the ordinary captured configuration search.
                # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
                elif prefix not in {None, "cwd", "default", "relative"}:
                    raise NativeError("Fontconfig include prefix requires verified copy semantics.")
                elif value.startswith("~"):
                    # FcConfigGetFilename uses FcConfigFileExists(HOME, suffix):
                    # insert a separator even for ~name; do not use dir expansion.
                    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c
                    environment = found.binding.environment()
                    if "HOME" not in environment:
                        raise NativeError("Fontconfig home include lacks a captured home.")
                    value = os.path.normpath(environment["HOME"] + "/" + value[1:])
                    if not Path(value).is_absolute():
                        value = os.path.normpath(str(found.binding.directory) + "/" + value)
                elif not Path(value).is_absolute():
                    value = _search_include(value, found)
                if value not in _loaded_files(found.scope):
                    # _FcConfigParse omits absent optional includes. Retain
                    # the include boundary, but confine its absent path to
                    # the copy. Existing/unbound or dangling inputs refuse.
                    # FcNameBool tests initial bytes; DontCare is nonzero.
                    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcname.c
                    optional = attributes.get("ignore_missing", "").lower()
                    ignored = optional[:1] in {"t", "y", "1", "d", "x", "2"} or (
                        optional[:2] in {"on", "or"}
                    )
                    try:
                        Path(value).lstat()
                    except FileNotFoundError:
                        if not ignored:
                            raise NativeError(
                                "Required Fontconfig include lacks a loaded destination."
                            ) from None
                    except OSError as error:
                        raise NativeError("Cannot verify absent Fontconfig include.") from error
                    else:
                        raise NativeError("Fontconfig include lacks a bound loaded destination.")
                targets = [_snapshot_path(root, value)]
            attributes = {key: value for key, value in attributes.items() if key != "prefix"}
        offset = parser.CurrentByteIndex
        stop = (
            raw.index(b">", offset) + 1
            if raw.startswith(("</" + name).encode(), offset)
            else offset
        )
        attrs = "".join(" " + key + "=" + quoteattr(value) for key, value in attributes.items())
        replacement = b"".join(
            ("<" + name + attrs + ">" + escape(str(target)) + "</" + name + ">").encode()
            for target in targets
        )
        patches.append((first, stop, replacement))
        start = None

    def entity(*args: object) -> None:
        raise NativeError("Entity-dependent Fontconfig snapshots are unsupported.")

    parser.StartElementHandler = begin
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text
    parser.EntityDeclHandler = entity
    try:
        parser.Parse(raw, True)
    except expat.ExpatError as error:
        raise NativeError("Cannot parse a copied Fontconfig input.") from error
    for first, last, replacement in reversed(patches):
        raw = raw[:first] + replacement + raw[last:]
    return raw


def copy_fontconfig_inputs(
    found: FontconfigDiscovery,
    root: Path,
    *,
    check_cancel: Callable[[], None] = lambda: None,
) -> None:
    """Mirror bound input spellings as independent bytes; redirect supported paths.

    This private import operation requires an owned empty directory. It deliberately
    redirects captured XDG/realpath-relative/cwd/home font paths and loaded XDG
    and home/search-path includes, retaining genuinely absent optional targets privately.
    Bound remap directories preserve their logical cache path, salt and order.
    Dangling candidates retain their names and missing targets inside the copy.
    Entity-dependent configuration remains unsupported.
    It copies no native library and makes no complete runtime-resource claim.
    """
    found.binding.verify(check_cancel=check_cancel)
    root = root.resolve(strict=True)
    _snapshot_overlap(found, root)
    if any(root.iterdir()):
        raise NativeError("Fontconfig snapshot directory must initially be empty.")
    input_trees = {
        *found.scope.config_dirs,
        *found.scope.effective_font_dirs,
        *(name for name in found.scope.config_files if Path(name).is_dir()),
    }
    if input_trees - {tree.path for tree in found.binding.directories}:
        raise NativeError("Fontconfig input tree lacks a complete resource binding.")
    files: dict[str, str] = {}
    absent_links: dict[str, str] = {}
    directories: set[str] = set()
    for tree in found.binding.directories:
        if tree.path not in input_trees:
            continue
        if tree.entries is None:
            continue  # Absent optional inputs remain absent in the private copy.
        for item in tree.entries:
            check_cancel()
            if item.kind == "directory":
                directories.add(item.path)
            elif item.kind == "file" and item.sha256 is not None:
                files[item.path] = item.sha256
            elif item.kind == "dangling-symlink":
                absent_links[item.path] = item.resolved
            else:
                raise NativeError("Cannot snapshot an unsupported Fontconfig resource entry.")
    for name in _loaded_files(found.scope) - input_trees:
        candidates = [item for item in found.binding.files if item.path == name]
        if len(candidates) != 1 or candidates[0].sha256 is None:
            raise NativeError("Fontconfig configuration file lacks a bound byte identity.")
        files[name] = candidates[0].sha256
    for name in sorted(directories, key=lambda name: (len(Path(name).parts), name)):
        check_cancel()
        _snapshot_path(root, name).mkdir(mode=0o700, parents=True, exist_ok=True)
    for name, expected in sorted(files.items()):
        check_cancel()
        target = _snapshot_path(root, name)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Dereference aliases into owned bytes, never leave a route back to host
        # resources. Independently bind the copied digest before rewriting XML.
        shutil.copyfile(name, target)
        target.chmod(0o600)
        if digest(target, check_cancel=check_cancel) != expected:
            raise NativeError("Fontconfig input changed while making its private copy.")
    for name, missing in sorted(absent_links.items()):
        check_cancel()
        target = _snapshot_path(root, missing)
        if target.exists() or target.is_symlink():
            raise NativeError("Missing Fontconfig target became present in its private copy.")
        link = _snapshot_path(root, name)
        link.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Native scans every name; preserve absence without a route to host.
        # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcdir.c
        link.symlink_to(target)
    for name in _loaded_files(found.scope) - input_trees:
        check_cancel()
        target = _snapshot_path(root, name)
        target.write_bytes(_redirect_paths(target.read_bytes(), found, root, Path(name)))
    found.binding.verify(check_cancel=check_cancel)


def _snapshot_scope(original: ConfiguredScope, copied: ConfiguredScope, root: Path) -> None:
    for field in ("config_files", "config_dirs"):
        expected = {_snapshot_path(root, name) for name in getattr(original, field)}
        actual = {Path(name) for name in getattr(copied, field)}
        if actual != expected:
            raise NativeError("Copied Fontconfig configuration scope does not match its source.")
    expected_parsed = {
        str(_snapshot_path(root, name)) if name in _loaded_files(original) else name
        for name in original.parsed_files
    }
    if (
        set(copied.parsed_files) != expected_parsed
        or copied.template_dirs != original.template_dirs
    ):
        raise NativeError("Copied Fontconfig parsed/template scope does not match its source.")
    expected_fonts = {str(_snapshot_path(root, name)) for name in original.effective_font_dirs}
    if set(copied.font_dirs) != expected_fonts or set(copied.effective_font_dirs) != expected_fonts:
        raise NativeError("Copied Fontconfig font scope does not match its source.")
    expected_cache = (str(_snapshot_path(root, SNAPSHOT_CACHE)),)
    if copied.cache_dirs != expected_cache or copied.effective_cache_dirs != expected_cache:
        raise NativeError("Copied Fontconfig cache routes are not confined to the private root.")


def selected_configuration(found: FontconfigDiscovery, check_cancel: Callable[[], None]) -> Path:
    """Resolve captured native selection without initializing a font database."""
    binding = found.binding
    if not isinstance(binding, FontconfigBinding):
        raise NativeError("Fontconfig selection requires a verified native scope guard.")
    binding.verify(check_cancel=check_cancel)
    result = execute(
        [
            sys.executable,
            "-I",
            str(Path(__file__).with_name("fontconfig_probe.py")),
            str(binding.library),
            "--resolve-configuration",
        ],
        environment=binding.environment(),
        directory=binding.directory,
        check_cancel=check_cancel,
    )
    if result.returncode or result.stderr.strip():
        raise NativeError("Fontconfig configuration selection failed or reported diagnostics.")
    data = json_object(result.stdout)
    name = data.get("configuration_file")
    if (
        set(data) != {"schema", "version", "fontconfig_version", "configuration_file"}
        or data["schema"] != "BookScanBuilderFontconfigSelection"
        or type(data["version"]) is not int
        or data["version"] != 1
        or type(data["fontconfig_version"]) is not int
        or data["fontconfig_version"] != 21803
        or not isinstance(name, str)
        or "\x00" in name
        or not Path(name).is_absolute()
        or name not in found.scope.config_files
        or name not in {item.path for item in binding.files}
    ):
        raise NativeError("Fontconfig selection lacks a supported bound loaded configuration.")
    binding.verify(check_cancel=check_cancel)
    return Path(name)


@contextmanager
def prepared_fontconfig_snapshot(
    renderer: Path,
    directory: Path,
    configuration_file: Path | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    check_cancel: Callable[[], None] = lambda: None,
) -> Iterator[FontconfigDiscovery]:
    """Own copied selected configuration/fonts and its completed cache for import.

    Original selected configuration/fonts are needed through copying/verification.
    Native libraries and scan-only installed templates remain bound host dependencies.
    Omitted configuration uses captured native selection, including FILE/PATH.
    Unsupported path forms still fail; this is not durable project publication.
    """
    check_cancel()
    captured = dict(os.environ if environment is None else environment)
    if captured.get("FONTCONFIG_SYSROOT"):
        raise NativeError("Nested Fontconfig sysroot snapshotting is not supported.")
    if configuration_file is not None:
        captured["FONTCONFIG_FILE"] = str(configuration_file.absolute())
    original = discover_fontconfig(renderer, environment=captured, check_cancel=check_cancel)
    config = (
        selected_configuration(original, check_cancel)
        if configuration_file is None
        else configuration_file.absolute()
    )
    if str(config) not in original.scope.config_files:
        raise NativeError("Selected configuration is absent from the loaded Fontconfig inputs.")
    try:
        root = directory.parent.resolve(strict=True) / directory.name
        _snapshot_overlap(original, root)
        root.mkdir(mode=0o700)
        metadata = root.lstat()
    except (OSError, RuntimeError) as error:
        raise NativeError(f"Cannot reserve unused Fontconfig snapshot: {error}") from error
    expected = (metadata.st_dev, metadata.st_ino)
    try:
        tree = OwnedTree(root)
    except NativeError as failure:
        raise NativeError(f"Cannot own the new Fontconfig snapshot: {failure}") from failure

    try:
        try:
            copy_fontconfig_inputs(original, root, check_cancel=check_cancel)
        finally:
            # Our own synchronous copy writes, including a partial copy on failure.
            tree.capture()
        # FC_FILE emitted by a sysroot scan is still a logical host path. Cairo
        # opens it directly; use physical copied paths in configuration instead.
        # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcdir.c
        copied_environment = dict(captured, FONTCONFIG_FILE=str(_snapshot_path(root, str(config))))
        copied_environment.pop("FONTCONFIG_SYSROOT", None)
        if "FONTCONFIG_PATH" in captured:
            copied_environment["FONTCONFIG_PATH"] = os.pathsep.join(
                str(_snapshot_path(root, path))
                for path in _include_search_roots(captured, original.binding.directory)
            )
        copied = discover_fontconfig(
            renderer, environment=copied_environment, check_cancel=check_cancel
        )
        _snapshot_scope(original.scope, copied.scope, root)
        original.binding.verify(check_cancel=check_cancel)
        with prepared_fontconfig_cache(
            renderer,
            _snapshot_path(root, SNAPSHOT_CACHE),
            environment=copied_environment,
            check_cancel=check_cancel,
            owner=tree,
        ) as warm:
            _snapshot_scope(original.scope, warm.scope, root)
            _cache_identity(root, expected)
            yield replace(
                warm,
                resource_snapshot={
                    "method": "copied-path-cache-redirect",
                    "configuration_file": str(config),
                    "selection": "explicit"
                    if configuration_file is not None
                    else "captured-fontconfig",
                    "root": str(root),
                    "original": original.record(),
                    "runtime_resources_verified": False,
                    "limitation": (
                        "Supported selected configuration/font copy; native libraries/templates "
                        "stay host-bound. "
                        "No independent glyph truth."
                    ),
                },
            )
            _cache_identity(root, expected)
    except BaseException as error:
        try:
            _cleanup_owned(tree, "Fontconfig snapshot")
        except NativeError as failure:
            error.add_note(str(failure))
        raise
    else:
        _cleanup_owned(tree, "Fontconfig snapshot")
