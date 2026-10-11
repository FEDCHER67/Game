# BAT-ASTRA-001 — reference provenance

2026-10-05. Images made using the normal image generator in ordinary ChatGPT «Федя чат»:
https://chatgpt.com/g/g-p-6aadbaaa21c081918dcf9006013794cd-only-volunteers/c/6aadbae4-9db8-83eb-b549-cced1b1c33b2

FRONT is the design anchor; opposite camera views are requested through the selected-image editor, retaining silhouette, scale, background and lighting. Download original PNGs through the visible viewer Download button and preserve byte-identical copies. No local crop, resize, mirror or repaint.

Four separate1254×1254 PNGs completed in Rev01. Each hash matches its downloaded source exactly; Source/reference_manifest_Rev01.json contains full identities. Browser screenshots Source/chatgpt_front_Rev01_proof.png and chatgpt_back_Rev01_proof.png show the original images in ChatGPT's image viewer.

## Генерация и исходный файл

Rev01 утверждён Claude от имени Феди 05.10.2026: силуэт, обмотка и положение сколов согласованы. Одна разрешённая генерация: Smart Mesh, quads, P2.0, target 500, Create ровно 100. Баланс 580 → 480. Модель Tripo: https://studio.tripo3d.ai/ru/workspace/generate/wooden-baseball-bat-with-black-wrapped-grip-e9e6d389-11d3-464d-8ccc-1f1b761f5ca1

Доказательства: `Source/tripo_settings_create100.png`, `tripo_settings_create100_AX.txt`, `tripo_result_balance480.png`, `tripo_export_fbx.png`, `tripo_slots_cleared.png`. После генерации все четыре слота очищены.

Исходный скачанный `bat_astra_001_tripo_base.fbx` скопирован без изменений в `C:/Dev/Game/Working/Tripo/bat_tripo_base.fbx`: 34320 байт; SHA256 `16824B685F0F8A2298CD185584599E86482622F9089BB784BE5ECF2103338BE8`.

## Локальная доводка

Blender 5.2.1 LTS: исходная сетка 1092 треугольника, 32 незамкнутых ребра, UV отсутствуют. Вместо сохранения дефектных швов выполнена локальная ретопология по силуэту исходной модели: 15 кольцевых сечений, 16 сегментов, 476 треугольников. Удалённых платных операций не было. Исходник сохранён скрытым в отдельной коллекции Blender и исключён из экспорта.

Дерево, витки изоленты и два неглубоких скола созданы локальным материалом и запечены в атлас 1024×1024. Референсные PNG не редактировались. Сколы не добавляют геометрии. `Scripts/polish_v01.py` воспроизводит доводку; `Scripts/validate_export_v01.py` независимо проверяет экспорт. Итоговые файлы и превью имеют номер v01. Готовая v01 принята здесь Claude от имени Феди 05.10.2026: 476 треугольников, замкнутая сетка, PASS, баланс 480.
