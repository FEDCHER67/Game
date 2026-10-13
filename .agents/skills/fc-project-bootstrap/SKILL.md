---
name: fc-project-bootstrap
description: "Use for bootstrapping this Unity patient-catching open-world game, auditing dependencies, connecting an existing Claude or Codex client, and verifying editor access."
---

# Безопасная рабочая база

Сначала прочитай UNITY_FIELD_CLINIC_PROMPT.md, существующие AGENTS.md/CLAUDE.md и Docs/EnvironmentReport.md, если они есть. Не подменяй существующие проектные инструкции содержимым стороннего README.

## Работа

Определи, где выполняешься: домашняя машина, удаленная среда с репозиторием или чат без исполнения. Проверь доступные файлы и редакторы, а не предполагаемую установку. Прочитай Unity ProjectVersion/Packages, render pipeline, текущие ошибки, Git status и настройки клиента. Не меняй существующую версию Unity без отдельного решения.

Для нового проекта исходное предложение — стабильный Unity 6.3 LTS/URP; точный патч и доступность сверяются с Unity releases. Не устанавливай preview, новые агенты, локальные модели или платные API. Разрешен минимальный editor bridge для уже работающего клиента. Один активный канал управления Unity: официальный plugin/CLI или подходящий Unity MCP.

Каталог ресурсов классифицируй целиком, но скачивай только выбранное на текущем этапе. Прочитай LICENSE и package metadata; исходные ассеты проверь отдельно. Зафиксируй тег, commit SHA или checksum. Старые демо помести вне Assets и испытай отдельно. Добавляй зависимости по одной с проверкой Console. Не исполняй install scripts вслепую и не открывай MCP наружу.

## Выход и проверка

EnvironmentReport, DependencyDecisions, dependencies.lock.json и ThirdPartyNotices. Для каждой установки — путь, версия, назначение, результат проверки и откат. Editor-тест: создать отдельный временный объект, прочитать его обратно, убрать только его. Без редактора — BLOCKED, а не PASS. Не переключай ветки с чужими незакоммиченными изменениями, не удаляй их.

Источники:
https://github.com/Unity-Technologies/unity-agent-plugin
https://github.com/CoplayDev/unity-mcp
https://github.com/ahujasid/mcp-for-blender
https://unity.com/releases/unity-6
