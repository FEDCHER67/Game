using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>Save and quit (D13, CD-09): the player, the van and its cargo doors, every captured NPC not yet on the
    /// table (identity, OperationState with sleep / residual / blood / grades, ties, condition, stun, where his pelvis lies
    /// and which way his head points, van-local when in the bay), the table (patient and outputs, stock), the field kit
    /// and the time of day. Timers are saved values: nothing runs while the game is closed. Escaped NPCs (back on their
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
                if (npc.State == NpcState.Free) continue;
                var s = new CaptureNpcSave
                {
                    facts = c.Facts,
                    operation = c.State,
                    npcState = (byte)npc.State,
                    stunLeft = npc.State == NpcState.Down ? npc.StunLeft : 2f,
                    stunTotal = npc.State == NpcState.Down ? npc.StunTotal : 2f,
                    inCargo = npc.InCargo && van != null,
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
            if (d.Disposal != null) { data.bodyBags = d.Disposal.Stock; data.corpses = d.Disposal.Snapshot(); }
            var clock = Object.FindAnyObjectByType<OnlyVolunteers.Sky22V04.SkyClock22>();
            data.timeOfDay = clock != null ? clock.Hour : -1f;
            data.completedPatients.AddRange(d.Registry.Completed);
        }

        public static void Read(CaptureDirector d, CaptureSaveData data)
        {
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
            d.Disposal?.Restore(data.corpses, data.bodyBags);
            var clock = Object.FindAnyObjectByType<OnlyVolunteers.Sky22V04.SkyClock22>();
            if (clock != null && data.timeOfDay >= 0f) clock.SetHour(data.timeOfDay);
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
            CaptureNpc c = d.Ensure(npc);
            c.PutDownAt(Ground(pelvis), head, s.faceUp, s.stunLeft, s.stunTotal);
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
