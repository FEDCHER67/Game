using System.Collections.Generic;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Characters.Types;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using UnityEngine;

namespace OnlyVolunteers.Economy.Pharmacy
{
    /// <summary>
    /// The city pharmacy's staff placeholder (Pharmacy_W86): ONE adult crowd NPC (a clone of an existing crowd template,
    /// no crowd walker) stands at the cash desk and, on a timer, walks the staff route counter -> behind the counter ->
    /// staff door -> stockroom -> rear door -> service yard, waits there and walks back. Walks on the real floor with its
    /// CharacterController (gravity, walls and closed doors collide; no teleporting through a wall), the existing
    /// NpcAnimDriver walks / idles it, the doors open for it (PharmacyDoorV01.Hold) only when it stands outside their sweep.
    /// It is an ordinary free GreyboxNpc: it flees, is stunned, captured and tied like anyone; the moment it is not free and
    /// calm the walker lets go of it for good (the GreyboxNpc owns it from then). Server only (the host spawns him once the
    /// capture save is loaded; free NPCs are not saved, so a new session spawns a new one). A captured / lost pharmacist
    /// is replaced after <see cref="RespawnSeconds"/> when no player is near (the counter itself needs no pharmacist).
    /// Opening hours (PharmacyHours, Fedya 29.10): at 20:00 he walks his route out to the service yard and goes home there
    /// (despawns once nobody is near the yard); at 08:00 he comes back - straight to the desk when nobody watches it, else
    /// in through the yard and the rear door. Nobody stands at the counter at night. Clients see him through
    /// PharmacyNetV01 (pose + walk speed, a presentation-only copy).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PharmacyStaffV01 : MonoBehaviour
    {
        [Tooltip("Route nodes (children of the anchors root): 0 = the cash desk ... last = the service yard.")]
        public Transform[] Route = new Transform[0];
        [Tooltip("Doors on the route: door i is passed between nodes DoorFrom[i] and DoorTo[i] (both outside its sweep).")]
        public PharmacyDoorV01[] Doors = new PharmacyDoorV01[0];
        public int[] DoorFrom = new int[0];
        public int[] DoorTo = new int[0];
        [Tooltip("Seconds at the cash desk between trips (random in range).")]
        public Vector2 DeskSeconds = new Vector2(70f, 140f);
        [Tooltip("Seconds out in the service yard (random in range).")]
        public Vector2 YardSeconds = new Vector2(25f, 45f);
        public float WalkSpeed = 1.15f;
        public float RespawnSeconds = 240f;
        public float RespawnUnobserved = 35f;
        public string NpcName = "Pharmacy_Staff_01";

        private enum Phase : byte { None, Desk, ToYard, Yard, ToDesk, Gone, Home }

        private GreyboxNpc npc;
        private CharacterController controller;
        private Phase phase = Phase.None;
        private int node, heldDoor = -1;
        private float until, vy, nextTry, lostAt = -1f, stuckCheck;
        private Vector3 stuckFrom;
        private bool warned, fled, closing;
        private GreyboxNpc lost;
        private string templateName = "";
        private readonly List<Vector3> bodies = new List<Vector3>();

        public GreyboxNpc Npc => npc;
        public string State => phase + (phase == Phase.ToYard || phase == Phase.ToDesk ? " node " + node : "") + (closing ? " (closing)" : "");
        /// <summary>He walks his route now (the network pushes his pose faster).</summary>
        public bool Walking => phase == Phase.ToYard || phase == Phase.ToDesk;
        /// <summary>Horizontal walking speed (m/s) for the animation of the clients' copy.</summary>
        public float Speed => controller != null && controller.enabled ? Vector3.ProjectOnPlane(controller.velocity, Vector3.up).magnitude : 0f;
        /// <summary>The crowd template he was cloned from (clients clone the same one for their copy).</summary>
        public string TemplateName => templateName;
        /// <summary>At the cash desk now (standing there, not walking or away).</summary>
        public bool AtDesk => npc != null && phase == Phase.Desk;

        private void Update()
        {
            if (!FishNet.InstanceFinder.IsServerStarted || Route == null || Route.Length < 2) return;
            bool open = PharmacyNetV01.OpenNow;
            if (npc == null || !npc)
            {
                if (phase != Phase.None && phase != Phase.Gone && phase != Phase.Home) { phase = Phase.Gone; lostAt = Time.time; ReleaseDoor(); }
                closing = false;
                if (open) TrySpawn();
                return;
            }
            if (phase == Phase.Gone) return;
            if (npc.State != NpcState.Free || npc.InCargo)
            {
                LetGo();
                return;
            }
            if (npc.Fleeing)
            {
                // GreyboxNpc runs him (from the van / the pawn); the routine waits and rejoins its route when he is calm
                if (!fled) { fled = true; ReleaseDoor(); }
                return;
            }
            if (fled) { fled = false; if (!Rejoin()) { LetGo(); return; } }
            if (!open && !closing) GoHome();
            else if (open && closing) { closing = false; if (phase == Phase.ToYard) { phase = Phase.ToDesk; node = Mathf.Max(0, node - 1); StartLeg(); } }
            Tick();
        }

        /// <summary>Closing time: off along the route to the service yard (turning round if he was on his way in).</summary>
        private void GoHome()
        {
            closing = true;
            Debug.Log($"[PHARMACY] closing time: pharmacist {npc.name} leaves through the stockroom and the rear door ({State})", this);
            switch (phase)
            {
                case Phase.Desk: phase = Phase.ToYard; node = 1; StartLeg(); break;
                case Phase.ToDesk: phase = Phase.ToYard; node = Mathf.Min(Route.Length - 1, node + 1); StartLeg(); break;
                case Phase.Yard: until = 0f; break;
            }
        }

        // ---------- spawning ----------

        private void TrySpawn()
        {
            if (Time.time < nextTry) return;
            nextTry = Time.time + 2f;
            var capture = CaptureDirector.Instance;
            if (capture != null && !capture.Loaded) return; // the save restores captives first
            Transform yard = Route[Route.Length - 1];
            bool viaYard = false;
            if (phase == Phase.Home || phase == Phase.None)
            {
                // morning: at the desk when nobody watches it, else in through the yard (never popping up in sight)
                if (PlayerNear(Route[0].position, RespawnUnobserved))
                {
                    if (PlayerNear(yard.position, RespawnUnobserved)) return;
                    viaYard = true;
                }
            }
            else if (phase == Phase.Gone)
            {
                if (Time.time - lostAt < RespawnSeconds) return;
                if (PlayerNear(Route[0].position, RespawnUnobserved) || PlayerNear(Route[Route.Length - 1].position, RespawnUnobserved)) return;
                // the old one still stands free in or near the shop: no second pharmacist
                if (lost != null && lost && lost.State == NpcState.Free && !lost.InCargo &&
                    (lost.transform.position - Route[0].position).sqrMagnitude < 30f * 30f) return;
            }
            GameObject template = PickTemplate();
            if (template == null)
            {
                if (!warned) { warned = true; Debug.LogWarning("[PHARMACY] no adult crowd template: no pharmacist in this scene", this); }
                return;
            }
            Transform at = viaYard ? yard : Route[0];
            Transform parent = template.transform.parent != null ? template.transform.parent.parent : null;
            GameObject go = Instantiate(template, at.position + Vector3.up * 0.05f, at.rotation, parent);
            go.name = NpcName;
            if (go.TryGetComponent(out CrowdWalker walker)) DestroyImmediate(walker);
            go.SetActive(true);
            npc = go.GetComponent<GreyboxNpc>();
            if (npc == null) { Destroy(go); return; }
            controller = go.GetComponent<CharacterController>();
            npc.ExternalLocomotion = true;
            templateName = template.name;
            closing = false;
            if (viaYard) { phase = Phase.ToDesk; node = Route.Length - 2; StartLeg(); }
            else { node = 0; BeginDesk(); }
            Debug.Log($"[PHARMACY] pharmacist {go.name} at the cash desk {at.position} (template {template.name}, visual {NpcSpawnTables.VisualOf(template)})", this);
        }

        private static readonly string[] Prefer = { "PHARM", "NURSE", "DOCTOR", "MEDIC", "CLERK", "OFFICE", "SELLER", "SHOP" };
        private static readonly string[] NotAdult = { "KID", "CHILD", "TEEN", "BOY", "GIRL", "SCHOOL", "BABY", "STUDENT" };
        private static readonly string[] NotStaff = { "POLICE", "COP", "GOPNIK", "BAD", "DRUNK", "HOMELESS", "BUM", "CONSTR", "SWIM", "BEACH" };

        /// <summary>An adult crowd template (GreyboxNpc): a shop / medical type if the crowd has one, else an ordinary adult
        /// (the A/B Buddies first), never a child, police or a district character.</summary>
        public static GameObject PickTemplate()
        {
            var crowd = CrowdDirector.Instance;
            if (crowd == null || crowd.Templates == null) return null;
            GameObject preferred = null, buddy = null, plain = null;
            foreach (GameObject t in crowd.Templates)
            {
                if (t == null || t.GetComponent<GreyboxNpc>() == null) continue;
                string v = (NpcSpawnTables.VisualOf(t) + " " + t.name).ToUpperInvariant();
                if (Has(v, NotAdult)) continue;
                if (preferred == null && Has(v, Prefer)) preferred = t;
                if (Has(v, NotStaff)) continue;
                if (buddy == null && (v.Contains("SAUSAGEBUDDY_A") || v.Contains("SAUSAGEBUDDY_B"))) buddy = t;
                plain ??= t;
            }
            return preferred ?? buddy ?? plain;
        }

        private static bool Has(string s, string[] keys)
        {
            foreach (string k in keys) if (s.Contains(k)) return true;
            return false;
        }

        private bool PlayerNear(Vector3 p, float radius)
        {
            var capture = CaptureDirector.Instance;
            if (capture != null && capture.Pawn != null && (capture.Pawn.Position - p).sqrMagnitude < radius * radius) return true;
            Camera cam = Camera.main;
            if (cam != null && (cam.transform.position - p).sqrMagnitude < radius * radius) return true;
            var economy = TeamEconomy.Instance;
            if (economy == null || !economy.IsServer) return false;
            economy.ServerPlayerPositions(bodies);
            foreach (Vector3 b in bodies) if ((b - p).sqrMagnitude < radius * radius) return true;
            return false;
        }

        // ---------- the routine ----------

        private void BeginDesk()
        {
            phase = Phase.Desk;
            until = Time.time + Random.Range(DeskSeconds.x, DeskSeconds.y);
        }

        private void Tick()
        {
            switch (phase)
            {
                case Phase.Desk:
                    Stand(Route[0]);
                    if (Time.time >= until) { phase = Phase.ToYard; node = 1; StartLeg(); }
                    break;
                case Phase.Yard:
                    Stand(Route[Route.Length - 1]);
                    if (closing)
                    {
                        // home for the night once nobody is around to see him go
                        if (!PlayerNear(Route[Route.Length - 1].position, RespawnUnobserved))
                        {
                            Debug.Log($"[PHARMACY] pharmacist {npc.name} went home for the night", this);
                            npc.ExternalLocomotion = false;
                            Destroy(npc.gameObject);
                            npc = null; controller = null;
                            phase = Phase.Home;
                            closing = false;
                        }
                        break;
                    }
                    if (Time.time >= until) { phase = Phase.ToDesk; node = Route.Length - 2; StartLeg(); }
                    break;
                case Phase.ToYard:
                case Phase.ToDesk:
                    Walk();
                    break;
            }
        }

        private int Dir => phase == Phase.ToYard ? 1 : -1;
        private int From => node - Dir;

        private void StartLeg()
        {
            stuckFrom = npc.transform.position;
            stuckCheck = Time.time + 6f;
        }

        private void Walk()
        {
            // a door between the node we left and the next one: open it (we stand outside its sweep) and wait
            int door = DoorOn(From, node);
            if (door >= 0 && heldDoor != door)
            {
                ReleaseDoor();
                heldDoor = door;
                Doors[door].Hold(this);
            }
            if (heldDoor >= 0 && Doors[heldDoor] != null && !Doors[heldDoor].IsOpen && Near(From, 0.6f))
            {
                Move(Vector3.zero, Route[node].position - npc.transform.position);
                return;
            }
            Vector3 to = Route[node].position - npc.transform.position;
            to.y = 0f;
            if (to.magnitude < 0.3f)
            {
                // reached: past a door (its far node) lets it close
                if (heldDoor >= 0 && IsDoorEnd(heldDoor, node)) ReleaseDoor();
                int next = node + Dir;
                if (next < 0 || next >= Route.Length)
                {
                    if (phase == Phase.ToYard) { phase = Phase.Yard; until = Time.time + Random.Range(YardSeconds.x, YardSeconds.y); }
                    else BeginDesk();
                    Move(Vector3.zero, Vector3.zero);
                    return;
                }
                node = next;
                StartLeg();
                return;
            }
            Move(to.normalized * Mathf.Min(WalkSpeed, to.magnitude * 2.5f + 0.2f), to);
            if (Time.time >= stuckCheck)
            {
                // blocked for long (a player in the doorway, a body on the floor): give way and go back to the last node
                if ((npc.transform.position - stuckFrom).sqrMagnitude < 0.25f)
                    Debug.Log($"[PHARMACY] pharmacist blocked on the way to node {node}; waiting", this);
                stuckFrom = npc.transform.position;
                stuckCheck = Time.time + 6f;
            }
        }

        private bool Near(int i, float r)
        {
            if (i < 0 || i >= Route.Length) return false;
            Vector3 d = Route[i].position - npc.transform.position;
            d.y = 0f;
            return d.magnitude < r;
        }

        private int DoorOn(int a, int b)
        {
            for (int i = 0; i < Doors.Length && i < DoorFrom.Length && i < DoorTo.Length; i++)
            {
                int lo = Mathf.Min(DoorFrom[i], DoorTo[i]), hi = Mathf.Max(DoorFrom[i], DoorTo[i]);
                if (Mathf.Min(a, b) >= lo && Mathf.Max(a, b) <= hi && a != b) return i;
            }
            return -1;
        }

        private bool IsDoorEnd(int door, int at) => Dir > 0 ? at == Mathf.Max(DoorFrom[door], DoorTo[door]) : at == Mathf.Min(DoorFrom[door], DoorTo[door]);

        private void ReleaseDoor()
        {
            if (heldDoor >= 0 && heldDoor < Doors.Length && Doors[heldDoor] != null) Doors[heldDoor].Release(this);
            heldDoor = -1;
        }

        private void Stand(Transform spot)
        {
            Vector3 d = spot.position - npc.transform.position;
            d.y = 0f;
            if (d.magnitude > 0.35f) { Move(d.normalized * Mathf.Min(WalkSpeed, d.magnitude * 2f), d); return; }
            Move(Vector3.zero, spot.forward);
        }

        private void Move(Vector3 velocity, Vector3 face)
        {
            float dt = Time.deltaTime;
            if (controller != null && controller.enabled)
            {
                vy = controller.isGrounded ? -1f : vy - 20f * dt;
                controller.Move((velocity + Vector3.up * vy) * dt);
            }
            face.y = 0f;
            if (face.sqrMagnitude > 0.0001f)
                npc.transform.rotation = Quaternion.RotateTowards(npc.transform.rotation, Quaternion.LookRotation(face), 300f * dt);
            if (npc.Anim != null)
                npc.Anim.SetMove(controller != null && controller.enabled ? Vector3.ProjectOnPlane(controller.velocity, Vector3.up).magnitude : 0f);
        }

        /// <summary>After a flight: back to the nearest route node he can walk to in a straight line (no wall between), then
        /// on to the cash desk. False when none is in reach (he then stays an ordinary NPC where he is).</summary>
        private bool Rejoin()
        {
            Vector3 eye = npc.transform.position + Vector3.up;
            int best = -1;
            float bd = 8f * 8f;
            for (int i = 0; i < Route.Length; i++)
            {
                Vector3 p = Route[i].position + Vector3.up;
                float d = (p - eye).sqrMagnitude;
                if (d >= bd) continue;
                bool blocked = false;
                foreach (RaycastHit h in Physics.RaycastAll(eye, p - eye, Mathf.Sqrt(d), ~0, QueryTriggerInteraction.Ignore))
                    if (!h.collider.transform.IsChildOf(npc.transform)) { blocked = true; break; }
                if (blocked) continue;
                bd = d;
                best = i;
            }
            if (best < 0) return false;
            phase = Phase.ToDesk;
            node = best;
            StartLeg();
            return true;
        }

        /// <summary>Stunned, captured or in the van: the GreyboxNpc owns him from now on (like a released crowd walker).</summary>
        private void LetGo()
        {
            ReleaseDoor();
            if (npc != null)
            {
                npc.ExternalLocomotion = false;
                Debug.Log($"[PHARMACY] pharmacist {npc.name} left the routine ({npc.State}{(npc.Fleeing ? ", fleeing" : "")}{(npc.InCargo ? ", in the van" : "")})", this);
            }
            lost = npc;
            npc = null;
            controller = null;
            phase = Phase.Gone;
            lostAt = Time.time;
        }

        private void OnDisable() => ReleaseDoor();
    }
}
