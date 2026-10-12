"""Actual child imports/codec/profile operations; no calibrated colour or font truth."""

import hashlib
import io
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pikepdf
from PIL import Image, ImageCms, _imagingcms, _imagingft

import bookscan.render

raw = bytes([255, 0, 0, 255, 255, 255, 0, 0, 0])
image = Image.frombytes("RGB", (3, 1), raw)
encoded = io.BytesIO()
image.save(encoded, format="PNG")
with Image.open(io.BytesIO(encoded.getvalue())) as decoded:
    assert decoded.tobytes() == raw
# The untyped native CmsProfile is normalized through the documented wrapper.
# https://raw.githubusercontent.com/python-pillow/Pillow/12.3.0/src/PIL/ImageCms.py
factory = cast(Callable[[str], object], getattr(ImageCms, "createProfile"))
wrapper = cast(Callable[[object], ImageCms.ImageCmsProfile], ImageCms.ImageCmsProfile)
profile = wrapper(factory("sRGB"))
transformed = ImageCms.profileToProfile(image, profile, profile, outputMode="RGB")
assert transformed is not None
assert transformed.tobytes() == raw  # Identity smoke, never independent ICC fidelity.
pdf = pikepdf.Pdf.new()
pdf.add_blank_page(page_size=(72, 36))
serialized = io.BytesIO()
pdf.save(serialized)
with pikepdf.Pdf.open(io.BytesIO(serialized.getvalue())) as reopened:
    assert len(reopened.pages) == 1
modules: dict[str, dict[str, str]] = {}
for name, module in sorted(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if filename is not None and Path(filename).is_file():
        path = Path(filename).resolve(strict=True)
        modules[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
print(
    json.dumps(
        {
            "rgb_sha256": hashlib.sha256(raw).hexdigest(),
            "modules": modules,
            "native_extensions": [_imagingcms.__name__, _imagingft.__name__],
            "product_path": str(Path(bookscan.render.__file__).resolve()),
            "complete_runtime_resources_verified": False,
        },
        sort_keys=True,
    )
)
