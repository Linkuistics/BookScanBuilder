# Packet directory publication (baseline-finite-k63, milestone 3 mechanism)

`src/bookscan/packet_publication.py` builds a packet in a private directory beside
its unused destination and makes it visible with one exclusive rename.

## Observed native mechanism (macOS 27.0, arm64, Python 3.12/3.15 ctypes)

`renameatx_np(AT_FDCWD or dirfd, src, dirfd, dst, RENAME_EXCL=0x4)` through libc:

| Case | Result |
| --- | --- |
| source directory -> absent name | 0, directory moved atomically |
| -> existing directory | -1 `EEXIST` (nothing changed) |
| -> existing file | -1 `EEXIST` |
| -> dangling symlink | -1 `EEXIST` |
| FAT32 disk image (`hdiutil` MS-DOS), fresh / occupied | 0 / `EEXIST`: flag supported there too |
| source renamed onto **itself** with `RENAME_EXCL` | **0 (a no-op success)** |

The last row is why the capability probe renames the stage onto a *different*
existing private name and requires `EEXIST`; a self-rename probe would report
"supported" on any filesystem. `os.rename` is never used: it replaces an empty
destination directory. No filesystem lacking the flag was available to construct,
so unsupported publication (5) is exercised only through a substituted rename;
the real observation is the probe itself, which fails closed if `EEXIST` is not
returned.

## Checks

- `task process:packet-publication-check`: 18 real-filesystem cases (publish,
  empty/occupied/file/dangling/symlink destination, missing/file parent, symlinked
  parent, unsupported at probe/publish, replacing rename distrusted, stage cleanup,
  foreign entry retained, uncaptured contents never adopted, published packet
  survives later failure, two concurrent publishers have one winner).
- `mutate.py` (run from the repository root) applies five single-edit mutations to
  the module, runs the suite after each and restores the original, asserting its
  SHA-256. Observed: flags 0 fails nine cases; dropping the early occupied check
  fails four; dropping the probe fails two; dropping mode widening fails one;
  late `published` flag fails three. Original digest after restoration:
  `1c8d72fafda85fc41dd0511bd8444e50da6a7c83898659c235e4db30239248df`.

Scope: this is the publication primitive only. Packet content, descriptors,
receipts, the views/status-output commands and the installed packet pre/post-
publication writer barriers remain unfinished F work.
