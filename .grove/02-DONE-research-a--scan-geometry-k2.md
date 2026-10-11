# scan-geometry-k2

## Goal

Establish which locally runnable approaches can correct the collection's
within-page scan distortion while preserving visible content, so planning can
choose a small, credible correction trial.

## Context

- `plan-k1` records the user's confirmed requirements and direct observations
  from representative PDFs. The root brief contains the agreed test seams.
- The downstream audience is `book-reconstruction-k3`: it needs to identify
  design/prototype work and the first useful implementation increments.
- Preparation merges covers and content first. The main processor receives one
  assembled PDF and cannot depend on discovering separate files in collection
  folders.

## Done when

- A focused, primary-source survey is recorded at
  `docs/research/scan-geometry-a.md`, structured around the questions below.
- It distinguishes rigid deskew from correction of rotation that changes during
  scanner feed, and distinguishes both from distortion near a bound-book gutter.
- It compares a small set of practical local approaches, including existing
  tools where suitable, with evidence of their assumptions, failure cases and
  current feasibility on this Mac. No method is called proven on this collection
  without an actual trial.
- It recommends the smallest real-page experiment that could disprove its
  preferred approach, using the user's agreed image-fidelity and alignment
  criteria and an already-correct page as a control.
- The planning consumer can identify what is established, what still requires
  visual validation, and what should determine the next prototype/design leaf.

## Notes

Answer these load-bearing questions:

1. Which approaches can correct varying geometry within one page rather than
   estimate a single global angle? Which assumptions differ for cut-up scans
   and for the inspected bound-book spread scans?
2. What goes wrong in real use on music staves, sparse pages, multi-column text,
   code, diagrams, faint printing and colour covers? How can an uncertain change
   be detected for review without degrading a good page?
3. How should a later pipeline keep its OCR text layer aligned with the final
   corrected image, including inputs that may have earlier OCR or corrections?
   Identify constraints and failure cases rather than settling the interface.
4. What minimal dependencies and fixture trial would let the next session judge
   a candidate locally? A global deskew-only pass is the baseline to exceed,
   not evidence that the reported scanner-feed defect has been solved.

Bias the survey toward demonstrated limitations and practical experience, not a
general catalogue of document tools. The collection is at
`/Volumes/Glass/Book Conversion`; use the representative page references in
`plan-k1` to ground the questions and identify a clearly distorted candidate if
the initial samples are too mild. Preserve originals. The survey is evidence
for a later trial, not the full implementation or a commitment to an algorithm.

## Decisions (running log)

The research-a procedure owns the survey filename, so this solo survey uses
`docs/research/scan-geometry-a.md`. It will distinguish directly inspected
inputs, primary-source capabilities, and hypotheses awaiting a real-page trial;
no correction method is selected by this research leaf.

Prefer a two-page falsification trial of Leptonica's vertical-only, per-page
disparity model, because the installed CPU library exposes both geometry and
failure diagnostics without model weights or a GUI build. Use Fundamentals of
Musical Composition PDF page 140 as the distorted candidate and Algorithm Design
PDF page 20 as the apparently straight control. Automatic music-line extraction,
horizontal shape preservation and sampling fidelity are hypotheses to test,
not capabilities established on this collection. The Norwegian spread is a
separate gutter trial, with each book page evaluated independently.

Source inspection found practical traps to carry into planning: full-page PDF
rendering is necessary for the inspected music page's image-plus-stencil content;
Leptonica can return success while copying an unmodelled page, and its native
sampler uses integer source coordinates; page-dewarp 0.3.4 launches locally but
still emits grayscale with binary output disabled. Keep uncertain pages unchanged
and visible for review. These findings inform a prototype rather than an ADR or
an algorithm commitment.
