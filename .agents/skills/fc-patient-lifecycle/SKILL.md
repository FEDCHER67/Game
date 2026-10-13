---
name: fc-patient-lifecycle
description: "Use for patient AI states, capture, loading and unloading, stable identity, movement ownership, save and load, and preventing patient duplication."
---

# Один пациент — одно состояние и один владелец движения

Нужны постоянный PatientId, данные поведения и явный жизненный цикл. Подключение UnityHFSM не создает автоматически сохранение, анимацию или навигацию.

## Работа

Опиши разрешенные переходы Available/Alerted/Fleeing/Captured/Loaded/AtBase/InOperation/Resolved. Реализуй три data presets поведения без трех независимых кодовых систем. Сначала простой HFSM, GOAP только после доказанной потребности.

На каждом переходе явно меняй владельца движения: NavMeshAgent, controlled movement, Rigidbody либо socket. Нельзя одновременно вести загруженного пациента NavMesh и машиной. Повторный запрос погрузки должен быть безопасен; один слот не содержит два разных ID. Визуальный GameObject — представление данных, не единственный источник идентичности.

При выгрузке проверь место, коллизии и валидную навигационную поверхность. При удалении районной сцены сохраняй данные и не создавай копию при повторной активации. Пациент в автомобиле принадлежит persistent-системе транспорта, не выгружаемой территории.

Сохраняй ID, состояние, расположение/слот, этап операции и флаг выдачи результата. Версионируй формат, не полагайся на scene reference или случайное имя GameObject. Повторная доставка события завершения не начисляет вторую награду.

## Приемка

Автотесты допустимых/запрещенных переходов, повторного load/unload и выдачи результата. PlayMode/build: поймать, привезти, выгрузить; сохранить до поимки, в машине, на базе, после операции; перезапустить и проверить уникальность ID. При отсутствие запуска — NOT RUN.

Источники:
https://github.com/Inspiaaa/UnityHFSM
https://docs.unity3d.com/Packages/com.unity.ai.navigation@2.0/manual/index.html
https://docs.unity3d.com/Packages/com.unity.test-framework@1.4/manual/index.html
