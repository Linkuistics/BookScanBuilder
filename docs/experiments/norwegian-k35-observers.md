# k35 blind addressing observations

Three fresh contexts received only the public packet and A/B/C grid PNGs under
`/private/tmp/bookscan-norwegian-k35-controls-final`. Each was instructed to hash
all four inputs before viewing, view every grid at original detail, identify the
single darkest source cell independently, report closed plausible x/y index
intervals and native/spread addresses, then hash after. The supplied protocol
states 32×16 native cells at 16× nearest-neighbour scale, axes starting at zero,
x right/y down; add the patch half-origin, then spread origin. Every context
excluded repository source, answer keys, historical notes, automatic arrays,
other observers and prior coordinates. No context wrote files or ran VCS.
These are addressing observations, not artifact reviews or real-baseline marks.
Parent graph provenance was supplied without source-coordinate evidence.

## Left initial observer — /root/left_observer

Verbatim observation report:

> Blind controls readings complete: A offset [6,3], intervals x[6,6] y[3,3], half/spread [321,183]; B [19,7], x[19,19] y[7,7], half/spread [974,1197]; C [29,13], x[29,29] y[13,13], half [239,2253], spread [2024,2253]. High visual confidence in each; counted labelled cells from zero, compared visible grey cells. All 4 before/after digests identical. Will return full maps and remain available for subsequent source assignment.

Verbatim method from final:

> Method: independently viewed each grid at original detail, visually compared shaded cells, and counted cell indices using the labelled axes beginning at zero. Confidence high for each; no visible tie or addressing ambiguity. These are synthetic controls, not baseline calibration.

## Right initial observer — /root/right_observer

Verbatim observation report:

> Blind controls complete, only four authorized files accessed. A reading offset[6,3], plausible x[6,6] y[3,3], half[321,183], spread[321,183]. B offset[18,8], plausible x[18,18] y[8,8], half[973,1198], spread[973,1198]. C offset[28,4], plausible x[28,28] y[4,4], half[238,2244], spread[2023,2244]. Each viewed original separately; visual comparison of grey cells plus grid count. High confidence address, darkest cells visually distinguishable from adjacent slightly lighter diagonals. Exact digest maps follow in next message; waiting for source assignment.

## Independent verification/repeat observer — /root/verifier_observer

Verbatim observation report:

> Blind independent verification observer readings complete: A offset [6,3], plausible x[6,6] y[3,3], half-native [321,183], spread [321,183]; B [17,11], x[17,17] y[11,11], half-native [972,1201], spread [972,1201]; C [26,8], x[26,26] y[8,8], half-native [236,2248], spread [2021,2248]. Every image viewed detail=original after SHA256 of all four allowed inputs; after hashes identical. Only those inputs accessed. Full maps and method in final.

Verbatim method from final:

> Read each grid independently with `view_image(detail=original)`. Counted labelled cells from index 0, x right/y down, and selected the visually darkest source cell. No address ambiguity observed.

## Observation provenance

All three separately reported these exact maps for both before and after:

| Input | SHA-256 |
| --- | --- |
| packet.json | 43db97772dc2a36c746b7ce2b92a732a3209bef6ea37971f25c96a23527cf078 |
| A-grid.png | 96358286122cc8d191072991fd72fff04d79d73051cd9b724a89c02a035d7809 |
| B-grid.png | 1d5238d751a17cf5b4750ec31d2786a70c51435aeab93e0d4afed9352da9f810 |
| C-grid.png | 9a212fd058b88e526aa936fc2e51d1a6d06f5ba881242c1e22b4e4d0e4e410be |

The retained [packet](norwegian-k35-controls/packet.json), ordinary PNGs and
supervisory [answer key](norwegian-k35-controls/answer-key.json) preserve what
was shown and its reference positions. The answer key was not supplied to any
observer. Their reported absence of ambiguity is not an error bound: every
joint x/y interval misses its known target. These findings stop both halves
before real marks under the predeclared falsifier. No true cell was revealed
for a second attempt, and no grid/scale/holdout was tuned to rescue this run.
