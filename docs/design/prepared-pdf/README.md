# Prepared PDF views

Serve with `task prepare:design-serve`, then open
[the current design](http://127.0.0.1:8769/#discussion).
Use `DESIGN_PORT=PORT` to choose another port. The server exposes only this
presentation directory. The editable sources and generated SVGs stay together.

Dark nodes labelled **Start here** are the reading entry for each workflow
graph; numbered edges show order. These graphs describe contracts rather than
model-checked state machines. The [specification](../../specs/prepared-pdf.md)
holds the complete command and preservation contract.

- [Assembly → Explicit roles become one prepared PDF](http://127.0.0.1:8769/#diagram-assembly) — Defined front/content/back ordering and the one-PDF handoff.
- [Publication → Publish a complete PDF without overwriting](http://127.0.0.1:8769/#diagram-publication) — Defined the private write and no-clobber commit point.

Render using D2 **0.9.0** and `task prepare:design-render`. That recipe uses
Dagre, light theme 0 and dark theme 200. No CDN or browser-side diagram compiler
is needed. Open the affected deep link after regeneration to check readability
and correspondence with the specification.

The viewer is copied from the installed Grove design skill's
`assets/diagram-viewer.html`; it is a standalone static artifact.
