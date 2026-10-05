# Inventory — подключение (на одобрение Вадиму)

Модуль ничего не меняет в `Player/` и `Network/`. Чтобы подключить его, нужно отредактировать префабы и ассеты (не скрипты). Эти шаги делает Вадим или кто-то с его согласия.

## 1. Префаб игрока `Network/Prefabs/NetworkPlayer.prefab`

Добавить на корень (там же, где `NetworkObject` и `NetworkPlayer`):

| Компонент | Поля |
| --- | --- |
| `NetworkInventory` | `database` = `Inventory/Items/ItemDatabase`; `slotCount` 6 (1–8); `capacity` 12; `reach` 2.5; **`reachOrigin` = трансформ KCC-мотора (вложенный ExampleCharacter)**: корень префаба на сервере не двигается вместе с игроком, а камера чужих игроков на сервере не обновляется. |
| `InventoryInput` | `inventory` и `viewCamera` (`FirstPersonCamera`) найдутся сами, если не заданы. |
| `InventoryHud` | `inventory` найдётся сам. Канвас создаётся только у владельца. |

`NetworkInventory` — это `NetworkBehaviour` на существующем `NetworkObject`; FishNet должен перезапечь префаб (Rebuild при сохранении).

## 2. Предметы в мире

- Префаб предмета: `NetworkObject` + `WorldItem` (`definition`, `initialCount`, `initialUnitValue`; 0 = базовая цена) + коллайдер (можно триггер).
- Префаб нужно добавить в `DefaultPrefabObjects` и указать в `ItemDefinition.worldPrefab`, иначе предмет нельзя выбросить: сервер откажет, и предмет не пропадёт.
- В примерах `worldPrefab` пустой: готовых сетевых префабов органов пока нет.
- Сетевой скальпель — это `NetworkPhysicsBody`. Если повесить на него `WorldItem`, его можно будет поднять, пока его кто-то тащит. Проверки на это нет: модуль не видит код `Network/`. Нужен либо отдельный префаб, либо проверка на стороне Вадима.

## 3. События и API

Клиент (владелец):
- `NetworkInventory.Changed`: изменились слоты, выбор или наличные. На хосте срабатывает и для серверной копии.
- `SlotCount`, `GetSlot(i)`, `SelectedIndex` (выбор предсказывается локально), `Cash`.

Сервер:
- `ServerPickedUp(ItemStack)`, `ServerDropped(ItemStack, WorldItem)`, `ServerArrested(ArrestResult)`.
- `ServerTryAdd(definition, count, unitValue)` — например, органы после операции.
- `ServerTakeFromSlot(slot, count)` — продажа.
- `ServerAddCash` / `ServerTrySpendCash`.
- `ServerMostValuableItem()`, `ServerApplyArrestPenalty(10)` — для полиции.
- `ServerModel` — `InventoryModel` целиком.

Видимость: слоты и наличные видит только владелец (`ReadPermission.OwnerOnly`). Номер выбранного слота видят все — пригодится, чтобы потом показывать предмет в руке.

## 4. Конфликты ввода

- Модуль использует собственные `InputAction` (Input System), без `InputSystem_Actions.inputactions`. Active Input Handling = Both, так что работает рядом со старым `Input` в `KccFirstPersonInput`/`NetworkGrabber`.
- Пересечений по клавишам E/G/1–8/колесо в сцене NetworkTest нет. В VanDriveTest цифры 1–4 и 7–9 заняты дверями и апгрейдами, но инвентаря там нет.
- Когда открыта панель NetworkSession, курсор свободен, и ввод инвентаря выключается.

## 5. Открытые решения

- Что происходит с предметами при отключении игрока. Сейчас они исчезают вместе с ним.
- Что даёт выбранный слот: предмет в руке, его модель и использование. Пока выбор влияет только на «выбросить».
- Делать ли наличные физическим предметом (в ArtSource есть проп cash). Сейчас это число.
- Реальные цены, размеры, шкала качества органов и иконки.

## 6. Что не проверено (Unity в облаке не запускался)

- Компиляция в Unity 6000.5.11f1 и разрешение ссылок asmdef по именам (`FishNet.Runtime`, `Unity.InputSystem`, `UnityEngine.UI`). Код собран только против заглушек этих API.
- Кодоген FishNet 4.7.3 для `SyncList<ItemStack>` с ручным сериализатором `ItemStackSerializers` из соседней сборки, и `SyncTypeSettings(ReadPermission.OwnerOnly)`. Сверено по исходникам FishNet 4.7.3, но не запускалось.
- Значения `SyncVar`, заданные между `Instantiate` и `Spawn` (`WorldItem.ServerSetContents`), должны прийти клиентам в пакете спавна.
- Порядок `OnChange` на хосте и сброс локального предсказания выбора.
- Импорт ассетов `Items/*.asset`, написанных вручную (ссылки на скрипты по GUID из `.meta`).
- Внешний вид HUD, шрифт `LegacyRuntime.ttf`, масштаб `CanvasScaler`, скорость затухания. Нужен просмотр в игре.
- Знак колеса мыши (вверх = предыдущий слот) и порог прокрутки.
- EditMode-тесты в Unity Test Runner. Через `dotnet test` они проходят (14/14).
- Сетевое поведение на двух машинах, задержка и отключения.
