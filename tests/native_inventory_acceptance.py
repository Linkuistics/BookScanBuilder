"""Read real retained inventories after PDF loss and store reopen; no fidelity verdict."""

import argparse
import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import cast

from placement_acceptance import construct as construct_placement
from placement_acceptance import shape
from placement_acceptance import truth as placement_truth
from profile_acceptance import NAMES
from profile_acceptance import construct as construct_profile
from sample_acceptance import TRUTH, failures
from sample_acceptance import make_fixture as construct_packed
from sample_acceptance import record as sample_record

from bookscan import (
    intake,
    native_blobs,
    native_inventory_record,
    ownership,
    project_header,
    samples,
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run(directory: Path) -> dict[str, object]:
    directory.mkdir()
    truth: dict[str, object] = {
        "placements": placement_truth(),
        "packed": TRUTH,
        "profiles": NAMES,
        "claim": "Saved full ordered resolution/channel inventories and exact retained blobs.",
        "limitation": (
            "No historical native use, CMM execution, composition fidelity or accepted project."
        ),
        "controls": ["wrong-maximum", "false-completeness", "false-composition", "lost-sample"],
    }
    (directory / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    subjects: list[samples.Inventory] = []
    rows: list[dict[str, object]] = []
    payloads: dict[str, bytes] = {}
    for label, build in (
        ("packed", construct_packed),
        ("profile", construct_profile),
        ("placement", construct_placement),
    ):
        original = directory / (label + ".pdf")
        build(original)
        saved = intake.snapshot(original, directory / (label + "-snapshot.pdf"))
        for index, page in enumerate(saved.pages):
            inventory = samples.collect(saved, page)
            if label == "placement":
                assert shape(inventory.resolution) == placement_truth()[index]
            if label == "packed" and index != 7:
                assert len(inventory.images) == 1
                assert not failures(sample_record(inventory.images[0]), TRUTH[index % 6])
            for sample in inventory.images:
                if sample.packed is not None:
                    payloads[sha(sample.packed)] = sample.packed
                pending = [sample.color]
                while pending:
                    color = pending.pop()
                    if color is not None:
                        for raw in (color.profile, color.palette):
                            if raw is not None:
                                payloads[sha(raw)] = raw
                        pending.append(color.base)
            value = native_inventory_record.record(inventory)
            rows.append(
                {
                    "case": label,
                    "source_pdf_page": page.source_page,
                    "source_sha256": saved.sha256,
                    "inventory": value,
                }
            )
            subjects.append(inventory)
        original.unlink()
        saved.path.unlink()
    project = directory / "project"
    project.mkdir()
    lock = ownership.provision(project)

    def verify(stores: project_header.Stores, value: dict[str, object]) -> None:
        saved = [
            native_blobs.Blob.from_record(v) for v in cast(list[object], value["native_blobs"])
        ]
        by_digest = {ref.sha256: ref for ref in saved}
        for item in cast(list[object], value["inventories"]):
            native_inventory_record.restore(
                item, read_blob=lambda digest: stores.native.read(by_digest[digest])
            )

    with ownership.Writer.acquire(project, lock) as owner:
        stores = project_header.Stores.provision(owner)
        blobs, history = stores.native, stores.checkpoints
        references = {digest: blobs.publish(raw) for digest, raw in payloads.items()}
        state: dict[str, object] = {
            "inventories": [row["inventory"] for row in rows],
            "native_blobs": [ref.record() for _, ref in sorted(references.items())],
        }
        previous = history.commit(
            state, expected=None, verify_state=lambda value: verify(stores, value)
        ).checkpoint
        current = history.commit(
            state, expected=previous, verify_state=lambda value: verify(stores, value)
        ).checkpoint
    controls: list[dict[str, object]] = []

    # No directory identity/reference survives in the read adapter's closure.
    # Resume supplies saved-identity stores; each historical state supplies refs.
    with project_header.resume(project, verify_state=verify) as (loaded, restored_checkpoint):
        assert restored_checkpoint == current
        saved_refs = {
            ref.sha256: ref
            for ref in (
                native_blobs.Blob.from_record(v)
                for v in cast(list[object], restored_checkpoint.state["native_blobs"])
            )
        }

        def read(digest: str) -> bytes:
            return loaded.native.read(saved_refs[digest])

        for index, (row, subject) in enumerate(zip(rows, subjects, strict=True)):
            value = cast(dict[str, object], row["inventory"])
            restored = native_inventory_record.restore(value, read_blob=read)
            assert restored == subject
            refused: list[str] = []
            for name in cast(list[str], truth["controls"]):
                altered = copy.deepcopy(value)
                resolution = cast(dict[str, object], altered["resolution"])
                if name == "wrong-maximum":
                    resolution["maximum_ppi"] = 123456.0
                elif name == "false-completeness":
                    resolution["complete"] = not resolution["complete"]
                elif name == "false-composition":
                    altered["composition_fidelity_verified"] = True
                else:
                    entries = cast(list[object], altered["native_samples"])
                    if entries:
                        entries.pop()
                    else:
                        entries.append({})
                try:
                    native_inventory_record.restore(altered, read_blob=read)
                except native_inventory_record.NativeInventoryRecordError:
                    refused.append(name)
                else:
                    raise AssertionError("Wrong inventory passed: " + name)
            controls.append({"ordinal": index, "refused": refused})
        assert all(read(digest) == raw for digest, raw in payloads.items())
        assert not list(directory.glob("*.pdf"))
    report: dict[str, object] = {
        "format": "BookScanBuilderNativeInventoryAcceptance",
        "version": 1,
        "truth": truth,
        "rows": rows,
        "controls": controls,
        "references": [ref.record() for _, ref in sorted(references.items())],
        "reopened_checkpoint_revision": current.revision,
        "native_identity": {
            "lock": asdict(lock),
            "blobs": asdict(loaded.header.native),
            "checkpoints": asdict(loaded.header.checkpoints),
        },
        "saved_header": loaded.header.record(),
        "restart_identity_source": "project.json; references in each checkpoint",
        "all_pdf_paths_removed": True,
        "composition_fidelity_verified": False,
        "accepted_project_delivered": False,
    }
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.artifacts), indent=2))


if __name__ == "__main__":
    main()
