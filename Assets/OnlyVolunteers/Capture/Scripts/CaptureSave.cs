using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>Save and quit (D13, CD-09): the player, the van and its cargo doors, every captured NPC not yet on the
    /// table (identity, OperationState with sleep / residual / blood / grades, ties, condition, stun, where his pelvis lies
    /// and which way his head points, van-local when in the bay), the table (patient and outputs, stock), the field kit
    /// the time of day and (v2) the team economy block (shared fund, van tiers, bases, deliveries). Timers are saved values: nothing runs while the game is closed. Escaped NPCs (back on their
    /// feet and free) are part of the crowd again and are not saved. One JSON file in persistentDataPath/OnlyVolunteers.</summary>
    public static class CaptureSave
    {
        private static readonly int GroundMask = OvLayers.ShootMask & ~OvLayers.NpcMask;

        public static void Write(CaptureDirector d, CaptureSaveData data)
        {
            var pawn = d.Pawn;
            var van = d.Van;
            if (pawn != null)
            {
                bool driving = !pawn.Controlled && van != null;
                data.playerDriving = driving;
                data.playerPosition = driving ? van.transform.TransformPoint(new Vector3(-1.8f, 0f, 0.6f)) : pawn.Position;
                data.playerYaw = pawn.ViewCamera != null ? pawn.ViewCamera.transform.eulerAngles.y : pawn.Body.eulerAngles.y;
            }
            if (van != null)
            {
                data.vanPosition = van.transform.position;
                data.vanRotation = van.transform.rotation;
                var cargo = van.GetComponent<GreyboxVanCargo>();
                if (cargo != null) { data.slideOpen = cargo.DoorOpen(0); data.rearOpen = cargo.DoorOpen(1); }
            }
            foreach (CaptureNpc c in CaptureNpc.All)
            {
                if (c == null || c.Admitted || c.Npc == null || !c.Npc.isActiveAndEnabled || c.Facts == null) continue;
                GreyboxNpc npc = c.Npc;
                // K10: a doomed runner (belly opened, not sewn) is no ordinary escapee: he is saved on his feet with his run
                // (the rolled distance and what he covered), so a load neither frees him nor loses the body.
                bool doomedRunner = npc.State == NpcState.Free && c.State != null && c.State.ShockRun;
                if (npc.State == NpcState.Free && !doomedRunner) continue;
                var s = new CaptureNpcSave
                {
                    facts = c.Facts,
                    operation = c.State,
                    npcState = (byte)npc.State,
                    stunLeft = npc.State == NpcState.Down ? npc.StunLeft : 2f,
                    stunTotal = npc.State == NpcState.Down ? npc.StunTotal : 2f,
                    inCargo = npc.InCargo && van != null,
                    standing = doomedRunner,
                };
                c.Facts.condition = npc.Condition;
                PatientRecord record = d.Registry.Get(c.PatientId);
                s.stage = record != null ? (byte)record.Stage : (byte)PatientStage.Captured;
                INpcBody body = npc.PhysicalBody;
                Vector3 pelvis, head;
                bool faceUp = true;
                if (body != null && body.Active)
                {
                    pelvis = body.Landmark(NpcLandmark.Pelvis);
                    head = body.Landmark(NpcLandmark.Head) - pelvis;
                    if (npc.Ragdoll != null && npc.Ragdoll.Active) faceUp = Vector3.Dot(npc.Ragdoll.Front, Vector3.up) > -0.2f;
                }
                else
                {
                    pelvis = npc.Center;
                    head = npc.transform.forward;
                }
                head = Vector3.ProjectOnPlane(head, Vector3.up);
                if (head.sqrMagnitude < 1e-4f) head = Vector3.forward;
                if (s.inCargo)
                {
                    pelvis = van.transform.InverseTransformPoint(pelvis);
                    head = van.transform.InverseTransformDirection(head);
                }
                s.pelvis = pelvis;
                s.headDirection = head.normalized;
                s.faceUp = faceUp;
                data.npcs.Add(s);
            }
            if (d.Table != null && d.Table.IsServerInitialized)
            {
                // A deep copy (JsonUtility round trip): the live objects keep running after the save.
                var world = d.Table.SnapshotWorld();
                data.table = world != null ? JsonUtility.FromJson<OperationWorldState>(JsonUtility.ToJson(world)) : null;
                data.tablePatient = d.Table.HasPatient ? d.Bridge.PatientFacts : null;
            }
            data.kit = d.Kit.Snapshot();
            WriteSyringes(d, data);
            if (d.Disposal != null) { data.bodyBags = d.Disposal.Stock; data.corpses = d.Disposal.Snapshot(); }
            var clock = Object.FindAnyObjectByType<OnlyVolunteers.Sky22V04.SkyClock22>();
            data.timeOfDay = clock != null ? clock.Hour : -1f;
            data.completedPatients.AddRange(d.Registry.Completed);
            // ECONOMY spec v01 §3.1 / §10: the money is the team's shared fund (with its history, transaction keys, van
            // tiers, flags, bases and deliveries) in one block. The old per-player hasCash / cash fields are not written
            // any more (v2), so nothing can migrate twice.
            data.hasCash = false;
            data.cash = 0;
            EconomySaveData economy = TeamEconomy.Instance != null ? TeamEconomy.Instance.ServerSaveBlock() : null;
            if (economy != null) data.economy = economy;
            else Debug.LogWarning("[CAPTURE] no team economy on this server: the save carries no fund");
            // PLAYER stage: the world's immutable mode + opening/tutorial state, in the same atomic file as the fund.
            data.world = OnlyVolunteers.Session.WorldSessionV01.ServerSaveBlock();
        }

        /// <summary>The shared fund from the save (§10.3): a v2 block is restored as it is; a v1 save has none, so the
        /// host's legacy cash (hasCash / cash, W86) moves into the fund exactly once and the migrated block is written
        /// back at once. The per-player NetworkInventory cash is no longer a money store (its legacy API forwards here).</summary>
        private static void RestoreEconomy(CaptureSaveData data)
        {
            TeamEconomy economy = TeamEconomy.Instance;
            if (economy == null || !economy.IsServer) { Debug.LogWarning("[CAPTURE] fund not restored: no team economy on the server"); return; }
            economy.ServerLoad(data.economy, data.hasCash, data.cash);
            // WP02: one first-blood flag per world. An older save may hold it only in the C01 syringe record: the economy takes
            // it once, and the record mirrors the economy (so the next C01 quote shows the XP the economy grants).
            var sales = data.syringes != null ? data.syringes.Sales : null;
            if (economy.ServerState != null && sales != null)
            {
                economy.ServerState.ReconcileFirstBlood(sales.FirstBloodXpGranted);
                sales.FirstBloodXpGranted |= economy.ServerState.FirstBloodGranted;
            }
        }

        public static void Read(CaptureDirector d, CaptureSaveData data)
        {
            OnlyVolunteers.Session.WorldSessionV01.ServerLoad(data.world); // PLAYER stage: mode + opening/tutorial first
            var van = d.Van;
            if (van != null)
            {
                van.ResetUpright(data.vanPosition, data.vanRotation.eulerAngles.y);
                van.transform.rotation = data.vanRotation;
                var rb = van.GetComponent<Rigidbody>();
                if (rb != null) rb.rotation = data.vanRotation;
                var cargo = van.GetComponent<GreyboxVanCargo>();
                if (cargo != null)
                {
                    if (cargo.DoorOpen(0) != data.slideOpen) cargo.ToggleDoor(0);
                    if (cargo.DoorOpen(1) != data.rearOpen) cargo.ToggleDoor(1);
                }
            }
            Physics.SyncTransforms();
            if (d.Pawn != null && d.Pawn.Controlled) d.Pawn.Teleport(data.playerPosition, data.playerYaw);
            d.Registry.LoadCompleted(data.completedPatients);
            foreach (CaptureNpcSave s in data.npcs) Respawn(d, s);
            if (data.table != null && d.Table != null)
            {
                if (data.tablePatient != null && !string.IsNullOrEmpty(data.tablePatient.patientId)) d.Facts[data.tablePatient.patientId] = data.tablePatient;
                d.Bridge.PatientFacts = data.table.patient != null ? data.tablePatient : null;
                d.Table.ServerRestore(data.table);
            }
            d.Kit.Restore(data.kit);
            ReadSyringes(d, data);
            d.Disposal?.Restore(data.corpses, data.bodyBags);
            RestoreEconomy(data);
            var clock = Object.FindAnyObjectByType<OnlyVolunteers.Sky22V04.SkyClock22>();
            if (clock != null && data.timeOfDay >= 0f) clock.SetHour(data.timeOfDay);
        }

        /// <summary>G49 snapshot: the kit's two syringe references, every syringe instance in the host's hotbar (Items) and
        /// lying free in the world (WorldItems, with pose), the C01 sale record and the daily-find record. Table syringes are
        /// saved by the table snapshot itself (not listed twice). Deep copies: the live objects keep running.</summary>
        private static void WriteSyringes(CaptureDirector d, CaptureSaveData data)
        {
            data.kit.bloodSyringe = d.Kit.BloodSyringe?.Copy();
            data.kit.anaesthesiaSyringe = d.Kit.AnaesthesiaSyringe?.Copy();
            data.syringes = JsonUtility.FromJson<SyringeSaveBlock>(JsonUtility.ToJson(d.Syringes));
            data.syringes.Items.Clear();
            var inv = d.Kit.Inventory != null ? d.Kit.Inventory.Model : null;
            if (inv != null)
                for (int slot = 0; slot < inv.SlotCount; slot++)
                {
                    var syringe = inv.GetSlot(slot).Syringe;
                    if (syringe != null && !syringe.Discarded) data.syringes.Items.Add(syringe.Copy());
                }
            data.syringes.WorldItems.Clear();
            foreach (var drop in Object.FindObjectsByType<OfflineWorldItem>())
            {
                if (drop.Syringe == null || drop.Syringe.Discarded || drop.Definition == null || drop.Count <= 0) continue;
                if (d.Syringes.Daily.Uncollected != null && drop.Syringe.ItemId == d.Syringes.Daily.Uncollected.ItemId) continue; // the find record owns it
                var p = drop.transform.position;
                var q = drop.transform.rotation;
                data.syringes.WorldItems.Add(new SyringeWorldSave { DefinitionId = drop.Definition.Id, Item = drop.Syringe.Copy(), X = p.x, Y = p.y, Z = p.z, Qx = q.x, Qy = q.y, Qz = q.z, Qw = q.w });
            }
        }

        /// <summary>G49 restore: the same instances come back (TryAdd(instance), never TryAdd(type id), which would mint a NEW
        /// syringe); one already present is not added twice; a save without the block restores nothing and invents nothing.</summary>
        private static void ReadSyringes(CaptureDirector d, CaptureSaveData data)
        {
            d.Syringes = data.syringes ?? new SyringeSaveBlock();
            d.Syringes.Items ??= new System.Collections.Generic.List<SyringeInstance>();
            d.Syringes.WorldItems ??= new System.Collections.Generic.List<SyringeWorldSave>();
            d.Syringes.Sales ??= new SyringeSalesSave();
            d.Syringes.Daily ??= new DailySyringeFindSave();
            d.Kit.RestoreSyringes(data.kit?.bloodSyringe, data.kit?.anaesthesiaSyringe);
            var inv = d.Kit.Inventory != null ? d.Kit.Inventory.Model : null;
            if (inv != null)
                foreach (var syringe in d.Syringes.Items)
                {
                    if (syringe == null || syringe.Discarded || HasSyringe(inv, syringe.ItemId)) continue;
                    int definition = syringe.Kind == SyringeKind.Blood ? SyringeRules.BloodDefinitionId : SyringeRules.AnaesthesiaDefinitionId;
                    int price;
                    try { price = SyringeRules.Price(syringe.Kind); } catch (System.Exception) { price = 0; }
                    var copy = syringe.Copy();
                    if (inv.TryAdd(new ItemStack(definition, 1, price, copy)) != 1)
                        Debug.LogWarning($"[CAPTURE] syringe {syringe.ItemId} kept in the save record: no hotbar space");
                    // the kit's own references point at the live hotbar instances again (same ids)
                    if (d.Kit.BloodSyringe != null && d.Kit.BloodSyringe.ItemId == copy.ItemId) d.Kit.RestoreSyringes(copy, d.Kit.AnaesthesiaSyringe);
                    if (d.Kit.AnaesthesiaSyringe != null && d.Kit.AnaesthesiaSyringe.ItemId == copy.ItemId) d.Kit.RestoreSyringes(d.Kit.BloodSyringe, copy);
                }
            var database = d.Kit.Inventory != null ? d.Kit.Inventory.Database : null;
            foreach (var saved in d.Syringes.WorldItems)
            {
                if (saved?.Item == null || saved.Item.Discarded) continue;
                bool present = false;
                foreach (var drop in Object.FindObjectsByType<OfflineWorldItem>())
                    if (drop.Syringe != null && drop.Syringe.ItemId == saved.Item.ItemId) { present = true; break; }
                if (present) continue;
                var definition = database != null ? database.Get(saved.DefinitionId) : null;
                if (definition == null) { Debug.LogWarning($"[CAPTURE] saved world syringe {saved.Item.ItemId}: definition {saved.DefinitionId} missing (kept in the record)"); continue; }
                int price;
                try { price = SyringeRules.Price(saved.Item.Kind); } catch (System.Exception) { price = 0; }
                var item = OfflineWorldItem.Spawn(definition, 1, price, new Vector3(saved.X, saved.Y, saved.Z));
                item.transform.rotation = new Quaternion(saved.Qx, saved.Qy, saved.Qz, saved.Qw);
                item.SetSyringe(saved.Item.Copy());
            }
            Debug.Log($"[CAPTURE] syringes restored: hotbar {d.Syringes.Items.Count}, world {d.Syringes.WorldItems.Count}, C01 sold portions {d.Syringes.Sales.SoldPortions.Count}, first sale {d.Syringes.Sales.FirstSyringeSold}");
        }

        private static bool HasSyringe(InventoryModel inv, string itemId)
        {
            for (int i = 0; i < inv.SlotCount; i++)
                if (inv.GetSlot(i).Syringe != null && inv.GetSlot(i).Syringe.ItemId == itemId) return true;
            return false;
        }

        /// <summary>A captured NPC again: a fresh copy of his crowd template, his identity, down where he lay.</summary>
        public static CaptureNpc Respawn(CaptureDirector d, CaptureNpcSave s)
        {
            if (s == null || s.facts == null || s.operation == null || string.IsNullOrEmpty(s.facts.patientId)) return null;
            GameObject template = Template(s.facts.visual);
            if (template == null) { Debug.LogWarning("[CAPTURE] no crowd template for " + s.facts.visual); return null; }
            Vector3 pelvis = s.pelvis, head = s.headDirection;
            if (s.inCargo && d.Van != null)
            {
                pelvis = d.Van.transform.TransformPoint(pelvis);
                head = d.Van.transform.TransformDirection(head);
            }
            // Made far below the map so nobody "witnesses" a knockdown that already happened before the save.
            var go = Object.Instantiate(template, new Vector3(pelvis.x, -400f, pelvis.z), Quaternion.identity, template.transform.parent != null ? template.transform.parent.parent : null);
            go.name = "Captured_" + s.facts.patientId;
            go.AddComponent<PatientTag>().PatientId = s.facts.patientId;
            go.SetActive(true);
            var npc = go.GetComponent<GreyboxNpc>();
            npc.Condition = s.facts.condition;
            d.Facts[s.facts.patientId] = s.facts;
            PatientRecord record = d.Registry.Ensure(npc);
            record.Operation = s.operation;
            // Round 4: a former patient keeps the patient look (trunks, his skin and face), in the field and after a load.
            if (s.facts.undressed && d.Table != null && d.Table.PatientPrefab != null && CaptureUndress.Apply(go, d.Table.PatientPrefab.gameObject))
                // K10 (Fedya 29.10): the belly as it left the table: the open wound (opened, not sewn) or the seam / patch.
                OperationBodyWound.Attach(go, d.Table.Tuning, s.operation, d.Table.PatientPrefab.gameObject);
            CaptureNpc c = d.Ensure(npc);
            if (s.standing && !s.inCargo) c.StandAt(Ground(pelvis), head);
            else c.PutDownAt(Ground(pelvis), head, s.faceUp, s.stunLeft, s.stunTotal);
            Debug.Log($"[CAPTURE] restored {s.facts.patientId} at {pelvis} cargo={s.inCargo} sleep={s.operation.sleepRemaining:F1} blood={s.operation.bloodPortions} ties={s.facts.restraints}");
            return c;
        }

        private static GameObject Template(string visual)
        {
            var crowd = CrowdDirector.Instance;
            if (crowd == null || crowd.Templates == null) return null;
            GameObject first = null;
            foreach (var t in crowd.Templates)
            {
                if (t == null) continue;
                first ??= t;
                var a = t.GetComponentInChildren<Animator>(true);
                if (a != null && a.gameObject.name == visual) return t;
            }
            return first;
        }

        private static Vector3 Ground(Vector3 p)
        {
            if (Physics.Raycast(p + Vector3.up * 0.9f, Vector3.down, out RaycastHit hit, 3f, GroundMask, QueryTriggerInteraction.Ignore))
                return hit.point + Vector3.up * 0.02f;
            return p;
        }
    }
}
