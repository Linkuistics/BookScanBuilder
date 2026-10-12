"""Private scope child, with explicit cache construction; -I suppresses Python hooks."""

import ctypes
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import cast


class FileInfoIter(ctypes.Structure):
    # Public 2.18.3 ABI: three opaque pointers, never an internal FcConfig layout.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/fontconfig/fontconfig.h
    _fields_ = [
        ("dummy1", ctypes.c_void_p),
        ("dummy2", ctypes.c_void_p),
        ("dummy3", ctypes.c_void_p),
    ]


def _template_directory(path: str) -> str:
    # The template path is a build setting with no public getter. This supported
    # Mac build's FcInitLoadOwnConfig disassembly names this exact Cellar path.
    # Unknown builds must be verified, not inferred from their version or prefix.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/meson.build
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != (
        "e1f5e06e8339b42f0e1af11cc77979ef6a8f48ffa7588e4dc243e4bd69ea656d"
    ):
        raise ValueError("Unverified Fontconfig build/template directory")
    return "/opt/homebrew/Cellar/fontconfig/2.18.3/share/fontconfig/conf.avail"


def _configuration_path(value: str) -> str:
    # ConfigFiles/FileInfo and GetFilename can retain relative search roots.
    # Freeze that spelling against this captured child's cwd; reject a lexical
    # alias/.. simplification that would identify another filesystem target.
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c
    absolute = os.path.abspath(value)
    if absolute == value:
        return absolute
    if Path(value).resolve(strict=False) != Path(absolute).resolve(strict=False):
        raise ValueError("Configuration path normalization changes its target")
    return absolute


def configured_scope(
    path: str, *, build_cache_root: str | None = None, resolve_configuration: bool = False
) -> dict[str, object]:
    template_directory = _template_directory(path)
    library = ctypes.CDLL(path)
    # Exact 2.18.3 ABI and ownership: returned string lists are finished with Done;
    # config is destroyed once. Parse directly: InitLoadConfig's failure path
    # calls BuildFonts, despite the reference's configuration-only description.
    # https://fontconfig.pages.freedesktop.org/fontconfig/fontconfig-devel/
    # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcinit.c
    library.FcGetVersion.argtypes = []
    library.FcGetVersion.restype = ctypes.c_int
    version = cast(int, library.FcGetVersion())
    if version != 21803:
        raise ValueError("Unsupported Fontconfig version")
    library.FcConfigCreate.argtypes = []
    library.FcConfigCreate.restype = ctypes.c_void_p
    library.FcConfigParseAndLoad.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    library.FcConfigParseAndLoad.restype = ctypes.c_int
    library.FcConfigParseOnly.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    library.FcConfigParseOnly.restype = ctypes.c_int
    library.FcConfigGetSysRoot.argtypes = [ctypes.c_void_p]
    library.FcConfigGetSysRoot.restype = ctypes.c_void_p
    library.FcConfigDestroy.argtypes = [ctypes.c_void_p]
    library.FcConfigDestroy.restype = None
    library.FcStrListNext.argtypes = [ctypes.c_void_p]
    library.FcStrListNext.restype = ctypes.c_void_p
    library.FcStrListDone.argtypes = [ctypes.c_void_p]
    library.FcStrListDone.restype = None
    library.FcStrFree.argtypes = [ctypes.c_void_p]
    library.FcStrFree.restype = None
    library.FcConfigFileInfoIterInit.argtypes = [ctypes.c_void_p, ctypes.POINTER(FileInfoIter)]
    library.FcConfigFileInfoIterInit.restype = None
    library.FcConfigFileInfoIterNext.argtypes = [ctypes.c_void_p, ctypes.POINTER(FileInfoIter)]
    library.FcConfigFileInfoIterNext.restype = ctypes.c_int
    library.FcConfigFileInfoIterGet.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(FileInfoIter),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    library.FcConfigFileInfoIterGet.restype = ctypes.c_int
    config = cast(int | None, library.FcConfigCreate())
    if not config:
        raise ValueError("Fontconfig configuration unavailable")
    result: dict[str, object] = {
        "schema": "BookScanBuilderFontconfigScope",
        "version": 3,
        "fontconfig_version": version,
    }
    try:
        if resolve_configuration:
            # Filename(NULL) references the global config and can build fonts.
            # This exact verified build exports GetFilename(config, name); pass
            # our empty config so selection never enters global initialization.
            # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c
            library.FcConfigGetFilename.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            library.FcConfigGetFilename.restype = ctypes.c_void_p
            selected = cast(int | None, library.FcConfigGetFilename(config, None))
            if not selected:
                raise ValueError("Fontconfig configuration selection unavailable")
            try:
                name = _configuration_path(os.fsdecode(ctypes.string_at(selected)))
            finally:
                library.FcStrFree(selected)
            if not os.path.isabs(name):
                raise ValueError("Fontconfig configuration selection is not absolute")
            return {
                "schema": "BookScanBuilderFontconfigSelection",
                "version": 1,
                "fontconfig_version": version,
                "configuration_file": name,
            }
        # Null filename selects the default, including FONTCONFIG_FILE/PATH.
        # No Init/BuildFonts/fallback or cache initialization is invoked.
        # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcxml.c
        if not library.FcConfigParseAndLoad(config, None, 1):
            raise ValueError("Fontconfig configuration parse failed")
        # Mirror the successful initializer's optional scan-only pass. It reads
        # templates without enabling their rules or invoking Init/BuildFonts.
        # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcinit.c
        if not library.FcConfigParseOnly(config, os.fsencode(template_directory), 0):
            raise ValueError("Fontconfig template scan failed")
        sysroot = cast(int | None, library.FcConfigGetSysRoot(config))
        root = os.fsdecode(ctypes.string_at(sysroot)) if sysroot else None
        # FcConfigGetFilename avoids adding a sysroot already prefixing the path.
        # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c
        effective = (
            os.path.join(root, template_directory.lstrip("/"))
            if root and not template_directory.startswith(root)
            else template_directory
        )
        result["template_dirs"] = [effective]
        iterator = FileInfoIter()
        library.FcConfigFileInfoIterInit(config, ctypes.byref(iterator))
        parsed: set[str] = set()
        while True:
            name = ctypes.c_void_p()
            # Get allocates the filename; descriptions would invoke gettext.
            # Request neither descriptions nor enabled-state data and free names.
            # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccfg.c
            present = library.FcConfigFileInfoIterGet(
                config, ctypes.byref(iterator), ctypes.byref(name), None, None
            )
            try:
                if not present:
                    break
                if not name.value:
                    raise ValueError("Fontconfig parsed filename unavailable")
                parsed.add(_configuration_path(os.fsdecode(ctypes.string_at(name.value))))
            finally:
                if name.value:
                    library.FcStrFree(name)
            if not library.FcConfigFileInfoIterNext(config, ctypes.byref(iterator)):
                raise ValueError("Fontconfig parsed-file iterator failed")
        result["parsed_files"] = sorted(parsed)
        for field, name in (
            ("config_files", "FcConfigGetConfigFiles"),
            ("config_dirs", "FcConfigGetConfigDirs"),
            ("font_dirs", "FcConfigGetFontDirs"),
            ("cache_dirs", "FcConfigGetCacheDirs"),
        ):
            getter = getattr(library, name)
            getter.argtypes = [ctypes.c_void_p]
            getter.restype = ctypes.c_void_p
            strings = cast(int | None, getter(config))
            if not strings:
                raise ValueError("Fontconfig string list unavailable")
            paths: list[str] = []
            try:
                while pointer := cast(int | None, library.FcStrListNext(strings)):
                    name = os.fsdecode(ctypes.string_at(pointer))
                    paths.append(
                        _configuration_path(name)
                        if field in {"config_files", "config_dirs"}
                        else name
                    )
            finally:
                library.FcStrListDone(strings)
            result[field] = sorted(set(paths))
            if field in {"font_dirs", "cache_dirs"}:
                # Getters report logical paths. Scan/cache I/O always prepends
                # sysroot, even if that string already prefixes the logical path.
                # Configuration paths above instead use GetFilename's rule.
                # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcdir.c
                # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fccache.c
                result["effective_" + field] = sorted(
                    {os.path.join(root, path.lstrip("/")) if root else path for path in paths}
                )
        if build_cache_root is not None:
            owned = Path(build_cache_root).resolve(strict=True)
            caches = cast(list[str], result["effective_cache_dirs"])
            if not caches or any(Path(name).resolve(strict=True) != owned for name in caches):
                raise ValueError("Cache construction requires the reserved effective root")
            # Explicit opt-in only, after direct successful parsing (no fallback).
            # Build the same configuration we checked, rather than reloading it.
            # https://github.com/fontconfig/fontconfig/blob/2.18.3/src/fcinit.c
            library.FcConfigBuildFonts.argtypes = [ctypes.c_void_p]
            library.FcConfigBuildFonts.restype = ctypes.c_int
            if not library.FcConfigBuildFonts(config):
                raise ValueError("Fontconfig cache construction failed")
    finally:
        library.FcConfigDestroy(config)
    return result


def main() -> int:
    try:
        build_root = None
        selection = len(sys.argv) == 3 and sys.argv[2] == "--resolve-configuration"
        if len(sys.argv) == 4 and sys.argv[2] == "--build-cache" and os.path.isabs(sys.argv[3]):
            build_root = sys.argv[3]
        elif len(sys.argv) != 2 and not selection:
            raise ValueError("Expected native library and optional owned cache root")
        if not os.path.isabs(sys.argv[1]):
            raise ValueError("Expected an absolute native library path")
        result = configured_scope(
            sys.argv[1], build_cache_root=build_root, resolve_configuration=selection
        )
    except (OSError, ValueError, AttributeError, RuntimeError):
        # No native diagnostic or environment data escapes the private protocol.
        print("Fontconfig configured-scope discovery failed", file=sys.stderr)
        return 5
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
