# Page and book geometry discussion

Design v2 is agreed: the human replied **“agreed”** to the presented geometry-only
design and preserved-scale alignment. Review clarifications expose the fixed
300-dpi MediaBox RGB import's fidelity/extent costs and define existing
coordinate, parity, disposition, dependency and report/server contracts.
Reordering and OCR remain external.
The current contract and public/visual seams are
[Page and book geometry](../../specs/rotation-processor.md). This agreement does
not accept a working product or unresolved within-page geometry.

Serve this directory with `task process:design-serve DESIGN_PORT=8770` and open
[the current discussion](http://127.0.0.1:8770/#discussion). Graphs use a dark
“Start here” entry and numbered sequential edges. These are workflow and
registration-dependency views, not physical scale drawings or checked models.

- [Agreement → Geometry-only Design v2](http://127.0.0.1:8770/contract.html#agreement) — Recorded the actual “agreed” reply and its design/test-seam scope, without attributing output inspection or acceptance.
- [Book geometry → Page sides and mirrored alignment](http://127.0.0.1:8770/#diagram-book-alignment) — Settled scale preservation; placement uses translation/padding and never mirrors page images.

Reviewed discussion: [workflow](http://127.0.0.1:8770/#diagram-workflow),
[page/group review](http://127.0.0.1:8770/#diagram-review) and
[saved geometry dependencies](http://127.0.0.1:8770/#diagram-versions).

D2 0.9.0/Dagre, theme 0/dark theme 200, produces the adjacent self-contained SVGs
with `task process:design-render`. That recipe also renders the canonical spec
as contract.html and refreshes served reference copies. Edit Markdown/D2 sources,
not generated copies. SVG-only views need no CDN. This documentation viewer is
not the proposed working review UI. The removed OCR experiment has no current
product role; existing frozen preparation/geometry evidence remains unchanged.
