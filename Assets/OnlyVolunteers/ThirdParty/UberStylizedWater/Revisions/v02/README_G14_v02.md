# Uber Stylized Water — OnlyVolunteers v02

G14b effects + G14c muted palette, 2026-10-11. MIT derivative; see LICENSE and SOURCE_MANIFEST_v02.json.

Полный отчёт, таблицы параметров, настройка URP, стоимость и известные ограничения: `docs/art/G14_WATER_v02.md` в корне проекта.

Пять готовых материалов: `Assets/OnlyVolunteers/Art/StyleKit_v3/Materials/M3_Water_*_v02.mat`.

Меню теста: **OnlyVolunteers/Art/Build Water Test Scene**. Запускает лид в Unity; здесь редактор не запускался. Проверить новый shader при импорте и затем вид/движение в тестовой сцене.

**В карту автоматически не включено.** Для ревью Claude использует `ArtSource/Textures/StyleKit_v3/candidate_water/water_entries_v02.json`. Активный v05 и оригиналы/v01 не изменены.

Shader: `OnlyVolunteers/Uber Stylized Water v02`, один forward pass. Основные режимы: Surface, Waterfall, FoamSplash. Depth Texture обязательна поверхности/контактной пене; Opaque Texture нужна преломлению. Ни SSR, ни дополнительных камер.
