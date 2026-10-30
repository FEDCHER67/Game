# G49 — приложение: вставки Claude

Это **не применённые** вставки к SYRINGE_RULE_G49_RU.md. Защищённые файлы остаются у Claude. Якоря проверены 28.10.2026; при дальнейших изменениях найти строку-якорь заново, не заменять файл целиком. Никаких изменений сцен/раскладки/магазина этим приложением не предлагается.

## 1. Сохранение: поля

Файл **C:\Dev\Game\Assets\OnlyVolunteers\Capture\Core\OnlyVolunteers.Capture.Core.asmdef**: в references дописать `"OnlyVolunteers.Inventory.Core"`. Другие ссылки сохранить.

Файл **C:\Dev\Game\Assets\OnlyVolunteers\Capture\Core\CaptureRules.cs**, класс FieldKitSave, сразу после `public int tool;`:

```csharp
public OnlyVolunteers.Inventory.SyringeInstance bloodSyringe;
public OnlyVolunteers.Inventory.SyringeInstance anaesthesiaSyringe;
```

Там же, CaptureSaveData, после `public FieldKitSave kit = new FieldKitSave();`:

```csharp
public OnlyVolunteers.Inventory.SyringeSaveBlock syringes = new OnlyVolunteers.Inventory.SyringeSaveBlock();
```

Файл **C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureDirector.cs**, в полях класса:

```csharp
public OnlyVolunteers.Inventory.SyringeSaveBlock Syringes = new OnlyVolunteers.Inventory.SyringeSaveBlock();
```

После существующей загрузки G48-каталога (именно экземпляра EconomyCatalog, не загрузка второго прайс-листа):

```csharp
OnlyVolunteers.Buyers.BuyerCatalog.SyringePrices =
    new OnlyVolunteers.Inventory.G48SyringePriceLookup(economy);
```

`economy` — уже загруженный экземпляр G48. В этом месте не создавать фонд и не начислять деньги.

## 2. CaptureSave: snapshot/restore

Файл **C:\Dev\Game\Assets\OnlyVolunteers\Capture\Scripts\CaptureSave.cs**, добавить `using OnlyVolunteers.Inventory;`.

В Write, якорь `data.kit = d.Kit.Snapshot();`, **после** него:

```csharp
data.kit.bloodSyringe = d.Kit.BloodSyringe?.Copy();
data.kit.anaesthesiaSyringe = d.Kit.AnaesthesiaSyringe?.Copy();
data.syringes = JsonUtility.FromJson<SyringeSaveBlock>(JsonUtility.ToJson(d.Syringes));
data.syringes.Items.Clear();
var inv = d.Kit.Inventory != null ? d.Kit.Inventory.Model : null;
if (inv != null) for (int slot = 0; slot < inv.SlotCount; slot++)
{
    var syringe = inv.GetSlot(slot).Syringe;
    if (syringe != null && !syringe.Discarded) data.syringes.Items.Add(syringe.Copy());
}
data.syringes.WorldItems.Clear();
foreach (var drop in UnityEngine.Object.FindObjectsByType<OfflineWorldItem>(FindObjectsSortMode.None))
{
    if (drop.Syringe == null || drop.Syringe.Discarded || drop.Definition == null) continue;
    var p = drop.transform.position; var q = drop.transform.rotation;
    data.syringes.WorldItems.Add(new SyringeWorldSave { DefinitionId = drop.Definition.Id,
        Item = drop.Syringe.Copy(), X = p.x, Y = p.y, Z = p.z, Qx = q.x, Qy = q.y, Qz = q.z, Qw = q.w });
}
```

В Read, якорь `d.Kit.Restore(data.kit);`, **после** него:

```csharp
d.Syringes = data.syringes ?? new SyringeSaveBlock();
d.Kit.RestoreSyringes(data.kit?.bloodSyringe, data.kit?.anaesthesiaSyringe);
var inv = d.Kit.Inventory != null ? d.Kit.Inventory.Model : null;
if (inv != null) foreach (var syringe in d.Syringes.Items)
{
    if (syringe == null || syringe.Discarded) continue;
    int definition = syringe.Kind == SyringeKind.Blood ? SyringeRules.BloodDefinitionId : SyringeRules.AnaesthesiaDefinitionId;
    // TryAdd(instance), never TryAdd(type-id): the latter creates a genuinely NEW purchase.
    inv.TryAdd(new ItemStack(definition, 1, SyringeRules.Price(syringe.Kind), syringe.Copy()));
}
foreach (var saved in d.Syringes.WorldItems)
{
    if (saved.Item == null || saved.Item.Discarded) continue;
    bool present = false;
    foreach (var drop in UnityEngine.Object.FindObjectsByType<OfflineWorldItem>(FindObjectsSortMode.None))
        if (drop.Syringe?.ItemId == saved.Item.ItemId) { present = true; break; }
    if (present) continue;
    var definition = d.Kit.Inventory.Database.Get(saved.DefinitionId);
    if (definition == null) continue; // report missing authored data; do not replace the saved instance with a new one
    var item = OfflineWorldItem.Spawn(definition, 1, SyringeRules.Price(saved.Item.Kind), new Vector3(saved.X, saved.Y, saved.Z));
    item.transform.rotation = new Quaternion(saved.Qx, saved.Qy, saved.Qz, saved.Qw);
    item.SetSyringe(saved.Item.Copy());
}
```

Эти вставки обслуживают **нынешний локальный Capture-инвентарь**. Для сетевых игроков тот же блок сохранять по существующему стабильному client GUID, не складывать чужие предметы в карман хоста. При нехватке места оставить record в сохранении и восстановить позднее; не терять/не дублировать. Items — карманы, WorldItems — drops; table.bloodSyringe/anesthesiaSyringe уже сохраняются самим SnapshotWorld, не дублировать их в Items. Если меняется полный owner/location save adapter, использовать его вместо второго списка тех же предметов.

У старого сейва без полей не вызывать SyringeInstance.New: отсутствующая история остаётся отсутствующей/legacy. Доказанный старый PersonId передаётся в SyringeSaveBlock.Legacy(id, type, provenPersonId). Поле `CaptureSaveData.syringes` сохраняется тем же атомарным файлом, что фонд и подтверждения, без отдельного шприцевого JSON-сейва.

## 3. NetworkInventory: перенос экземпляра

Файл **C:\Dev\Game\Assets\OnlyVolunteers\Inventory\Runtime\NetworkInventory.cs**, pickup, якорь `int added = model.TryAdd(itemId, item.Count, unitValue);` — заменить этой вставкой:

```csharp
var picked = item.Stack;
if (picked.Syringe == null && item.Definition.SyringeKind != SyringeKind.None)
    picked.Syringe = SyringeSaveBlock.Legacy(System.Guid.NewGuid().ToString("N"), item.Definition.SyringeKind);
int added = model.TryAdd(picked);
```

В том же методе заменить `ServerPickedUp?.Invoke(new ItemStack(itemId, added, unitValue));`:

```csharp
ServerPickedUp?.Invoke(new ItemStack(itemId, added, unitValue, picked.Syringe));
```

Drop: после `worldItem.ServerSetContents(dropped.Count, dropped.UnitValue);`, **до Spawn(instance)**:

```csharp
worldItem.ServerSetSyringe(dropped.Syringe);
```

После метода `ServerTryAdd(ItemDefinition definition, int count, int unitValue)` добавить overload для передачи/возврата:

```csharp
public int ServerTryAdd(ItemStack existing) =>
    IsServerInitialized && model != null ? model.TryAdd(existing) : 0;

public void ServerRefreshSyringeSlot(int slot)
{
    if (!IsServerInitialized || model == null || slot < 0 || slot >= model.SlotCount) return;
    var stack = model.GetSlot(slot);
    stack.Syringe = stack.Syringe?.Copy();
    slots[slot] = stack; // new snapshot after server binding/fill changes
}
```

При hand-over использовать `ServerTakeFromSlot` → `ServerTryAdd(ItemStack)`; при отказе получателя вернуть тот же stack отправителю. Для физического hand-over оставлять тот же WorldItem: его ServerSetSyringe уже существует. Точки spawn покупки/находки явно присваивают `SyringeInstance.New(type, stableId)` только **новому** экземпляру. Не выдавать новый экземпляр при pickup существующего.

## 4. C01: тот же payout, отдельное подтверждение выбора

Файл **C:\Dev\Game\Assets\OnlyVolunteers\Buyers\Runtime\FirstBuyerCrateV01.cs**. Этот ящик сейчас органная заглушка; C01-confirm не вызывать из её авто-сканирования. `TakeEmpty` подписать «Забрать пустой шприц», `LeaveWithBuyer` — «Оставить покупателю», default TakeEmpty. Подтверждение сервер получает после выбора, не при hover/drop.

Добавить `using OnlyVolunteers.Inventory;`. Вынести **существующую** выплату из TrySell в общий helper ниже, после `PriceOf`. Это перемещение одной существующей операции, не второй путь выплаты:

```csharp
private bool TryPaySale(int price, string title, string key, out FundResult paid)
{
    paid = default;
    TeamEconomy economy = TeamEconomy.Instance;
    if (economy == null || !economy.IsServer || !economy.ServerCanCommit) return false;
    paid = economy.ServerCredit(price, "sale", title, key);
    return paid.Ok;
}
```

В существующем TrySell участок от `TeamEconomy economy = TeamEconomy.Instance;` до проверки `if (!paid.Ok)` заменить вызовом **этого же helper**, сохранив существующий ключ продажи органов и обработку paid.Replayed:

```csharp
string title = item.Title;
string key = "sale:first-buyer:" + (string.IsNullOrEmpty(item.Identity)
    ? "noid:" + Guid.NewGuid().ToString("N") : item.Identity);
if (!TryPaySale(price, title, key, out FundResult paid)) return;
```

В старой строке Debug.Log после этого использовать `paid.Balance`; ссылку на локальную переменную economy убрать. Старое тело ServerCredit из TrySell удалить при извлечении: в файле должен остаться **один** вызов ServerCredit — внутри общего helper.

В классе добавить адаптер и серверный вход:

```csharp
private sealed class C01Payout : ISyringeSalePayout
{
    public FirstBuyerCrateV01 Crate;
    public OperationPhysicalItem Item;
    public bool TryCommit(SyringeSaleReceipt receipt, SyringeSalesSave nextState, SyringeInstance after)
    {
        var director = CaptureDirector.Instance;
        if (director == null || after == null) return false;
        // One portion key for every representation. Do not key payment by reusable syringe ItemId.
        if (!Crate.TryPaySale(receipt.Amount, "C01: кровь", "sale:c01:portion:" + receipt.PortionId, out FundResult paid)) return false;
        director.Syringes.Sales = nextState;
        Item.Data.syringe = after;
        Item.World.ServerSetSyringe(after);
        if (after.Discarded)
        {
            if (Item.Holder != null && Item.Holder.TryGetComponent(out NetworkInventory owner))
                owner.ServerReleasePhysical(Item.transform.position, Vector3.zero);
            InstanceFinder.ServerManager.Despawn(Item.NetworkObject, DespawnType.Destroy);
        }
        // receipt.XpEach/Participants + TransactionId are the XP command, saved in nextState.Receipts.
        // Attach the authoritative XP projection here once; on paid.Replayed do not book it again.
        // Existing TeamEconomy.ServerCommitted persists the SAME CaptureSave after the item outcome this frame.
        return true;
    }
}
public bool ServerConfirmC01Syringe(OperationPhysicalItem item, NetworkInventory seller, string confirmationId,
    SyringeReturnChoice choice = SyringeReturnChoice.TakeEmpty)
{
    if (!InstanceFinder.IsServerStarted || item?.Data?.syringe == null || seller == null ||
        seller.PhysicalItem != item.World || !InZone(item.transform.position)) return false;
    var director = CaptureDirector.Instance;
    if (director == null) return false;
    var rules = new SyringeSaleRules(director.Syringes.Sales);
    var syringe = item.Data.syringe;
    int participants = Math.Max(1, Math.Min(4, InstanceFinder.ServerManager.Clients.Count));
    return rules.TryConfirm(confirmationId, syringe.Portion, syringe, participants,
        new C01Payout { Crate = this, Item = item }, out _, choice);
}
```

Вызов — только из существующего авторитетного RPC/взаимодействия, где seller получен от sender, не из доверенного клиентского поля. Если операция подготовки физического шприца не сделана, не создавать копию поверх существующего предмета в кармане: сначала перевести тот же ItemId в physical item и убрать из кармана одним исходом. При возврате остаётся та же физическая сущность с after, а не предмет, созданный вызовом ServerTryAdd(type-id).

**Оставшийся обязательный шаг Claude:** в текущем ящике вообще нет XP-проекции. Сниппет сохраняет готовую единственную XP-команду в receipt; начисление реального XP должно войти в тот же авторитетный коммит вместе с nextState и itemAfter. До этого не объявлять runtime-C01/XP готовыми. Не вызывать BuyerRules.ConfirmSale поверх TryPaySale ради XP: это создаст вторую денежную проводку в другом состоянии. Для пакета использовать тот же SyringeSaleRules с сохранённым PortionId; не разрешать старому bag-adapter обойти SoldPortions. При проекции в Buyers Core всегда передавать BuyerItemState.BloodPortionId и SyringeItemId.

## 5. Находки, исход владельца, старт

CaptureDirector, только активный сервер: один сохранённый `Syringes.Daily` на мир. В серверном обновлении времени и при старте/загрузке вызывать тот же код (не отдельную стартовую выдачу):

```csharp
if (string.IsNullOrEmpty(Syringes.Daily.WorldId)) Syringes.Daily.WorldId = Guid.NewGuid().ToString("N");
bool created = DailySyringeFindRules.Advance(Syringes.Daily, Syringes.Daily.WorldId,
    activeWorldGameSeconds, worldActive);
// created => materialize Syringes.Daily.Uncollected at the authored wagon anchor.
// Never replace the existing Uncollected object; no coordinates are chosen by G49.
```

`activeWorldGameSeconds` — сохранённое абсолютное игровое время с 00:00, не Time.time/UTC и не один timeOfDay, обнуляемый каждый день. При pickup вызвать `Collect(state, actualItemId)` только после успешного переноса того же экземпляра в карман. При неуспехе спавна сохранять Uncollected и повторять материализацию того же ID. ExtraSpots — отдельный авторский список, не обязательный ежедневный спавн всех точек.

Обработка смерти/поимки в защищённом владельце должна списать **только переносимые шприцы**, один раз в существующем исходе; обычный disconnect не вызывает списания. Вещи мира/базы не перечислять в этой операции. Новые правила SyringeInstance.Discarded и item identity позволяют сохранить такой исход без выдачи нового экземпляра при respawn; отдельный денежный штраф не добавлять.

Для строго пустого нового инвентаря владелец Capture должен отдельно отключить автоматическое добавление kit-item 301 в EnsureItems. G49 оставил этот вспомогательный слот ради существующей схемы ввода; бесплатные стяжки/наркоз уже убраны. Магазин должен передать 303/304 в фактически используемый Capture ItemDatabase, а не ограничиться изменённым общим Inventory/Items/ItemDatabase. Эти действия не требуют менять сцены в G49.
