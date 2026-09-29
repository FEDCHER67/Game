# SCALPEL-ASTRA-001 — design proposal

Status (2026-09-29): concept image completed in the **ordinary FEDCHER ChatGPT chat at High / 3 of 3**, using the approved matte table render as an art-style reference: https://chatgpt.com/g/g-p-6aa6b8a4108c81919e59c95ac93a1145-fedcher/c/6abb8694-2d30-83eb-a9dd-3a9900e250bc . Exact locally saved PNG: `Source/Concept/01_concept.png`, SHA256 `B09C108C68ABF1DC41CAB26A8A2D35BE762FE8498C302A50F34CFA2F8150D24E`. Visually checked full image: one stylized scalpel, matte dark handle, broad grip bars, light curved blade, clear joint, no extra objects. Await the owner's design review. No Tripo generation or credits have been used.

## Role and recommended design

One recognizable, reusable operating scalpel for the stylized low-poly game. Approximate total length 15–16 cm. A straight, flattened No.3-type metal handle, a separate No.10-type curved blade, and a clearly readable junction. The blade remains a separate Blender/Unity mesh so the base asset can later support blade variants or replacement without paying for a second handle model.

- Handle: dark matte graphite, broad simple planes, four or five shallow grip bars. No microscopic knurl, bolts, labels or logo.
- Blade: muted satin silver, broad controlled highlight, readable curved cutting edge. Slight silhouette exaggeration is acceptable at tabletop/game-view distance. Avoid mirror-metal rendering and fantasy proportions.
- One clean 3/4 concept image for design approval; then four consistent front/left/right/back PNGs in ordinary ChatGPT at High for a **separate exact-image approval gate before Tripo credits**.
- Do not infer owner approval from any assistant response in the ordinary chat.

## Manufacturer references (shape and function only)

1. [FEATHER surgical blade and handle catalog](https://www.feather.co.jp/en/m_Products/surgery01.html): No.3 handle and compatible No.10 curved blade. Use the overall shaft/blade relationship and replaceable blade construction, not the brand's exact product image or markings.
2. [Swann-Morton surgical handle No.3](https://www.swann-morton.com/product/123.php): simple reusable flat-handle silhouette and blade fitment. Use as a cross-check of the handle shape.
3. [FEATHER disposable scalpel catalog](https://www.feather.co.jp/en/m_Products/surgery03.html): shape comparison for an integrated disposable alternative. The recommended game asset uses a reusable separate handle/blade instead, because it better supports low-cost variants.

## Workflow and review gates

1. User reviews the concept from the ordinary chat. Revise if needed.
2. Generate four matched views there at High. Save exact PNGs under `Source/TripoViews/` and show all four to the user in that chat. Wait for explicit user approval here before spending Tripo credits.
3. One Tripo Smart Mesh multi-view job if the approved images are consistent and the job price is confirmed. Export raw source to `Working/Tripo/`, clear all four input slots after the model is delivered.
4. Blender cleanup, separate handle/blade meshes, matte materials, FBX export/reimport, renders and visual QA. Send final views to the user's phone and await acceptance. Follow the repository `AGENTS.md` art exception; Unity runtime code, if later requested, uses the normal agent pipeline.

The table caster motion remains under colleague review; this scalpel work does not change it.
