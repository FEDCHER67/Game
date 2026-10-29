using System.Collections.Generic;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Player;
using OnlyVolunteers.Story;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Economy
{
    /// <summary>
    /// The workshop mechanic (Workshop_W86; Fedya 29.10): a character standing at his point by the desk and pit stairs, and
    /// the E conversation with him (every machine, IMGUI in the style of the pharmacy counter). Lines depend on the state the
    /// server published (MechanicDialogue): a short chat line, the M06 task (accept / hand the rival over: the existing
    /// StoryMechanic request, so the story logic stays StoryDirector's), "Улучшить бусик" once the workshop is open (M06
    /// done or the DEV unlock), "Пока". "Улучшить бусик" asks WorkshopServiceV01 to put the team van on the lift; the session
    /// owner then sees the upgrade screen (WorkshopUpgradeRows: engine / handling / brakes tiers 0-III with their catalogue
    /// prices and effects; the cargo body: capacity I / II, containment I / II, storage greyed) and "Готово" lowers the van. Leaving the screen (Esc / E,
    /// walking off) also lowers it.
    /// The character: <see cref="ModelPrefab"/> = the dedicated MECHANIC_W86 v01 (pot belly, wrench always in the right hand;
    /// Characters/Mechanic_W86/Mechanic_W86_v01.prefab, set by the integrator); without it an adult crowd worker stands in.
    /// Either way he is named <see cref="MechanicId"/> and keeps this identity (M06, saves, the conversation). His movement
    /// and actions belong to <see cref="WorkshopMechanicBrainV01"/> alone (route, attention, gags, the upgrade performance;
    /// server-owned, synced); this component spawns the body and runs the E conversation.
    /// </summary>
    // E (29.10 fix): runs before the pawn interactor, the van seat and the gates (GreyboxInteractor 0, VadimGate -200) so
    // that looking at him the press talks; after the body-bag hands (-250), which drop a carried bag on E. Reach is the pure
    // MechanicTalkReach rule (flat from his body wherever he walks, or the crosshair on him), never his physics capsule.
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-210)]
    public sealed class WorkshopMechanicV01 : MonoBehaviour
    {
        /// <summary>The mechanic's stable identity (the model can be replaced, the id and the anchor stay).</summary>
        public const string MechanicId = "WORKSHOP_MECHANIC";
        public const float TalkRadius = MechanicTalkReach.Radius;

        [Tooltip("Where he stands (the StoryAnchor Workshop.Mechanic of W86_Workshop_Anchors).")]
        public Transform Spot;
        [Tooltip("A dedicated mechanic model (later, after the reference is approved). Empty = an adult crowd worker template.")]
        public GameObject ModelPrefab;
        [Tooltip("Crowd template preference (visual / name contains), first match wins; CONSTR is the M06 rival's look, so last.")]
        public string[] PreferTemplates = { "MUZHIK", "FOREMAN", "PROM_", "WORKER", "CONSTR" };

        private GameObject body;
        private float nextSpawnTry;
        private bool warned;
        // conversation
        private enum Mode : byte { Closed, Talk, Upgrade }
        private Mode mode = Mode.Closed;
        private int selected, turn;
        private string line = "", status = "";
        private bool statusOk, busy, doneSent;
        private float statusUntil;
        private KccFirstPersonInput walker;
        private bool savedMove, savedLook, savedVisible;
        private CursorLockMode savedLock;
        private string prompt = "";
        private GUIStyle label, title, small, button, row;
        private Vector2 scroll;

        private Vector3 SpotPos => Spot != null ? Spot.position : transform.position;
        /// <summary>Where he stands now (he walks his route): the conversation is measured from here.</summary>
        private Vector3 TalkPos => body != null ? body.transform.position : SpotPos;
        /// <summary>His spawned body (null until spawned).</summary>
        public Transform Body => body != null ? body.transform : null;
        private Vector3 openedAt;

        private void Awake()
        {
            // the one movement owner (the integrator adds it with the route; a scene without it still gets one)
            if (!TryGetComponent(out WorkshopMechanicBrainV01 _)) gameObject.AddComponent<WorkshopMechanicBrainV01>();
        }

        private void OnDisable()
        {
            if (mode != Mode.Closed) Close(false);
            if (body != null) Destroy(body);
        }

        // ================================================================== the character

        private void Spawn()
        {
            if (body != null || Time.unscaledTime < nextSpawnTry) return;
            nextSpawnTry = Time.unscaledTime + 2f;
            GameObject source = ModelPrefab;
            bool crowd = false;
            if (source == null) { source = PickTemplate(); crowd = source != null; }
            if (source == null)
            {
                if (!warned) { warned = true; Debug.LogWarning("[WORKSHOP] no crowd template for the mechanic (placeholder): only the anchor stands there", this); }
                return;
            }
            Transform at = Spot != null ? Spot : transform;
            GameObject go = Instantiate(source, at.position, at.rotation, transform);
            go.name = MechanicId + (crowd ? " (placeholder: " + source.name + ")" : " (" + source.name + ")");
            if (!crowd)
            {
                // the dedicated model: its presenter plays the brain's actions; no crowd driver, no physics push
                foreach (Rigidbody rb in go.GetComponentsInChildren<Rigidbody>(true)) rb.isKinematic = true;
                if (go.GetComponent<MechanicW86PresenterV01>() == null && go.GetComponent<NpcAnimDriver>() == null && go.GetComponentInChildren<Animator>(true) != null)
                    go.AddComponent<NpcAnimDriver>();
            }
            if (crowd)
            {
                // presentation only: no crowd walk, no NPC brain (he cannot be scared off, stunned or captured), no physics
                if (go.TryGetComponent(out CrowdWalker w)) Destroy(w);
                if (go.TryGetComponent(out GreyboxNpc npc)) npc.enabled = false;
                foreach (var tag in go.GetComponentsInChildren<OnlyVolunteers.Clinic.PatientTag>(true)) Destroy(tag);
                foreach (Rigidbody rb in go.GetComponentsInChildren<Rigidbody>(true)) rb.isKinematic = true;
                if (go.TryGetComponent(out CharacterController cc)) cc.enabled = true; // a solid capsule: players walk round him
                if (go.GetComponent<NpcAnimDriver>() == null) go.AddComponent<NpcAnimDriver>();
            }
            go.SetActive(true);
            body = go;
            Debug.Log($"[WORKSHOP] mechanic {MechanicId} at {at.position} ({(crowd ? "placeholder from " : "model ")}{source.name})", this);
        }

        private GameObject PickTemplate()
        {
            var director = CrowdDirector.Instance;
            if (director == null || director.Templates == null) return null;
            foreach (string want in PreferTemplates)
                foreach (GameObject t in director.Templates)
                {
                    if (t == null || t.GetComponent<GreyboxNpc>() == null) continue;
                    string v = (OnlyVolunteers.Characters.Types.NpcSpawnTables.VisualOf(t) + " " + t.name).ToUpperInvariant();
                    if (v.Contains("KID") || v.Contains("CHILD") || v.Contains("POLICE")) continue;
                    if (v.Contains(want)) return t;
                }
            return PharmacyStaffPick();
        }

        private static GameObject PharmacyStaffPick() => OnlyVolunteers.Economy.Pharmacy.PharmacyStaffV01.PickTemplate();

        // ================================================================== input

        private OnlyVolunteers.Network.NetworkPlayer clientPlayer;
        private float nextClientLook, nextVanLook, nextRefusalLog;
        private OnlyVolunteers.Map.GreyboxVanSeat seat;
        private OnlyVolunteers.Map.GreyboxVanCargo cargo;
        private MechanicTalkRefusal lastRefusal;
        private static readonly RaycastHit[] SightHits = new RaycastHit[12];

        /// <summary>This machine's own player: the map pawn on the host / offline, the owned player object on a pure client
        /// (on a client the map pawn is the HOST's body: measuring from it, only the host's position could talk).</summary>
        private bool LocalPlayer(out Vector3 feet, out Transform eye, out bool mapPawn)
        {
            feet = default; eye = null; mapPawn = false;
            FishNet.Managing.NetworkManager nm = FishNet.InstanceFinder.NetworkManager;
            bool clientOnly = nm != null && nm.IsClientStarted && !nm.IsServerStarted;
            var capture = CaptureDirector.Instance;
            if (!clientOnly)
            {
                if (capture != null)
                {
                    if (capture.Pawn == null || !capture.Pawn.Controlled) return false;
                    feet = capture.Pawn.Position;
                    eye = capture.Pawn.ViewCamera != null ? capture.Pawn.ViewCamera.transform : null;
                    mapPawn = true;
                    return true;
                }
                Camera cam = Camera.main;
                if (cam == null) return false;
                eye = cam.transform;
                feet = cam.transform.position - Vector3.up * 1.6f;
                return true;
            }
            if ((clientPlayer == null || !clientPlayer.IsOwner) && Time.unscaledTime >= nextClientLook)
            {
                nextClientLook = Time.unscaledTime + 1f;
                clientPlayer = null;
                foreach (var p in FindObjectsByType<OnlyVolunteers.Network.NetworkPlayer>())
                    if (p != null && p.IsOwner && !p.ExternalControl) { clientPlayer = p; break; }
            }
            if (clientPlayer == null || !clientPlayer.IsOwner) return false;
            feet = clientPlayer.MotorPosition;
            eye = clientPlayer.ViewCamera != null ? clientPlayer.ViewCamera.transform : null;
            return true;
        }

        private Vector3? PlayerFeet() => LocalPlayer(out Vector3 feet, out _, out _) ? feet : (Vector3?)null;

        /// <summary>The team van right here offers E to the map pawn (get in, a cargo door, the inside handle, an item on
        /// the floor): then E talks only when the player looks at the mechanic.</summary>
        private bool VanOffersE(Vector3 feet)
        {
            if (Time.unscaledTime >= nextVanLook && (seat == null || cargo == null))
            {
                nextVanLook = Time.unscaledTime + 2f;
                seat = FindAnyObjectByType<OnlyVolunteers.Map.GreyboxVanSeat>();
                cargo = seat != null ? seat.GetComponent<OnlyVolunteers.Map.GreyboxVanCargo>() : FindAnyObjectByType<OnlyVolunteers.Map.GreyboxVanCargo>();
            }
            if (seat != null && seat.isActiveAndEnabled && seat.CanEnter) return true;
            if (cargo != null && cargo.isActiveAndEnabled && (cargo.AtInsideHandle(feet) || cargo.NearestDoor(feet) >= 0)) return true;
            return OnlyVolunteers.Inventory.OfflineWorldItem.Nearest(feet, 2.5f) != null;
        }

        /// <summary>A clear line from the eye to his chest (walls, the van, shelves block; his own body and the player don't).</summary>
        private bool SightClear(Vector3 eye)
        {
            Vector3 chest = TalkPos + Vector3.up * 1.2f;
            Vector3 d = chest - eye;
            float len = d.magnitude;
            if (len < 0.3f) return true;
            int n = Physics.RaycastNonAlloc(eye, d / len, SightHits, len, OnlyVolunteers.Map.OvLayers.ShootMask & ~(1 << OnlyVolunteers.Map.OvLayers.RemotePlayer), QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
            {
                Collider c = SightHits[i].collider;
                if (c == null || body != null && c.transform.IsChildOf(body.transform)) continue;
                if (SightHits[i].distance > len - 0.35f) continue; // at his chest
                return false;
            }
            return true;
        }

        private MechanicTalkInput TalkInput(bool hasPlayer, Vector3 feet, Transform eye, bool mapPawn, bool eTaken)
        {
            Vector3 at = TalkPos;
            var i = new MechanicTalkInput
            {
                HasPlayer = hasPlayer,
                MenuOpen = OnlyVolunteers.UI.OvMenuGate.Blocking,
                ETaken = eTaken,
                EconomyReady = EconomyClientView.Current != null && EconomyClientView.Current.ready,
            };
            if (!hasPlayer) return i;
            Vector3 d = feet - at;
            i.Dx = d.x; i.Dy = d.y; i.Dz = d.z;
            if (eye != null)
            {
                Vector3 e = eye.position - at, v = eye.forward;
                i.HasView = true;
                i.EyeX = e.x; i.EyeY = e.y; i.EyeZ = e.z;
                i.ViewX = v.x; i.ViewY = v.y; i.ViewZ = v.z;
                // only worth a raycast when the aim is what reaches him
                i.SightClear = MechanicTalkReach.Flat(d.x, d.z) <= MechanicTalkReach.Radius ||
                               MechanicTalkReach.Aimed(i.EyeX, i.EyeY, i.EyeZ, i.ViewX, i.ViewY, i.ViewZ) && SightClear(eye.position);
            }
            // the van's E belongs to the map pawn's interactor only (a client has none here)
            i.VanOffersE = mapPawn && MechanicTalkReach.Flat(d.x, d.z) <= MechanicTalkReach.AimRadius + 1f && VanOffersE(feet);
            return i;
        }

        /// <summary>E this frame, from the Input System (as the other map menus) or, as a fallback, the legacy input the
        /// pawn interactor reads (one press is one E either way).</summary>
        private static bool EPressed(Keyboard key)
        {
            if (key != null && key.eKey.wasPressedThisFrame) return true;
#if ENABLE_LEGACY_INPUT_MANAGER
            if (Input.GetKeyDown(KeyCode.E)) return true;
#endif
            return false;
        }

        private void Update()
        {
            Spawn();
            prompt = "";
            WorkshopServiceV01 lift = WorkshopServiceV01.Instance;
            bool hasPlayer = LocalPlayer(out Vector3 feet, out Transform eye, out bool mapPawn);
            Vector3? me = hasPlayer ? feet : (Vector3?)null;
            Keyboard key = OpsInput.Keyboard;
            if (mode != Mode.Closed)
            {
                OnlyVolunteers.UI.OvMenuGate.Blocking = true;
                // walked off: beyond the leash from him AND from where the talk started (he may walk to the lift box)
                if (!me.HasValue || !MechanicTalkReach.KeepOpen(me.Value.x - TalkPos.x, me.Value.z - TalkPos.z, me.Value.x - openedAt.x, me.Value.z - openedAt.z)) { Close(true); return; }
                // the upgrade screen follows the server's session (it may end on its own: owner left, server stop)
                if (mode == Mode.Upgrade && lift != null && !lift.MineSession && !busy) { mode = Mode.Talk; selected = 0; }
                if (key == null) return;
                if (key.escapeKey.wasPressedThisFrame) { OnlyVolunteers.UI.OvMenuGate.ConsumeEscape(); Close(true); return; }
                if (EPressed(key) || key.tabKey.wasPressedThisFrame) { GreyboxInput.UseE(); Close(true); return; }
                int n = mode == Mode.Talk ? Options().Count : Rows().Count + 1;
                if (n > 0)
                {
                    if (key.upArrowKey.wasPressedThisFrame || key.wKey.wasPressedThisFrame) selected = (selected + n - 1) % n;
                    if (key.downArrowKey.wasPressedThisFrame || key.sKey.wasPressedThisFrame) selected = (selected + 1) % n;
                    selected = Mathf.Clamp(selected, 0, n - 1);
                    int digit = Digit(key);
                    if (digit > 0 && digit <= n) { selected = digit - 1; Choose(selected); }
                    else if (key.enterKey.wasPressedThisFrame || key.numpadEnterKey.wasPressedThisFrame || key.spaceKey.wasPressedThisFrame) Choose(selected);
                }
                return;
            }
            bool pressed = EPressed(key);
            // cheap early out: far from him nothing is shown or measured
            if (!me.HasValue || (me.Value - TalkPos).sqrMagnitude > (MechanicTalkReach.AimRadius + 2f) * (MechanicTalkReach.AimRadius + 2f)) return;
            MechanicTalkRefusal shown = MechanicTalkReach.Check(TalkInput(hasPlayer, feet, eye, mapPawn, false));
            switch (shown)
            {
                case MechanicTalkRefusal.None:
                    prompt = lift != null && lift.MineSession ? "<b>E</b> — механик: вернуться к подъёмнику" : "<b>E</b> — поговорить с механиком";
                    break;
                case MechanicTalkRefusal.EconomyLoading:
                    prompt = "Механик: «Секунду…» (экономика загружается)";
                    break;
                case MechanicTalkRefusal.VanOwnsE:
                    prompt = "Наведись на механика и нажми <b>E</b> — поговорить";
                    break;
            }
            if (!pressed) return;
            MechanicTalkRefusal r = shown == MechanicTalkRefusal.None && !GreyboxInput.EFree ? MechanicTalkRefusal.ETaken : shown;
            if (r != MechanicTalkRefusal.None) { NoteRefusal(r, me.Value); return; }
            GreyboxInput.UseE();
            Open();
        }

        /// <summary>E pressed near him and nothing opened: say why in the log (once per reason and half second), so a
        /// playtest report "E does nothing" shows the cause.</summary>
        private void NoteRefusal(MechanicTalkRefusal r, Vector3 me)
        {
            if (r == lastRefusal && Time.unscaledTime < nextRefusalLog) return;
            lastRefusal = r;
            nextRefusalLog = Time.unscaledTime + 0.5f;
            Vector3 d = me - TalkPos;
            Debug.Log($"[WORKSHOP] E near the mechanic did not open the talk: {r} (flat {MechanicTalkReach.Flat(d.x, d.z):0.00} m, dy {d.y:0.00}, " +
                      $"menu gate {OnlyVolunteers.UI.OvMenuGate.Blocking}, E free {GreyboxInput.EFree}, action {(WorkshopMechanicBrainV01.Instance != null ? WorkshopMechanicBrainV01.Instance.Action.ToString() : "-")})", this);
        }

        private static int Digit(Keyboard k)
        {
            if (k.digit1Key.wasPressedThisFrame) return 1;
            if (k.digit2Key.wasPressedThisFrame) return 2;
            if (k.digit3Key.wasPressedThisFrame) return 3;
            if (k.digit4Key.wasPressedThisFrame) return 4;
            if (k.digit5Key.wasPressedThisFrame) return 5;
            return 0;
        }

        // His movement (route, the lift box, attention, the upgrade performance) is WorkshopMechanicBrainV01's alone.

        private void Open()
        {
            WorkshopServiceV01 lift = WorkshopServiceV01.Instance;
            mode = lift != null && lift.MineSession ? Mode.Upgrade : Mode.Talk;
            selected = 0;
            doneSent = false;
            Vector3? at = PlayerFeet();
            openedAt = at ?? TalkPos;
            // the server learns who talks to him: he attends the talker and does no gags meanwhile (a menu stays local)
            lift?.Request(WorkshopRequestKind.Talk, "1", 0, null);
            EconomySnapshot snap = EconomyClientView.Current;
            line = snap != null ? MechanicDialogue.ChatLine(M06(snap), snap.workshopUnlocked, turn) : "";
            // the local player's own walker (a client's owned player, else the map pawn's), else the first live one
            walker = clientPlayer != null && clientPlayer.IsOwner ? clientPlayer.GetComponent<KccFirstPersonInput>() : null;
            if (walker == null && CaptureDirector.Instance != null && CaptureDirector.Instance.Pawn != null)
                walker = CaptureDirector.Instance.Pawn.GetComponentInParent<KccFirstPersonInput>() ?? CaptureDirector.Instance.Pawn.GetComponentInChildren<KccFirstPersonInput>();
            if (walker != null && !walker.isActiveAndEnabled) walker = null;
            if (walker == null)
                foreach (var k in FindObjectsByType<KccFirstPersonInput>())
                    if (k.isActiveAndEnabled) { walker = k; break; }
            if (walker != null)
            {
                savedMove = walker.MovementLocked; savedLook = walker.LookSuspended;
                walker.MovementLocked = true; walker.LookSuspended = true;
            }
            savedLock = Cursor.lockState; savedVisible = Cursor.visible;
            Cursor.lockState = CursorLockMode.None; Cursor.visible = true;
            OnlyVolunteers.UI.OvMenuGate.Blocking = true;
        }

        /// <summary>Leaving the conversation; leaving the upgrade screen also lowers the van ("Готово").</summary>
        private void Close(bool lowerIfMine)
        {
            if (mode == Mode.Closed) return;
            WorkshopServiceV01 lift = WorkshopServiceV01.Instance;
            if (lowerIfMine && lift != null && lift.MineSession && !doneSent) SendDone();
            mode = Mode.Closed;
            lift?.Request(WorkshopRequestKind.Talk, "0", 0, null);
            if (walker != null) { walker.MovementLocked = savedMove; walker.LookSuspended = savedLook; walker = null; }
            Cursor.lockState = savedLock; Cursor.visible = savedVisible;
            OnlyVolunteers.UI.OvMenuGate.Blocking = false;
        }

        private static JournalState M06(EconomySnapshot snap)
        {
            if (snap != null && snap.journal != null && snap.journal.missions != null)
                foreach (StoryJournalEntry m in snap.journal.missions) if (m.id == MissionId.M06.ToString()) return m.State;
            return JournalState.Locked;
        }

        private List<MechanicOption> Options()
        {
            EconomySnapshot snap = EconomyClientView.Current;
            return MechanicDialogue.Options(M06(snap), snap != null && snap.workshopUnlocked);
        }

        private List<WorkshopUpgradeRow> Rows()
        {
            List<WorkshopUpgradeRow> rows = WorkshopUpgradeRows.Build(EconomyClientView.Current);
            VanUpgradeConfig config = null;
            VanController v = FindAnyObjectByType<VanController>();
            if (v != null && v.TryGetComponent(out VanUpgrades up)) config = up.Config;
            foreach (WorkshopUpgradeRow r in rows)
                if (r.Kind == WorkshopUpgradeRows.VanBranchKind && !r.AtMax)
                    r.Effect = VanUpgradeConfig.DescribeProgression(config, Category(r.Branch), r.Tier + 1);
            return rows;
        }

        private static VanUpgradeCategory Category(VanBranch b) =>
            b == VanBranch.Engine ? VanUpgradeCategory.Engine : b == VanBranch.Handling ? VanUpgradeCategory.Handling : VanUpgradeCategory.Brakes;

        private void Choose(int index)
        {
            if (busy) return;
            if (mode == Mode.Talk)
            {
                List<MechanicOption> options = Options();
                if (index < 0 || index >= options.Count) return;
                switch (options[index])
                {
                    case MechanicOption.Chat:
                    {
                        turn++;
                        EconomySnapshot snap = EconomyClientView.Current;
                        line = MechanicDialogue.ChatLine(M06(snap), snap != null && snap.workshopUnlocked, turn);
                        break;
                    }
                    case MechanicOption.AcceptRival:
                    case MechanicOption.HandInRival:
                    {
                        TeamEconomy economy = TeamEconomy.Instance;
                        if (economy == null) { Show(false, "Экономика не запущена"); return; }
                        busy = true;
                        economy.Request(EconomyRequestKind.StoryMechanic, "", "", 0, (ok, text) => { busy = false; Show(ok, text); });
                        break;
                    }
                    case MechanicOption.UpgradeVan:
                    {
                        WorkshopServiceV01 lift = WorkshopServiceV01.Instance;
                        if (lift == null) { Show(false, "В этой мастерской нет подъёмника"); return; }
                        busy = true;
                        lift.Request(WorkshopRequestKind.Start, "", 0, (ok, text) =>
                        {
                            busy = false;
                            Show(ok, text);
                            if (ok) { mode = Mode.Upgrade; selected = 0; doneSent = false; }
                        });
                        break;
                    }
                    default:
                        Close(true);
                        break;
                }
                return;
            }
            // upgrade screen: rows, then "Готово"
            List<WorkshopUpgradeRow> rows = Rows();
            if (index >= rows.Count) { SendDone(); Close(false); return; }
            WorkshopUpgradeRow r = rows[index];
            WorkshopServiceV01 service = WorkshopServiceV01.Instance;
            if (service == null || r.Blocked.Length > 0 || r.AtMax) { if (r.Blocked.Length > 0) Show(false, r.Blocked); return; }
            if (service.Phase != LiftPhase.Up) { Show(false, WorkshopRules.Explain(WorkshopRefusal.NotRaised)); return; }
            busy = true;
            // valid selections are answered at the mechanic's Poof (aim -> puff -> result); the buttons stay off till then
            Show(true, "Механик прицеливается ключом…");
            service.Request(WorkshopRequestKind.Buy, r.Kind + "|" + r.Arg, r.Expected, (ok, text) => { busy = false; Show(ok, text); });
        }

        private void SendDone()
        {
            WorkshopServiceV01 lift = WorkshopServiceV01.Instance;
            if (lift == null || doneSent) return;
            doneSent = true;
            lift.Request(WorkshopRequestKind.Done, "", 0, (ok, text) => { if (!ok && !string.IsNullOrEmpty(text)) Toast(false, text); });
        }

        private void Show(bool ok, string text)
        {
            status = text ?? "";
            statusOk = ok;
            statusUntil = Time.unscaledTime + 5f;
            Toast(ok, status);
        }

        private static void Toast(bool ok, string text)
        {
            if (string.IsNullOrEmpty(text)) return;
            CaptureDirector.Instance?.Toast(text, ok ? CaptureHud.Good : CaptureHud.Warn, 4f);
        }

        // ================================================================== UI

        private void Styles()
        {
            if (label != null) return;
            label = new GUIStyle(GUI.skin.label) { fontSize = 18, richText = true, alignment = TextAnchor.MiddleLeft, wordWrap = true };
            label.normal.textColor = new Color(0.95f, 0.93f, 0.86f);
            small = new GUIStyle(label) { fontSize = 14 };
            small.normal.textColor = new Color(0.75f, 0.8f, 0.78f);
            title = new GUIStyle(label) { fontSize = 22, fontStyle = FontStyle.Bold, wordWrap = false };
            title.normal.textColor = new Color(1f, 0.78f, 0.35f);
            button = new GUIStyle(GUI.skin.button) { fontSize = 16, fontStyle = FontStyle.Bold, richText = true };
            row = new GUIStyle(GUI.skin.box);
        }

        private void OnGUI()
        {
            Styles();
            if (mode == Mode.Closed)
            {
                if (prompt.Length == 0) return;
                var p = new Rect(Screen.width * 0.1f, Screen.height * 0.66f, Screen.width * 0.8f, 40f);
                var s = new GUIStyle(label) { alignment = TextAnchor.MiddleCenter, fontSize = 19 };
                s.normal.textColor = new Color(0f, 0f, 0f, 0.85f);
                GUI.Label(new Rect(p.x + 2f, p.y + 2f, p.width, p.height), System.Text.RegularExpressions.Regex.Replace(prompt, "<.*?>", ""), s);
                s.normal.textColor = new Color(1f, 0.93f, 0.75f);
                GUI.Label(p, prompt, s);
                return;
            }
            float w = Mathf.Min(780f, Screen.width - 40f), h = Mathf.Min(mode == Mode.Talk ? 430f : 620f, Screen.height - 40f);
            var r = new Rect((Screen.width - w) * 0.5f, (Screen.height - h) * 0.5f, w, h);
            GUI.color = new Color(0.1f, 0.09f, 0.07f, 0.94f);
            GUI.DrawTexture(r, Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUILayout.BeginArea(new Rect(r.x + 18f, r.y + 12f, r.width - 36f, r.height - 24f));
            EconomySnapshot snap = EconomyClientView.Current;
            if (mode == Mode.Talk) DrawTalk(snap); else DrawUpgrade(snap, w);
            if (Time.unscaledTime < statusUntil && status.Length > 0)
                GUILayout.Label("<color=" + (statusOk ? "#5BE07A" : "#FF8A5B") + ">" + status + "</color>", label);
            GUILayout.Label(mode == Mode.Talk ? "Мышь или ↑/↓ и Enter (1–5) · E / Esc — уйти" : "Мышь или ↑/↓ и Enter · «Готово», E или Esc — опустить бусик и уйти", small);
            GUILayout.EndArea();
        }

        private void DrawTalk(EconomySnapshot snap)
        {
            GUILayout.Label("МЕХАНИК", title);
            if (line.Length > 0) GUILayout.Label(line, label);
            GUILayout.Space(8f);
            List<MechanicOption> options = Options();
            for (int i = 0; i < options.Count; i++)
            {
                string mark = i == selected ? "▶ " : "";
                GUI.enabled = !busy;
                if (GUILayout.Button(mark + (i + 1) + ". " + MechanicDialogue.Title(options[i]), button, GUILayout.Height(34f))) { selected = i; Choose(i); }
                GUI.enabled = true;
            }
            if (snap != null && !snap.workshopUnlocked && M06(snap) == JournalState.Completed)
                GUILayout.Label("<color=#FFB13B>Мастерская закрыта</color>", small);
        }

        private void DrawUpgrade(EconomySnapshot snap, float w)
        {
            WorkshopServiceV01 lift = WorkshopServiceV01.Instance;
            GUILayout.Label("МАСТЕРСКАЯ — бусик на подъёмнике", title);
            int balance = snap != null ? snap.balance : 0;
            string phase = lift == null ? "нет подъёмника" : lift.Phase == LiftPhase.Up ? "<color=#5BE07A>поднят</color>" :
                lift.Phase == LiftPhase.Raising ? $"поднимается… {lift.Height / Mathf.Max(0.01f, lift.Travel) * 100f:0}%" :
                lift.Phase == LiftPhase.Lowering ? "опускается…" : "внизу";
            GUILayout.Label("Подъёмник: " + phase + " · общий фонд <b>" + EconomyState.Money(balance) + "</b>", label);
            if (snap != null && snap.vanLegacyDebugProfile)
                GUILayout.Label("<color=#FFB13B>Бусик в отладочном профиле (старый максимум StartAtMax): покупки недоступны. Телефон → Магазин: «Перейти на прогрессию».</color>", small);
            GUILayout.Space(4f);
            scroll = GUILayout.BeginScrollView(scroll);
            List<WorkshopUpgradeRow> rows = Rows();
            string group = null;
            for (int i = 0; i < rows.Count; i++)
            {
                WorkshopUpgradeRow r = rows[i];
                if (r.Group != group) { group = r.Group; GUILayout.Label("<b>" + group + "</b>", small); }
                GUILayout.BeginHorizontal(row);
                string mark = i == selected ? "<color=#FFD24A>▶</color> " : "   ";
                string tiers = r.Single
                    ? (r.AtMax ? "<color=#5BE07A>— установлено</color>" : "<b>" + (r.NextPrice > 0 ? EconomyState.Money(r.NextPrice) : "—") + "</b>")
                    : EconomyPrices.TierName(r.Tier) + (r.AtMax ? " — максимум" : " → " + EconomyPrices.TierName(r.Tier + 1) + "  <b>" + EconomyState.Money(r.NextPrice) + "</b>");
                string afford = !r.AtMax && snap != null && r.NextPrice > snap.balance ? " <color=#FF4D5E>(не хватает)</color>" : "";
                GUILayout.BeginVertical();
                GUILayout.Label(mark + "<b>" + r.Title + "</b>  " + tiers + afford, label);
                if (r.Effect.Length > 0) GUILayout.Label("      " + r.Effect, small);
                if (r.Blocked.Length > 0 && !r.AtMax) GUILayout.Label("      <color=#FFB13B>" + r.Blocked + "</color>", small);
                GUILayout.EndVertical();
                GUI.enabled = !busy && r.Blocked.Length == 0 && !r.AtMax && lift != null && lift.Phase == LiftPhase.Up;
                if (GUILayout.Button("Купить", button, GUILayout.Width(90f), GUILayout.Height(32f))) { selected = i; Choose(i); }
                GUI.enabled = true;
                GUILayout.EndHorizontal();
            }
            GUILayout.EndScrollView();
            GUILayout.Space(6f);
            string doneMark = selected == rows.Count ? "▶ " : "";
            GUI.enabled = !busy;
            if (GUILayout.Button(doneMark + "Готово — опустить бусик", button, GUILayout.Height(36f))) { selected = rows.Count; Choose(rows.Count); }
            GUI.enabled = true;
        }
    }
}
