# LIVER-ASTRA-001 — sources and attribution

## Important archive placement note

The local ZIP archives are in folders named for the opposite authors. This was verified from the ZIP names and contents, and from the Sketchfab model metadata. **The asset follows the authors named in the brief:** Faqihcuk supplies the exterior shape; ElliotSS supplies only the color direction. The original ZIP files were read only and remain unchanged.

## Shape source — Faqihcuk

- **Model:** [Liver Organ](https://sketchfab.com/3d-models/liver-organ-69be472b7a48499e9ab407dfab491e0e) by **Faqihcuk**.
- **License:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/), listed by the Sketchfab model page and model API as “CC Attribution.”
- **Local archive:** `_reference/liver_sources/ElliotSS_HumanLiver/liver-organ.zip` (despite that directory's name).
- **Archive SHA-256:** `D5673BFACBA68B9EAB5A96ED5C0B15E17A6C60CB1C5DD77F43E35C1006849A98`.
- **Used:** `source/LIVER.glb`, exterior liver-body mesh `mesh_id36`, as the direct basis for the broad silhouette, dominant lobe, tapered smaller lobe, and overall mass. The original body topology was replaced by a closed voxel rebuild, relaxed, reduced for game use, centered, and UV unwrapped.
- **Excluded:** all other GLB meshes (`mesh_id56`, `mesh_id54`, `mesh_id67`), donor materials and textures, and their medical protrusions/details. No donor vessels, tubes, ducts, or gallbladder are in the finished scene or FBX.

This is an **adaptation of Faqihcuk's geometry**, not an independently modeled liver. Keep the source attribution with the game and any standalone derivative asset distribution.

## Color reference — ElliotSS

- **Model:** [Human liver and gallbladder](https://sketchfab.com/3d-models/human-liver-and-gallbladder-6c4e9bd0d49f4828b804259330c0c6c4) by **ElliotSS**.
- **License:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), listed by the Sketchfab model API as “CC Attribution.”
- **Local archive:** `_reference/liver_sources/Faqihcuk_LiverOrgan/human-liver-and-gallbladder.zip` (despite that directory's name).
- **Archive SHA-256:** `65925441FC656B0C42DF0ED6DEB739361553805F4299A97E43E159A4BADAC873`.
- **Used:** the broad dark warm red-brown liver color direction from the nested source's `liver texture combined darker for lowres.png`. The final color is a newly set solid Principled BSDF value adjusted for the project's organ family.
- **Excluded:** all ElliotSS geometry, UVs, original material nodes, texture image files, gloss, gallbladder, vena cava, artery, portal vein, and other medical details. No ElliotSS pixels or mesh data occur in the finished `.blend` or FBX.

## Changes and credit to carry forward

The final organ has one closed, simplified game mesh and one solid-color matte material. The silhouette was retained from Faqihcuk while anatomy and fine surface variation were removed. The color was interpreted from ElliotSS, then warmed and softened for the VOLUNTEERS ONLY heart/kidney/brain visual family. Preview lighting and materials were newly authored.

Suggested game credit or accessible attribution-page text:

> Liver shape adapted from “Liver Organ” by Faqihcuk, https://sketchfab.com/3d-models/liver-organ-69be472b7a48499e9ab407dfab491e0e, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Modified: simplified, closed, retopologized, resized, UV unwrapped, and recolored for LIVER-ASTRA-001. Liver color reference: “Human liver and gallbladder” by ElliotSS, https://sketchfab.com/3d-models/human-liver-and-gallbladder-6c4e9bd0d49f4828b804259330c0c6c4, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). No ElliotSS geometry or textures were copied. The source artists do not endorse VOLUNTEERS ONLY.

CC BY 4.0 requires appropriate credit, a license link, an indication of changes, and no implication of endorsement. The attribution above should accompany the game and any distributed derivative asset.
