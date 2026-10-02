# SYRINGE-ASTRA-001 — Tripo handoff

Project root: `C:\Dev\Game-main`
Tripo Studio: https://studio.tripo3d.ai/ru/workspace/generate/pink-brain-model-with-smooth-lobed-surface-03c2acf3-9205-4400-85a2-7bc10b7e9739

## Input images

Put four approved views of the same syringe in `Source\TripoViews\`:

| Tripo Studio slot | File |
| --- | --- |
| Спереди (front) | `01_front.png` |
| Слева (left) | `02_left.png` |
| Справа (right) | `03_right.png` |
| Обратная сторона (back) | `04_back.png` |

Tripo Studio accepts JPG, PNG and WEBP, up to 20 MB per file in the current UI. The four numbered PNG files were uploaded to the corresponding slots on 2026-09-29.

## Tripo output

Save the downloaded source model and any files included with its export under `Working\Tripo\`. Name the base FBX `syringe_tripo_base.fbx` when that format is available. Leave the original reference images intact. Blender and Unity work should use this exported base as input and place later deliverables elsewhere in this asset folder.

## Current state

The four-view syringe model was generated on 2026-09-29 in the user's authenticated Chrome session with **Умная сетка**, quad topology, a 5,000 polygon target, one generation, and AI model P2.0. Tripo charged **100 tokens** (balance 1895 → 1795). The resulting mesh reports **4,812 faces and 4,955 vertices**. It was exported as Blender-oriented FBX to `Working\Tripo\syringe_tripo_base.fbx` (192,160 bytes; SHA-256 `27730BC9042B9C8F48DBBD41AD2C288C270414C32A7C9820FFD284BAB1B8FF41`). Blender 5.2.1 imported the FBX successfully and confirmed a 4,812-face mesh.

## Generation settings in Tripo Studio

1. Open the **Модель** section and select **Умная сетка**.
2. Select **Многоракурсное изображение в 3D** (the four separate view slots). Do not use the adjacent batch upload mode.
3. Fill the labeled slots from the corresponding files above. Match each label, rather than relying on a generic file picker order.
4. In **Общие настройки → Топология**, select **Четырехугольник**. Set **Количество полигонов** to **5,000** for this relatively simple, smooth syringe base; the UI currently allows 500–25,000. Increase only if the generated body loses its silhouette.
5. Set **Количество генераций** to **1** and **AI Модель** to **P2.0**.
6. Confirm the **Создать** button displays **100** Tripo tokens before launching. If the price or requested options differ, stop and check the settings.
7. Wait for completion, inspect the generated model, export an FBX when available, and place the complete download under `Working\Tripo\`. Record the model page URL and exact chosen polygon count here after the run.

The settings, 100-token charge, completed mesh, and FBX export were verified in the authenticated Tripo session on 2026-09-29.

## Blender review handoff

After the exported base has been colored and prepared by Codex, Codex must save its final `.blend` and run `C:\Dev\Game-main\tools\Show-AssetForReview.ps1 -BlendPath <absolute path> -AssetName 'Syringe'`. This opens the final file in Blender and plays the project's completion alarm. Use the same handoff step for each subsequent asset. Do not notify before the saved file exists and has been checked.
