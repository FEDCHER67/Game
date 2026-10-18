using System;
using System.Collections;
using System.Collections.Generic;
using FishNet;
using FishNet.Object;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Network;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Player;
using UnityEngine;
using ThrowCharge = OnlyVolunteers.Inventory.ThrowCharge;
using ThrowChargeIndicator = OnlyVolunteers.Inventory.ThrowChargeIndicator;

namespace OnlyVolunteers.Capture
{
    /// <summary>Capture identity carried by a corpse: a field NPC's ragdoll (map grab) or the network patient ragdoll
    /// (off the table, or packed into a body bag: the same ragdoll, wrapped).</summary>
    public sealed class CaptureCorpse : MonoBehaviour
    {
        public CaptureFacts Facts { get; private set; }
        public OperationState State { get; private set; }
        public CaptureNpc FieldNpc { get; private set; }
        public bool Sinking { get; set; }
        public bool EvidenceActive { get; set; } = true;
        public OperationPatientRagdoll Ragdoll { get; private set; }
        public NetworkPhysicsBody Body { get; private set; }
        /// <summary>Packed into a body bag (the ragdoll wears the bag; Rework 2026-10-18).</summary>
        public bool Bagged => Ragdoll != null && Ragdoll.Bagged;
        public string PatientId => Facts != null ? Facts.patientId : "";
        public bool WasHeld;
        private CaptureCorpseDisposal owner;
        private OperationRules rules;
        public bool Held => FieldNpc != null ? FieldNpc.Npc != null && FieldNpc.Npc.PhysicalBody != null && FieldNpc.Npc.PhysicalBody.HolderCount > 0
            : Body != null && Body.HasHolder;
        public Vector3 Center => FieldNpc != null && FieldNpc.Npc != null && FieldNpc.Npc.PhysicalBody != null ? FieldNpc.Npc.PhysicalBody.Landmark(NpcLandmark.Pelvis) :
            Ragdoll != null && Ragdoll.Active ? Ragdoll.PlacementPoint : transform.position;
        public void Bind(CaptureCorpseDisposal disposal, CaptureFacts facts, OperationState state, CaptureNpc field = null)
        {
            owner = disposal; Facts = facts; State = state; FieldNpc = field;
            Ragdoll = GetComponent<OperationPatientRagdoll>(); Body = GetComponent<NetworkPhysicsBody>();
            if (field == null) rules = new OperationRules(state, disposal.Director.Tuning);
        }
        private void FixedUpdate() { if (!Sinking && rules != null) rules.Tick(Time.fixedDeltaTime, 0f, false); }
        private void OnDestroy() { if (owner != null) owner.Forget(this); }
    }

    /// <summary>The one R owner: hold R at a corpse to pack it into a body bag where it lies (consumes one bag; the bag
    /// is the same ragdoll, wrapped). A dead patient stays on the table until a player takes him (LMB grab or R; review
    /// G35 M1). Disposal only after a physical drop into River/Lake/Canal water.</summary>
    [DefaultExecutionOrder(300)]
    public sealed class CaptureCorpseDisposal : MonoBehaviour
    {
        public const float Reach = 3f, PackSeconds = 1f, MinDisposalDepth = 0.35f;
        public CaptureDirector Director { get; private set; }
        public int Stock = 2;
        public int Disposed { get; private set; }
        public string LastDisposed { get; private set; }
        public readonly List<CaptureCorpse> Corpses = new();
        public readonly List<CaptureWitnessHook> WitnessHooks = new();
        public event Action<CaptureWitnessHook> WitnessCarryHook;
        /// <summary>The corpse under the crosshair (in reach), or null.</summary>
        public CaptureCorpse Aimed { get; private set; }
        /// <summary>The crosshair is on the dead patient still lying on the table.</summary>
        public bool AimedTablePatient { get; private set; }
        public float PackProgress => held / PackSeconds;
        public CaptureCorpseHands Hands { get; private set; }
        private float held;
        private object packing;
        private readonly List<CaptureCorpse> scratch = new();
        private readonly List<CaptureNpc> npcScratch = new();
        public string Hint
        {
            get
            {
                if (Hands != null && Hands.Carrying != null) return "Мешок с телом в руках · E или G — положить · ЛКМ — бросить";
                if (AimedTablePatient)
                    return StrapsOpen(Director.Table.State) ? "Труп на столе · ЛКМ — снять со стола · держи R — сразу в мешок (мешков: " + Stock + ")"
                        : "Труп пристёгнут · у стола E → ПОДГОТОВКА: расстегни все ремни";
                if (Aimed == null) return null;
                if (Aimed.Bagged) return "Мешок с телом · E — поднять и нести · ЛКМ — тащить";
                return Stock > 0 ? "Труп · ЛКМ — тащить · держи R — упаковать в мешок (мешков: " + Stock + ")" : "Мешки кончились — тело можно тащить ЛКМ";
            }
        }
        public void Init(CaptureDirector director)
        {
            Director = director;
            Hands = gameObject.GetComponent<CaptureCorpseHands>();
            if (Hands == null) Hands = gameObject.AddComponent<CaptureCorpseHands>();
            Hands.Init(this);
        }
        public void Forget(CaptureCorpse corpse) => Corpses.Remove(corpse);
        public CaptureCorpse Register(GameObject source, CaptureFacts facts, OperationState state, CaptureNpc field = null)
        {
            var corpse = source.GetComponent<CaptureCorpse>(); if (corpse == null) corpse = source.AddComponent<CaptureCorpse>();
            corpse.Bind(this, facts, state, field); if (!Corpses.Contains(corpse)) Corpses.Add(corpse); return corpse;
        }
        public static bool StrapsOpen(OperationState state)
        { if (state == null) return false; if (state.restraints != null) foreach (bool closed in state.restraints) if (closed) return false; return true; }

        /// <summary>The dead patient on the table, all straps open: he leaves the table as the network ragdoll (only on a
        /// player's act: the LMB grab or R).</summary>
        public CaptureCorpse TakeOffTable()
        {
            var table = Director.Table; var facts = Director.Bridge.PatientFacts;
            if (table == null || !table.HasPatient || table.State == null || table.State.alive || !StrapsOpen(table.State) || facts == null) return null;
            var state = table.State;
            var body = table.ServerDetachCorpse();
            if (body == null) return null;
            Director.Bridge.PatientFacts = null;
            Debug.Log("[CAPTURE] corpse " + facts.patientId + " taken off the table by the player");
            return Register(body.gameObject, facts, state);
        }

        private void Update()
        {
            if (Director == null || !Director.Ready || Director.Table == null || !Director.Table.IsServerInitialized) return;
            npcScratch.Clear(); npcScratch.AddRange(CaptureNpc.All);
            foreach (var npc in npcScratch)
                if (npc != null && !npc.Alive && !npc.Admitted && npc.GetComponent<CaptureCorpse>() == null) Register(npc.gameObject, npc.Facts, npc.State, npc);
            Aimed = null; AimedTablePatient = false;
            var pawn = Director.Pawn; var key = OpsInput.Keyboard;
            bool active = pawn != null && pawn.Controlled && pawn.ViewCamera != null && !Director.Bridge.InTableMode && OpsInput.CursorLocked;
            if (active)
            {
                var ray = new Ray(pawn.ViewCamera.transform.position, pawn.ViewCamera.transform.forward);
                Aim(ray, out var corpse, out bool tablePatient);
                Aimed = corpse; AimedTablePatient = tablePatient;
                object target = corpse != null ? corpse : tablePatient ? Director.Table : null;
                bool can = key != null && key.rKey.isPressed && Hands.Carrying == null && Stock > 0 &&
                           (corpse != null ? !corpse.Bagged && !corpse.Sinking && !corpse.State.alive && !corpse.Held : tablePatient && StrapsOpen(Director.Table.State));
                if (can)
                {
                    if (!ReferenceEquals(packing, target)) { packing = target; held = 0f; }
                    held += Time.deltaTime;
                    if (held >= PackSeconds) TryPackAimed();
                }
                else { held = 0f; packing = null; }
            }
            else { held = 0f; packing = null; }
            scratch.Clear(); scratch.AddRange(Corpses);
            foreach (var corpse in scratch)
            {
                if (corpse == null || corpse.Sinking) continue;
                bool carrying = corpse.Held;
                if (carrying && !corpse.WasHeld)
                {
                    var hook = new CaptureWitnessHook { patientId = corpse.PatientId, districtId = corpse.Facts.districtId, bagged = corpse.Bagged, points = corpse.Bagged ? 2 : 10 };
                    WitnessHooks.Add(hook); WitnessCarryHook?.Invoke(hook);
                    Debug.Log("[CAPTURE WITNESS HOOK] " + hook.patientId + " bagged=" + hook.bagged + " points=" + hook.points + " (hook only)");
                }
                corpse.WasHeld = carrying;
                Vector3 point = corpse.Center;
                if (!carrying && WaterQuery.SurfaceAt(point, out float surface, out var kind) &&
                    (kind == WaterKind.River || kind == WaterKind.Lake || kind == WaterKind.Canal) && point.y <= surface + 0.1f &&
                    WaterQuery.Depth(point) >= MinDisposalDepth)
                    StartCoroutine(Sink(corpse, surface));
            }
        }

        /// <summary>First-person aim within Reach: a registered corpse, or the dead patient on the table.</summary>
        public void Aim(Ray ray, out CaptureCorpse corpse, out bool tablePatient)
        {
            corpse = null; tablePatient = false;
            var table = Director.Table;
            var hits = Physics.RaycastAll(ray, Reach, OvLayers.ShootMask & ~OperationSurgicalBones.Mask, QueryTriggerInteraction.Collide);
            Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
            foreach (var h in hits)
            {
                if (h.collider == null || (Director.Pawn != null && h.collider.transform.IsChildOf(Director.Pawn.transform))) continue;
                bool patient = table != null && table.HasPatient && table.PatientObject != null && h.collider.transform.IsChildOf(table.PatientObject.transform);
                if (patient) { tablePatient = table.State != null && !table.State.alive; return; }
                var c = h.collider.GetComponentInParent<CaptureCorpse>();
                if (c != null) { corpse = c; return; }
                if (!h.collider.isTrigger) return; // solid geometry in front
            }
        }

        public bool TryPackAimed()
        {
            held = 0f; packing = null;
            var corpse = Aimed;
            if (corpse == null && AimedTablePatient && Stock > 0) corpse = TakeOffTable();
            if (corpse == null || corpse.Bagged || corpse.Sinking || corpse.State.alive || corpse.Held || Stock <= 0) return false;
            if (Director.Pawn != null && Vector3.Distance(Director.Pawn.ViewCamera.transform.position, corpse.Center) > Reach + 0.5f) return false;
            if (corpse.FieldNpc != null) corpse = FromField(corpse);
            if (corpse == null || corpse.Ragdoll == null || !corpse.Ragdoll.ServerBag()) { Director.Toast("Не получилось упаковать", CaptureHud.Bad); return false; }
            Stock--;
            var ragdoll = corpse.GetComponent<NpcRagdoll>();
            Vector3 head = ragdoll.Landmark(NpcLandmark.Head), pelvis = ragdoll.Landmark(NpcLandmark.Pelvis);
            CaptureCloud.Spawn((head + pelvis) * 0.5f + Vector3.up * 0.05f, head - pelvis);
            Director.Toast("Тело в мешке. E — поднять и нести, ЛКМ — тащить. Отнеси к воде", CaptureHud.Neutral);
            Debug.Log("[CAPTURE] packed " + corpse.PatientId + " into a body bag; bags left " + Stock);
            return true;
        }

        /// <summary>A field corpse (the map NPC's offline ragdoll) becomes the network patient ragdoll where it lies, with the
        /// same identity, so every bag is the same kind of networked, saved, carried ragdoll.</summary>
        private CaptureCorpse FromField(CaptureCorpse field)
        {
            var npc = field.FieldNpc; var facts = field.Facts; var state = field.State;
            var source = npc != null && npc.Npc != null ? npc.Npc.PhysicalBody : null;
            Vector3 pelvis = source != null ? source.Landmark(NpcLandmark.Pelvis) : field.transform.position;
            Vector3 head = source != null ? source.Landmark(NpcLandmark.Head) : pelvis + field.transform.forward;
            Vector3 along = head - pelvis; along.y = 0f; if (along.sqrMagnitude < 1e-4f) along = Vector3.forward;
            var body = Instantiate(Director.Table.PatientPrefab, pelvis, Quaternion.LookRotation(along.normalized));
            InstanceFinder.ServerManager.Spawn(body.NetworkObject); NetworkSession.Active?.RegisterBody(body);
            var ragdoll = body.GetComponent<OperationPatientRagdoll>(); ragdoll.ServerCorpse();
            npc.Admitted = true;
            Corpses.Remove(field);
            var go = field.gameObject; Destroy(field); go.SetActive(false); Destroy(go);
            return Register(body.gameObject, facts, state);
        }

        private IEnumerator Sink(CaptureCorpse corpse, float surface)
        {
            corpse.Sinking = true;
            if (Hands != null && Hands.Carrying == corpse) Hands.Drop(false);
            Vector3 splash = corpse.Center; splash.y = surface;
            OperationVisuals.Splash(splash, 18, new Color(0.25f, 0.65f, 0.9f)); Sfx.PlayAt(SfxIds.WaterJumpIn, splash);
            foreach (var collider in corpse.GetComponentsInChildren<Collider>(true)) collider.enabled = false;
            float end = Time.time + 1.2f;
            while (corpse != null && Time.time < end)
            {
                foreach (var body in corpse.GetComponentsInChildren<Rigidbody>())
                    if (!body.isKinematic) body.linearVelocity = new Vector3(body.linearVelocity.x * 0.8f, -1.5f, body.linearVelocity.z * 0.8f);
                yield return new WaitForFixedUpdate();
            }
            if (corpse == null) yield break;
            string id = corpse.PatientId; corpse.EvidenceActive = false;
            foreach (var trash in Director.Bridge.Trash) if (trash != null && trash.TryGetComponent<CaptureTrash>(out var evidence) && evidence.PatientId == id) evidence.PatientId = "";
            Director.AfterRemove(id); Disposed++; LastDisposed = id;
            var network = corpse.GetComponent<NetworkObject>();
            if (network != null && network.IsSpawned) InstanceFinder.ServerManager.Despawn(network);
            else { corpse.gameObject.SetActive(false); Destroy(corpse.gameObject); }
            Debug.Log("[CAPTURE DISPOSED] " + id + (corpse.Bagged ? " (bagged)" : "") + " evidence cleared, identity resolved");
        }

        public List<CaptureCorpseSave> Snapshot()
        {
            var result = new List<CaptureCorpseSave>();
            foreach (var corpse in Corpses)
            {
                if (corpse == null || corpse.FieldNpc != null || corpse.Sinking) continue; // field corpses use CaptureNpcSave
                var data = new CaptureCorpseSave { facts = corpse.Facts, operation = corpse.State, bagged = corpse.Bagged, held = corpse.Held, position = corpse.transform.position, rotation = corpse.transform.rotation };
                var ragdoll = corpse.Ragdoll;
                if (ragdoll != null && ragdoll.Active)
                {
                    data.bonePositions = new Vector3[ragdoll.BoneCount]; data.boneRotations = new Quaternion[ragdoll.BoneCount];
                    for (int i = 0; i < ragdoll.BoneCount; i++) { data.bonePositions[i] = ragdoll.Bone(i).position; data.boneRotations[i] = ragdoll.Bone(i).rotation; }
                }
                result.Add(data);
            }
            return result;
        }

        /// <summary>Saved corpses come back as the network patient ragdoll at their pose; bagged ones are packed again
        /// (laid straight where they were: a bag carried at save time lies on the ground under it).</summary>
        public void Restore(List<CaptureCorpseSave> saved, int stock)
        {
            Stock = Mathf.Max(0, stock); if (saved == null) return;
            foreach (var data in saved)
            {
                if (data == null || data.facts == null || data.operation == null || data.operation.alive) continue;
                Director.Facts[data.facts.patientId] = data.facts; Director.Registry.EnsureOperationPatient(data.facts.patientId, data.operation);
                var body = Instantiate(Director.Table.PatientPrefab, data.position, data.rotation);
                InstanceFinder.ServerManager.Spawn(body.NetworkObject); NetworkSession.Active?.RegisterBody(body);
                var ragdoll = body.GetComponent<OperationPatientRagdoll>(); ragdoll.ServerCorpse();
                if (data.bonePositions != null && data.boneRotations != null && data.bonePositions.Length == ragdoll.BoneCount && data.boneRotations.Length == ragdoll.BoneCount)
                    for (int i = 0; i < ragdoll.BoneCount; i++)
                    { var bone = ragdoll.Bone(i).GetComponent<Rigidbody>(); bone.position = data.bonePositions[i]; bone.rotation = data.boneRotations[i]; bone.linearVelocity = Vector3.zero; bone.angularVelocity = Vector3.zero; ragdoll.Bone(i).SetPositionAndRotation(data.bonePositions[i], data.boneRotations[i]); }
                ragdoll.ServerCorpse();
                Register(body.gameObject, data.facts, data.operation);
                if (data.bagged) ragdoll.ServerBag(data.bonePositions == null);
            }
        }
    }

    /// <summary>Hands-on corpse actions read before the grabbers (order -250): LMB on the dead, unstrapped table patient
    /// takes him off the table so the normal grab holds him; E lifts a body bag and carries it (the same server hold as
    /// the LMB grab, on its middle, at carry height, held across the view), E/G puts it down, LMB throws it: round 3, a
    /// charged throw (ThrowCharge: hold LMB longer = stronger, a tap is a gentle toss; the bag is heavy, so its top speed
    /// is the old 4.5 m/s).</summary>
    [DefaultExecutionOrder(-250)]
    public sealed class CaptureCorpseHands : MonoBehaviour
    {
        public const float CarryHeight = 1.0f, CarryForward = 0.85f, CarryBelowEye = 0.72f, ThrowSpeed = 4.5f, ThrowLift = 1.6f;
        /// <summary>Round 2 (Fedya: "slow down to the speed the bag can follow"): the player's speed cap while carrying a
        /// bag in his arms, from the cl carry-speed measurement (see CAPTURE_DELIVERY_STAGE_A_HOWTO_RU / PROGRESS log).</summary>
        public const float CarrySpeed = 3.0f;
        /// <summary>Dev measurement only: a different carry cap (m/s) while &gt; 0.</summary>
        public static float CarrySpeedOverride = -1f;
        public static float CarryCap => CarrySpeedOverride > 0f ? CarrySpeedOverride : CarrySpeed;
        /// <summary>The hand point moves toward the carry point at most this fast (above the walking cap, so it never trails).</summary>
        public static float CarryTargetSpeed => Mathf.Max(3f, CarryCap * 1.3f);
        /// <summary>The hand (hold target) point, world.</summary>
        public Vector3 HandPoint => target;
        public const float EndSpring = 40f, EndDamping = 7f, EndMaxAccel = 30f, ArmsShare = 0.6f, LiftSpring = 25f, LiftDamping = 6f;
        /// <summary>Round 2: the arms carry the whole bag along with the hand (horizontal velocity matching, per second and its
        /// acceleration limit), so walking does not leave it trailing on the hold's spring alone.</summary>
        public const float FollowGain = 9f, FollowMaxAccel = 25f;
        private Vector3 lastTarget; private bool hasLastTarget;
        private static readonly System.Reflection.FieldInfo ProfileField = typeof(NetworkPhysicsBody).GetField("profile", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
        /// <summary>The hold's damping coefficient (GrabPhysicsSolver.TryCalculate: 2·ratio·sqrt(spring·mass), on the
        /// ABSOLUTE point velocity): fed forward with the hand's velocity, the hold damps relative to the moving hand
        /// instead of braking the bag ~0.33 s behind it.</summary>
        private static float HoldDamping(NetworkPhysicsBody body)
        {
            var profile = ProfileField != null ? ProfileField.GetValue(body) as OnlyVolunteers.Player.Physics.GrabPhysicsProfile : null;
            if (profile == null || body.Body == null) return 0f;
            return 2f * profile.DampingRatio * Mathf.Sqrt(profile.SpringStrength * Mathf.Max(0.01f, body.Body.mass));
        }
        private CaptureCorpseDisposal disposal;
        private NetworkGrabber grabber;
        private uint holdId = 0x40000000u, sequence;
        private KccFirstPersonInput input;
        private Vector3 target;
        public CaptureCorpse Carrying { get; private set; }
        /// <summary>Round 3: when the LMB charge of a throw started (unscaled time), -1 while not charging.</summary>
        private float chargeSince = -1f;
        /// <summary>The throw charge 0..1 while LMB is held with a bag in the arms, -1 otherwise.</summary>
        public float ThrowChargeShown => Carrying != null && chargeSince >= 0f ? ThrowCharge.FromHold(Time.unscaledTime - chargeSince) : -1f;
        public void Init(CaptureCorpseDisposal owner) => disposal = owner;

        private CaptureDirector D => disposal != null ? disposal.Director : null;

        private void Update()
        {
            var d = D;
            if (d == null || !d.Ready || d.Table == null || !d.Table.IsServerInitialized || d.Pawn == null) return;
            if (grabber == null) grabber = d.Pawn.GetComponent<NetworkGrabber>();
            var key = OpsInput.Keyboard; var mouse = OpsInput.Mouse;
            if (Carrying != null)
            {
                if (Carrying.Body == null || !Carrying.Body.HasHolder || Carrying.Sinking) { Carrying = null; return; }
                if (input == null) input = d.Pawn.GetComponent<KccFirstPersonInput>();
                OperationPlayerSpeed.Request(input, this, CarryCap);
                if (key != null && (key.eKey.wasPressedThisFrame || key.gKey.wasPressedThisFrame)) { GreyboxInput.UseE(); Drop(false); }
                else if (mouse != null)
                {
                    // Charged throw: LMB down starts the charge, LMB up throws with it.
                    if (mouse.leftButton.wasPressedThisFrame) chargeSince = Time.unscaledTime;
                    if (chargeSince >= 0f && mouse.leftButton.wasReleasedThisFrame) Drop(true, ThrowCharge.FromHold(Time.unscaledTime - chargeSince));
                    else if (chargeSince >= 0f && !mouse.leftButton.isPressed) chargeSince = -1f;
                }
                return;
            }
            bool active = d.Pawn.Controlled && d.Pawn.ViewCamera != null && !d.Bridge.InTableMode && OpsInput.CursorLocked;
            if (!active || key == null || mouse == null) return;
            var ray = new Ray(d.Pawn.ViewCamera.transform.position, d.Pawn.ViewCamera.transform.forward);
            // A field tool in hand: LMB belongs to the tool (round 2), only empty hands take a body off the table.
            bool lmb = mouse.leftButton.wasPressedThisFrame && (d.Kit == null || d.Kit.Tool == FieldTool.Hands), e = key.eKey.wasPressedThisFrame;
            if (!lmb && !e) return;
            disposal.Aim(ray, out var corpse, out bool tablePatient);
            if (lmb && tablePatient)
            {
                // The grabbers read the same press after this: the body is a free ragdoll by then.
                if (CaptureCorpseDisposal.StrapsOpen(d.Table.State) && disposal.TakeOffTable() != null) Physics.SyncTransforms();
                else d.Toast("Сначала расстегни все ремни (у стола E → ПОДГОТОВКА)", CaptureHud.Warn);
            }
            if (e && corpse != null && corpse.Bagged && !corpse.Sinking && !corpse.Held && StartCarry(corpse)) GreyboxInput.UseE();
        }

        private Vector3 CarryPoint()
        {
            var eye = D.Pawn.ViewCamera.transform;
            Vector3 flat = eye.forward; flat.y = 0f; flat = flat.sqrMagnitude > 1e-4f ? flat.normalized : D.Pawn.transform.forward;
            Vector3 at = eye.position + flat * CarryForward + Vector3.down * CarryBelowEye;
            at.y = Mathf.Max(at.y, Mathf.Min(eye.position.y - 0.35f, D.Pawn.Position.y + CarryHeight)); // in the arms, about waist high
            return at;
        }

        private bool StartCarry(CaptureCorpse corpse)
        {
            if (grabber == null || corpse.Body == null || corpse.Ragdoll == null || !corpse.Ragdoll.Active) return false;
            var ragdoll = corpse.GetComponent<NpcRagdoll>();
            Vector3 middle = ragdoll.CenterOfMass;
            holdId++; if (holdId == 0) holdId = 0x40000000u; sequence = 0;
            if (!corpse.Body.TryAcquire(grabber, holdId, middle, middle)) return false;
            target = middle; Carrying = corpse; hasLastTarget = false;
            // Both arms under the bag: no tool in hand (G puts the bag down and must not drop a hotbar item).
            D.Kit?.Select(FieldTool.Hands, false);
            Debug.Log("[CAPTURE] E: carrying body bag " + corpse.PatientId);
            return true;
        }

        public void Drop(bool throwIt, float charge = 0f)
        {
            var corpse = Carrying; Carrying = null; chargeSince = -1f;
            if (corpse == null || corpse.Body == null) return;
            corpse.Body.Release(grabber, holdId);
            if (!throwIt) return;
            var eye = D.Pawn.ViewCamera.transform;
            var ragdoll = corpse.GetComponent<NpcRagdoll>();
            float mass = 0f;
            for (int i = 0; i < ragdoll.PartCount; i++) { var b = ragdoll.BodyOf(i); if (b != null) mass += b.mass; }
            // The shared rule (ThrowCharge): this host-side hold is the server, the charge is clamped there too. A body always
            // counts as heavy (its full charge is the old, playtested 4.5 m/s), whatever the game masses of its ragdoll parts.
            Vector3 aim = eye.forward;
            ThrowCharge.Velocity(aim.x, aim.y, aim.z, ThrowCharge.Clamp(charge), Mathf.Max(mass, ThrowCharge.HeavyMass), out float vx, out float vy, out float vz);
            Vector3 velocity = new Vector3(vx, vy, vz);
            for (int i = 0; i < ragdoll.PartCount; i++) { var b = ragdoll.BodyOf(i); if (b != null && !b.isKinematic) b.linearVelocity = velocity; }
            if (!corpse.Body.Body.isKinematic) corpse.Body.Body.linearVelocity = velocity;
            Debug.Log($"[CAPTURE] LMB: threw body bag {corpse.PatientId} charge={charge:F2} speed={velocity.magnitude:F1} m/s");
        }

        private void FixedUpdate()
        {
            if (Carrying == null || Carrying.Body == null || D == null || D.Pawn == null) return;
            // The hand moves to carry height in front, a little at a time (never a jump that breaks the hold).
            target = Vector3.MoveTowards(target, CarryPoint(), CarryTargetSpeed * Time.fixedDeltaTime);
            Vector3 handVelocity = hasLastTarget ? (target - lastTarget) / Time.fixedDeltaTime : Vector3.zero;
            handVelocity.y = 0f; lastTarget = target; hasLastTarget = true;
            sequence++;
            Carrying.Body.SetTarget(grabber, holdId, sequence, target);
            if (Carrying.Body.Body != null && !Carrying.Body.Body.isKinematic) Carrying.Body.Body.AddForce(handVelocity * HoldDamping(Carrying.Body), ForceMode.Force);
            // Both arms under it: the head end and the feet end are held level, across the view (the hand on the middle
            // carries the weight; these soft springs only steady the ends, they are limited like a person's arms).
            var ragdoll = Carrying.GetComponent<NpcRagdoll>();
            Vector3 pelvis = ragdoll.Landmark(NpcLandmark.Pelvis), head = ragdoll.Landmark(NpcLandmark.Head);
            Vector3 feet = (ragdoll.Landmark(NpcLandmark.LeftAnkle) + ragdoll.Landmark(NpcLandmark.RightAnkle)) * 0.5f;
            Vector3 along = head - feet; along.y = 0f;
            if (along.sqrMagnitude < 1e-4f) return;
            Vector3 right = D.Pawn.ViewCamera.transform.right; right.y = 0f; right.Normalize();
            if (Vector3.Dot(along, right) < 0f) right = -right;
            Vector3 middle = ragdoll.CenterOfMass;
            Vector3 headGoal = middle + right * Vector3.Distance(head, middle), feetGoal = middle - right * Vector3.Distance(feet, middle);
            headGoal.y = feetGoal.y = middle.y;
            var profile = ragdoll.Profile;
            Vector3 baseVelocity = ragdoll.MainBody != null ? ragdoll.MainBody.linearVelocity : Vector3.zero;
            // ...and the arms bear part of the weight, up to the carry height (the hand's hold alone sags with the grab profile).
            float lift = Mathf.Clamp(Physics.gravity.magnitude * ArmsShare + (target.y - middle.y) * LiftSpring - baseVelocity.y * LiftDamping, 0f, Physics.gravity.magnitude * 1.5f);
            for (int i = 0; i < ragdoll.PartCount; i++)
            {
                var part = ragdoll.BodyOf(i); if (part == null || part.isKinematic) continue;
                Vector3 slip = handVelocity - part.linearVelocity; slip.y = 0f;
                part.AddForce(Vector3.up * lift + Vector3.ClampMagnitude(slip * FollowGain, FollowMaxAccel), ForceMode.Acceleration);
            }
            for (int i = 0; i < ragdoll.PartCount; i++)
            {
                var kind = profile.Parts[i].Kind;
                bool isHead = kind == NpcRagdollProfile.Kind.Head, isFoot = kind == NpcRagdollProfile.Kind.Calf;
                if (!isHead && !isFoot) continue;
                var b = ragdoll.BodyOf(i); if (b == null || b.isKinematic) continue;
                Vector3 goal = isHead ? headGoal : feetGoal + (b.worldCenterOfMass - feet);
                Vector3 accel = (goal - b.worldCenterOfMass) * EndSpring - (b.linearVelocity - baseVelocity) * EndDamping;
                b.AddForce(Vector3.ClampMagnitude(accel, EndMaxAccel), ForceMode.Acceleration);
            }
        }

        private void OnDisable() { if (Carrying != null) Drop(false); }

        private void OnGUI()
        {
            float charge = ThrowChargeShown;
            if (charge >= 0f && Time.unscaledTime - chargeSince > 0.12f) ThrowChargeIndicator.Draw(charge);
        }
    }
}
