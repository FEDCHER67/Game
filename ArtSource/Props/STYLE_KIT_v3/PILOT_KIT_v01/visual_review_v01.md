# G16 — Visual review v01

Inspected on 13 October 2026: the final 1280 x 1280 lineup, all four group compositions (1280 x 1000), and the earlier group review renders. This records the worker's inspection, not the project owners' artistic approval.

## Result

- **PASS — completeness:** all 37 modules are represented on the labelled lineup. Both rural window sizes and both garage-door variants are present. Ground-scale boxes in the group views are 1.75 m tall.
- **PASS — Hamlet forms:** scarecrow has the cross support, sack head, unequal coat sleeves/hem and broad patch; mailbox has a post and flag; cart has two wheels, plank bed and draw shaft. Tractor has three tires, a bare front-right axle and support block. Woodpile has stacked cut logs and a roof. Shed and barn have visible wall/roof gaps. Both bale shapes read distinctly.
- **PASS — facade depth:** windows show projecting wooden jambs, sill and broad carved crown, with glass behind the trim. Door uses the true wall recess recorded in validation; the standalone render cannot demonstrate a host-wall cut. Porch has three steps, clear platform, side rails and a roof carried by two front posts.
- **PASS — plots and yards:** gates show separate open leaves and included posts; fence faces, garden border, well shaft/crank and outhouse remain readable. Retaining edges have continuous flat caps. Bare T-poles follow the no-laundry-lines art rule.
- **PASS — Rough District:** ribbed garage doors have distinct closed/ajar silhouettes. The enclosure has an open front; bench seat/back and concrete legs read clearly. Basement geometry is shown raised as a cutaway so its below-ground portion is visible. External stairs show tread/rail/landing structure and an open upper exit.
- **PASS — palette and surface treatment:** muted wood, olive, slate-blue metal, neutral concrete, sand-coloured hay and rust fills; no photo grime, vertex jitter, fine grain or texture noise. Saved PNG swatches match target sRGB values within 0.5/255 quantization (maximum measured error 0.0019607843).

## Changes made during pre-export review

The first group layout placed smaller props behind the barn and crowded the left edge. The second layout orders items by height and centres the camera on the projected bounds. These are preview composition changes only. Both reviews are retained under `Review/`; no deliverable was overwritten. An early woodpile exceeded its 1,200-triangle budget; simplifying its decorative end discs reduced it to 1,116 triangles before export. A double-gate post transform was corrected before export.

## Limits and remaining checks

The lineup fits each item separately; compare real size in the group views and README table. Long module labels are easiest to read on the lineup. The kit uses deliberately simple silhouettes and broad carving; it does not attempt finely carved rural ornament, splinter noise or realistic decay. The shed and barn share a modular broken-roof language.

No Unity session, game-camera inspection, traversal test, van test, runtime material check or performance profile was run. Blender validation establishes geometry and exported data consistency; it does not establish movement-controller behaviour or owner acceptance of the candidate v07 palette.
