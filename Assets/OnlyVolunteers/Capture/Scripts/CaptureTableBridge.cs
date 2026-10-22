using System.Collections.Generic;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Network;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Capture
{
    /// <summary>The operating table side of stage A (D3, D4, D12; CD-01, CD-02, CD-06):
    /// - a captured NPC released over the table's pad (the operation's own OverPad box, not held, not flying) gets the
    ///   cartoon cloud; under it the NPC object goes away and the table admits HIS OperationState (same PatientId,
    ///   anesthesia, blood, grades) as the patient, spawned over the pad, where the table's existing magnet snap aligns
    ///   him; when the cloud clears he lies undressed in the patient shorts, with his own skin and face materials;
    /// - his hat / glasses (outfit parts named cap / hat / glasses) drop next to the table as small physical trash;
    /// - closing an arm strap cuts the hand tie, a leg strap the foot tie;
    /// - a dead patient stays on the table until a player takes him (CaptureCorpseDisposal: LMB with all straps open, or
    ///   R into a body bag; Claude rework 2026-10-18);
    /// - while the operation table view owns the screen the map's hands, hints and HUD step aside.
    /// The operation gameplay itself is untouched: everything goes through NetworkOperationTable's admission API.</summary>
    [DefaultExecutionOrder(11100)] // after OperationTableView (11000)
    public sealed class CaptureTableBridge : MonoBehaviour, IGreyboxUse
    {
        public const float RemoveHoldSeconds = 1f;
        public const float BaseRadius = 14f;
        /// <summary>Round 3: seconds a living patient lies off the table, held by nobody, before he is a field NPC again.</summary>
        public const float DischargeSettleSeconds = 0.8f; // round 4: ~1.5x faster (was 1.2 s)

        public NetworkOperationTable Table { get; private set; }
        public OperationTableView View { get; private set; }
        public CaptureFacts PatientFacts { get; set; }
        public int Admissions { get; private set; }
        public string LastAdmittedId { get; private set; } = "";
        public List<GameObject> Trash { get; } = new List<GameObject>();

        private CaptureDirector director;
        private GreyboxKccPawn pawn;
        private GreyboxInteractor interactor;
        private InventoryHud inventoryHud;
        private InventoryInput inventoryInput;
        private CaptureNpc admitting;
        private CaptureCloud cloud;
        private bool swapped;
        private Material[] npcSkin, npcFace;
        private GameObject[] bands;
        private LineRenderer handLink, footLink;
        private readonly Transform[] wrist = new Transform[2], ankle = new Transform[2];
        private bool tableMode;
        private float busyAt = -10f;
        private float removeHeld;
        private bool atBase;
        private float offTableSince = -1f;
        /// <summary>Patients whose hat / glasses already dropped (a discharged patient comes back in the crowd template's
        /// clothes; his second admission drops nothing new).</summary>
        private readonly HashSet<string> undressed = new HashSet<string>();
        public int Discharges { get; private set; }

        public bool Busy => admitting != null;
        public bool InTableMode => tableMode;

        public void Bind(NetworkOperationTable table, CaptureDirector owner, GreyboxKccPawn player)
        {
            Table = table;
            director = owner;
            pawn = player;
            View = table.GetComponent<OperationTableView>();
            interactor = pawn != null ? pawn.GetComponentInChildren<GreyboxInteractor>(true) : null;
            inventoryHud = pawn != null ? pawn.GetComponentInChildren<InventoryHud>(true) : null;
            inventoryInput = pawn != null ? pawn.GetComponentInChildren<InventoryInput>(true) : null;
            table.ServerPatientSpawned += OnPatientSpawned;
            table.CueReceived += OnCue;
            if (!GreyboxUses.All.Contains(this)) GreyboxUses.All.Add(this);
        }

        private void OnDestroy()
        {
            GreyboxUses.All.Remove(this);
            if (Table != null)
            {
                Table.ServerPatientSpawned -= OnPatientSpawned;
                Table.CueReceived -= OnCue;
            }
        }

        // ---------- admission ----------

        private void FixedUpdate()
        {
            if (Table == null || !Table.IsServerInitialized) return;
            if (admitting == null) { TryDischarge(); TryAdmit(); }
            else if (!swapped && cloud != null && cloud.Covered) Swap();
        }

        private void TryAdmit()
        {
            foreach (CaptureNpc c in CaptureNpc.All)
            {
                if (c == null || c.Admitted || c.Npc == null || !c.Npc.isActiveAndEnabled || c.Npc.State != NpcState.Down || c.Npc.InCargo) continue;
                INpcBody body = c.Npc.PhysicalBody;
                if (body == null || !body.Active || body.HolderCount > 0) continue;
                if (!OnTable(body)) continue;
                if (body.MainBody != null && body.MainBody.linearVelocity.magnitude > 4f) continue;
                if (Table.HasPatient)
                {
                    if (Time.time - busyAt > 3f)
                    {
                        busyAt = Time.time;
                        director.Toast("Стол занят — сначала закончи с тем, кто на нём", CaptureHud.Warn);
                        CaptureSounds.Error();
                    }
                    continue;
                }
                Begin(c, body);
                return;
            }
        }

        /// <summary>The release-over-pad check of the table's magnet snap, as generous as the van's body slide: the body's
        /// centre over the pad, or his upper body (collar or head) or hips laid on it; the magnet takes the rest.</summary>
        private bool OnTable(INpcBody body)
        {
            var tuning = Table.Tuning;
            if (OperationGeometry.OverPad(Table.transform.InverseTransformPoint(body.CenterOfMass + Table.transform.up * 0.1f), tuning)) return true;
            foreach (var mark in new[] { NpcLandmark.Collar, NpcLandmark.Head, NpcLandmark.Pelvis })
            {
                Vector3 l = Table.transform.InverseTransformPoint(body.Landmark(mark));
                if (Mathf.Abs(l.x) <= tuning.padHalfExtents.x + 0.08f && Mathf.Abs(l.z) <= tuning.padHalfExtents.z + 0.08f &&
                    l.y >= tuning.padTop - 0.12f && l.y <= tuning.padTop + 0.9f) return true;
            }
            return false;
        }

        private void Begin(CaptureNpc c, INpcBody body)
        {
            admitting = c;
            c.Admitted = true;
            swapped = false;
            Vector3 head = body.Landmark(NpcLandmark.Head), pelvis = body.Landmark(NpcLandmark.Pelvis);
            cloud = CaptureCloud.Spawn((head + pelvis) * 0.5f + Vector3.up * 0.05f, head - pelvis);
            Debug.Log($"[CAPTURE] cloud over {c.PatientId} on the table");
        }

        private void Swap()
        {
            swapped = true;
            CaptureNpc c = admitting;
            GreyboxNpc npc = c.Npc;
            INpcBody body = npc.PhysicalBody;
            Vector3 com = body != null && body.Active ? body.CenterOfMass : npc.Center;
            c.Facts.condition = npc.Condition;
            c.State.conditionLoss = CaptureGrades.ConditionLoss(npc.Condition);
            KeepAppearance(npc);
            if (undressed.Add(c.PatientId) && !c.Facts.undressed) SpawnTrash(npc);
            c.Facts.undressed = true;
            director.BeforeAdmit(c);
            // Over the pad, alongside the gurney (the KnockedOut root lies along its X axis, head toward the head end).
            var tuning = Table.Tuning;
            Vector3 local = Table.transform.InverseTransformPoint(com);
            local.x = Mathf.Clamp(local.x, -tuning.padHalfExtents.x * 0.5f, tuning.padHalfExtents.x * 0.5f);
            local.z = Mathf.Clamp(local.z, -tuning.padHalfExtents.z * 0.5f, tuning.padHalfExtents.z * 0.5f);
            local.y = tuning.padTop + 0.04f;
            Vector3 position = Table.transform.TransformPoint(local);
            Quaternion rotation = Table.transform.rotation * Quaternion.Euler(0f, -90f, 0f);
            PatientFacts = c.Facts;
            // One owner from here on: the NPC object (controller, ragdoll, animator) goes; the table owns the identity.
            npc.gameObject.SetActive(false);
            Destroy(npc.gameObject);
            bool ok = Table.ServerAdmit(c.State, position, rotation);
            Admissions++;
            LastAdmittedId = c.PatientId;
            director.AfterAdmit(c, ok);
            Debug.Log($"[CAPTURE] admitted {c.PatientId} ok={ok} ties={c.Facts.restraints} conditionLoss={c.State.conditionLoss}");
        }

        // ---------- round 3: a living patient off the table is a field NPC again ----------

        /// <summary>Fedya's round-3 bug: after the escape fall (or being taken off) a living patient lay as an inert table
        /// ragdoll: no escape, no Q, no kit. Now, once he lies off the table held by nobody for DischargeSettleSeconds, the
        /// table lets him go (ServerDischargeLiving) and he is re-created exactly like a loaded capture (CaptureSave.Respawn):
        /// the same PatientId, OperationState (anesthesia, blood, grades, the opening/seam), facts and ties. Awake, he is
        /// Groggy for a moment, then gets up and runs like any field NPC; asleep, he stays limp until the anesthesia wears
        /// off. Laid on the pad again he is admitted again (same identity).</summary>
        private void TryDischarge()
        {
            OperationState s = Table.State;
            NetworkPhysicsBody patient = Table.PatientBody;
            // Round 4: after the escape clips (HopRun / Stumble_Off) he is handed over at once, in the clip's last pose.
            bool ranOff = Table.PatientRanOff;
            bool candidate = Table.HasPatient && s != null && s.alive && !s.onTable && (!Table.PatientFalling || ranOff) && (patient == null || !patient.HasHolder);
            if (!candidate) { offTableSince = -1f; return; }
            if (!ranOff)
            {
                if (offTableSince < 0f) { offTableSince = Time.time; return; }
                if (Time.time - offTableSince < DischargeSettleSeconds) return;
            }
            offTableSince = -1f;
            CaptureFacts facts = PatientFacts;
            if (facts == null && director.Facts.TryGetValue(s.patientId, out CaptureFacts known)) facts = known;
            OperationState state = Table.ServerDischargeLiving(out Vector3 pelvis, out Vector3 head, out bool faceUp);
            if (state == null) return;
            bool standing = state.ranOff && !state.Sleeping;
            if (standing) pelvis = Table.RunOffPoint(state.escapeSide, out head);
            state.ranOff = false;
            if (facts == null)
            {
                facts = new CaptureFacts { patientId = state.patientId, districtId = "village", visual = "SausageBuddy_A", npcTypeId = "SAUSAGE_BUDDY_A", rolled = true };
                for (int i = 0; i < facts.intrinsic.Length && i < state.organs.Length; i++) facts.intrinsic[i] = state.organs[i].intrinsicGrade;
            }
            facts.undressed = true; // round 4: he stays in the patient trunks
            PatientFacts = null;
            CaptureTieVisuals.Remove(ref bands, ref handLink, ref footLink);
            bool asleep = state.Sleeping;
            var save = new CaptureNpcSave
            {
                facts = facts, operation = state, npcState = (byte)NpcState.Down,
                // Awake: past the Out share of the stun at once (Groggy: kicks), up and away in ~1.3 s (round 4: 1.5x faster).
                // Asleep: CaptureNpc pins him. Ran off (HopRun): on his feet, running.
                stunLeft = asleep ? 4f : 1.33f, stunTotal = asleep ? 8f : 4f,
                inCargo = false, pelvis = pelvis, headDirection = head, faceUp = faceUp, standing = standing,
            };
            CaptureNpc c = CaptureSave.Respawn(director, save);
            Discharges++;
            if (c == null) { Debug.LogWarning($"[CAPTURE] discharge of {state.patientId}: no crowd template, he is gone"); return; }
            c.gameObject.name = "Escaped_" + state.patientId;
            director.Toast(asleep ? "Он сполз со стола — спит на полу" : "Сбежал со стола! Лови его", asleep ? CaptureHud.Neutral : CaptureHud.Warn);
            Debug.Log($"[CAPTURE] discharged {state.patientId} -> field NPC alive={state.alive} asleep={asleep} ties={facts.restraints} sutured={state.sutured}");
        }

        // ---------- round 3: zip ties on the table patient (the field kit by the table) ----------

        /// <summary>The tie the kit would put on for an aimed body part of the table patient (None: not a limb, or done).</summary>
        public TieTarget TableTieFor(BodyPart part)
        {
            if (PatientFacts == null || Table == null || !Table.HasPatient) return TieTarget.None;
            TieTarget aimed = part == BodyPart.ArmL || part == BodyPart.ArmR || part == BodyPart.ShoulderL || part == BodyPart.ShoulderR ? TieTarget.Hands
                : part == BodyPart.LegL || part == BodyPart.LegR ? TieTarget.Feet : TieTarget.None;
            return aimed == TieTarget.None ? TieTarget.None : CaptureRules.ChooseTie(PatientFacts.restraints, aimed);
        }

        /// <summary>Server (the stage A host): a zip tie on the table patient. The ties travel with his facts (a discharged
        /// patient keeps them); a closing strap still cuts the matching tie (OnCue).</summary>
        public bool TieTablePatient(TieTarget tie)
        {
            if (tie == TieTarget.None || PatientFacts == null || Table == null || !Table.IsServerInitialized || !Table.HasPatient) return false;
            PatientFacts.restraints = CaptureRules.Apply(PatientFacts.restraints, tie);
            RefreshPatientTies();
            Debug.Log($"[CAPTURE] tie {tie} on the table patient {Table.State.patientId}: {PatientFacts.restraints}");
            return true;
        }

        private void KeepAppearance(GreyboxNpc npc)
        {
            npcSkin = null;
            npcFace = null;
            foreach (var smr in npc.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.name == "Body") npcSkin = smr.sharedMaterials;
                else if (smr.name == "Face") npcFace = smr.sharedMaterials;
            }
        }

        /// <summary>The same skin and face materials on the patient model (the Buddy head, face and build are the patient
        /// model's own: A and B share them). Kept for every later type: matching material names first.</summary>
        private void OnPatientSpawned(NetworkPhysicsBody patient)
        {
            if (patient == null) return;
            foreach (var smr in patient.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.name == "Body" && npcSkin != null) smr.sharedMaterials = Match(smr.sharedMaterials, npcSkin);
                else if (smr.name == "Face" && npcFace != null && npcFace.Length == smr.sharedMaterials.Length) smr.sharedMaterials = npcFace;
            }
            foreach (Transform t in patient.GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "mixamorig:LeftHand") wrist[0] = t;
                else if (t.name == "mixamorig:RightHand") wrist[1] = t;
                else if (t.name == "mixamorig:LeftFoot") ankle[0] = t;
                else if (t.name == "mixamorig:RightFoot") ankle[1] = t;
            }
            CaptureTieVisuals.Remove(ref bands, ref handLink, ref footLink);
            RefreshPatientTies();
        }

        private static readonly System.Collections.Generic.Dictionary<Material, Material> closedSkins = new();
        internal static Material[] Match(Material[] target, Material[] source)
        {
            var result = (Material[])target.Clone();
            Material npcSkin = null;
            foreach (var m in source) if (m != null && m.name == "Buddy_Skin") npcSkin = m;
            for (int i = 0; i < result.Length; i++)
            {
                if (result[i] == null) continue;
                // Patient v03 (closed back): the slot never cut by the opening stencil gets the NPC's own skin colour under its
                // own name, so the stencil (it takes only "Buddy_Skin*" slots) still never touches it.
                if (result[i].name.StartsWith("Patient_Skin_Closed") && npcSkin != null)
                {
                    if (!closedSkins.TryGetValue(npcSkin, out var closed) || closed == null)
                        closedSkins[npcSkin] = closed = new Material(npcSkin) { name = "Patient_Skin_Closed (" + npcSkin.name + ")" };
                    result[i] = closed; continue;
                }
                foreach (var m in source)
                    if (m != null && m.name == result[i].name) { result[i] = m; break; }
            }
            return result;
        }

        private void RefreshPatientTies()
        {
            if (PatientFacts == null || Table.PatientObject == null) { CaptureTieVisuals.Remove(ref bands, ref handLink, ref footLink); return; }
            CaptureTieVisuals.Ensure(ref bands, ref handLink, ref footLink, wrist, ankle, PatientFacts.restraints, Table.PatientObject.transform);
        }

        private void OnCue(PatientCue cue, int organ, int client)
        {
            if (cue != PatientCue.StrapChanged || PatientFacts == null || Table.State == null) return;
            Restraints before = PatientFacts.restraints;
            Restraints after = CaptureRules.AfterStraps(before, Table.State.restraints);
            if (before.hands == after.hands && before.feet == after.feet) return;
            PatientFacts.restraints = after;
            RefreshPatientTies();
            director.Toast(before.hands && !after.hands ? "Стяжку на руках срезали — держит ремень" : "Стяжку на ногах срезали — держит ремень", CaptureHud.Neutral);
            Debug.Log($"[CAPTURE] strap cut a tie on {Table.State.patientId}: {before} -> {after}");
        }

        // ---------- trash: hats and glasses ----------

        private static bool IsHeadwear(string material)
        {
            string m = material.ToLowerInvariant();
            return m.Contains("_cap_") || m.EndsWith("_cap") || m.Contains("hat") || m.Contains("beanie") || m.Contains("helmet") || m.Contains("glass");
        }

        private void SpawnTrash(GreyboxNpc npc)
        {
            foreach (var smr in npc.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                // TASK-000900: the types' crowd LODs (X_LOD1 / X_LOD2) would drop the same hat again: LOD0 only ("X" or "X_LOD0").
                string part = smr.name;
                int lodAt = part.LastIndexOf("_LOD", System.StringComparison.Ordinal);
                if (lodAt > 0 && int.TryParse(part.Substring(lodAt + 4), out int lod))
                {
                    if (lod > 0) continue;
                    part = part.Substring(0, lodAt);
                }
                if (smr.sharedMesh == null || part == "Body" || part == "Face") continue;
                var mats = smr.sharedMaterials;
                var subs = new List<int>();
                for (int i = 0; i < mats.Length && i < smr.sharedMesh.subMeshCount; i++)
                    if (mats[i] != null && IsHeadwear(mats[i].name)) subs.Add(i);
                if (subs.Count == 0) continue;
                var baked = new Mesh();
                smr.BakeMesh(baked, true);
                Vector3[] v = baked.vertices;
                var world = new List<Vector3>();
                var tris = new List<List<int>>();
                var map = new Dictionary<int, int>();
                var used = new List<Material>();
                foreach (int s in subs)
                {
                    var list = new List<int>();
                    foreach (int idx in baked.GetTriangles(s))
                    {
                        if (!map.TryGetValue(idx, out int j))
                        {
                            j = world.Count;
                            map[idx] = j;
                            world.Add(smr.transform.position + smr.transform.rotation * v[idx]);
                        }
                        list.Add(j);
                    }
                    tris.Add(list);
                    used.Add(mats[s]);
                }
                Destroy(baked);
                if (world.Count < 3) continue;
                var bounds = new Bounds(world[0], Vector3.zero);
                foreach (var p in world) bounds.Encapsulate(p);
                var mesh = new Mesh { name = "Trash_" + used[0].name };
                var local = new Vector3[world.Count];
                for (int i = 0; i < local.Length; i++) local[i] = world[i] - bounds.center;
                mesh.vertices = local;
                mesh.subMeshCount = tris.Count;
                for (int i = 0; i < tris.Count; i++) mesh.SetTriangles(tris[i], i);
                mesh.RecalculateNormals();
                mesh.RecalculateBounds();
                bool glasses = used[0].name.ToLowerInvariant().Contains("glass");
                var go = new GameObject(glasses ? "Мусор: очки" : "Мусор: кепка");
                // Off the table to the open (camera) side and down to the floor next to it.
                Vector3 side = Table != null ? -Table.transform.right : Vector3.right;
                // It slips off the head and drops beside the table (the pad is 0.84 m wide).
                Transform head = null;
                foreach (var t in npc.GetComponentsInChildren<Transform>(true)) if (t.name == "mixamorig:Head") { head = t; break; }
                Vector3 headPos = head != null ? head.position : npc.Center;
                Vector3 beside = Table != null ? Table.transform.position + side * 0.75f + Vector3.up * 0.95f : headPos;
                go.transform.position = Table != null ? beside + Table.transform.forward * Mathf.Clamp(Vector3.Dot(headPos - Table.transform.position, Table.transform.forward), -1f, 1f) : headPos;
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterials = used.ToArray();
                var box = go.AddComponent<BoxCollider>();
                box.size = Vector3.Max(mesh.bounds.size, Vector3.one * 0.03f);
                var rb = go.AddComponent<Rigidbody>();
                rb.mass = glasses ? 0.08f : 0.2f;
                rb.interpolation = RigidbodyInterpolation.Interpolate;
                foreach (var own in npc.GetComponentsInChildren<Collider>(true)) Physics.IgnoreCollision(box, own, true);
                if (Table != null && Table.PatientObject != null)
                    foreach (var other in Table.PatientObject.GetComponentsInChildren<Collider>(true)) Physics.IgnoreCollision(box, other, true);
                rb.linearVelocity = Vector3.up * 0.8f + side * 0.9f + Random.insideUnitSphere * 0.2f;
                rb.angularVelocity = Random.insideUnitSphere * 8f;
                var evidence = go.AddComponent<CaptureTrash>(); evidence.Kind = glasses ? "glasses" : "hat"; evidence.PatientId = admitting.PatientId;
                Trash.Add(go);
                Debug.Log($"[CAPTURE] trash {go.name} from {npc.name} ({world.Count} verts)");
            }
        }

        // ---------- per frame: table mode, E, R ----------

        private void Update()
        {
            if (admitting != null && swapped && cloud == null) admitting = null;
            if (Table == null || View == null) return;
            bool mode = View.Active || View.Blend > 0.01f;
            if (mode != tableMode)
            {
                tableMode = mode;
                if (interactor != null) interactor.enabled = !mode;
                if (inventoryHud != null) inventoryHud.enabled = !mode;
                // The table view's own 1-4 tool keys must not switch the field kit's hotbar slot meanwhile (round 2).
                if (inventoryInput != null) inventoryInput.enabled = !mode;
                director.SetTableMode(mode);
            }
            if (pawn != null && pawn.Controlled)
            {
                bool near = Vector3.Distance(pawn.Position, Table.transform.position) <= BaseRadius;
                if (near && !atBase) director.Kit?.RestockAtBase();
                atBase = near;
            }

        }

        private void LateUpdate() => CaptureTieVisuals.UpdateLinks(handLink, footLink, wrist, ankle, PatientFacts != null ? PatientFacts.restraints : default);

        public bool PatientFinished
        {
            get
            {
                var s = Table != null ? Table.State : null;
                return s != null && Table.HasPatient && (!s.alive || s.extracted >= 3);
            }
        }

        /// <summary>Whether the crosshair is on the patient and he is within reach.</summary>
        public bool AimingAtPatient
        {
            get
            {
                if (pawn == null || pawn.ViewCamera == null || Table.PatientObject == null) return false;
                Transform eye = pawn.ViewCamera.transform;
                if (!UnityEngine.Physics.Raycast(eye.position, eye.forward, out RaycastHit hit, 3f, OvLayers.ShootMask & ~OperationSurgicalBones.Mask, QueryTriggerInteraction.Collide)) return false;
                return hit.collider.transform.IsChildOf(Table.PatientObject.transform);
            }
        }

        public string RemoveHint => director != null && director.Disposal != null ? director.Disposal.Hint : null;
        public float RemoveProgress => director != null && director.Disposal != null ? director.Disposal.PackProgress : 0f;
        public void RemoveBody() => director?.Disposal?.TryPackAimed();

        // E by the table belongs to the table view: claim it so the same press never also opens a van door nearby.
        public bool Offer(GreyboxPawn who, out string label)
        {
            label = null;
            return View != null && Table != null && Table.State != null && View.PromptVisible && !View.Active;
        }

        public void Use(GreyboxPawn who) { }
    }

    /// <summary>A hat or glasses left by an undressed patient (cleanup evidence, ops §18).</summary>
    public sealed class CaptureTrash : MonoBehaviour
    {
        public string Kind = "hat";
        public string PatientId = "";
    }
}
