---
name: fc-performance-and-playtests
description: "Use for profiling this Unity open-world prototype, checking assets, automated and manual tests, save-load regressions, builds and evidence-based optimization."
---

# Измерение вместо слова «оптимизировано»

Прочитай PerformanceBudget, EnvironmentReport и предыдущие измерения. Цель 60 FPS/около 16,7 мс — предложение, не гарантия для 5070 Ti. CPU и целевая слабая машина не заданы. Не выдумывай baseline и показатели.

## Работа

Три одинаково повторяемых сценария: пешком в наполненном дворе; поездка с пациентом и переходами районов; операция на базе. Запиши build, hardware, разрешение, quality, длительность. По доступным средствам измеряй frame time, median/p95, пики, CPU/GPU time, allocations и память. Не называй Graphy полноценным GPU-профилированием.

Начинай с Unity Profiler/Memory Profiler. AssetUsageDetector помогает исследовать ссылки, но не разрешает удалять динамически загружаемые ассеты. RenderDoc — для конкретного вопроса к рендерингу. Не устанавливай инструменты ради списка.

Проверь материалы, прозрачность, тени, skinning, физику, Update, создание объектов, GC и поток загрузки. Далекие NPC не должны полностью симулироваться постоянно. Измени одно подтвержденное узкое место, повтори одинаковый тест, сравни изображение и корректность игры. Сохраняй оригиналы моделей и безопасный откат.

## Приемка

Автотесты состояний, операций, повторных событий и save/load; PlayMode для движения/погрузки; реальный запуск build для перезапуска и потоковой загрузки. Пустая Console не означает успешный playtest.

TestReport разделяет PASS, FAIL, NOT RUN, BLOCKED, указывает лог и способ проверки. Build должен иметь путь и результат реального запуска. Если среда не поддерживает графический/звуковой тест, честно оставь его невыполненным, сохрани доступную работу и NextAction. Не обещай фонового продолжения.

Источники:
https://docs.unity3d.com/Packages/com.unity.test-framework@1.4/manual/index.html
https://docs.unity3d.com/Packages/com.unity.memoryprofiler@1.1/manual/index.html
https://github.com/yasirkula/UnityAssetUsageDetector
https://github.com/baldurk/renderdoc
