using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Economy.Pharmacy
{
    /// <summary>
    /// A hinged door of the city pharmacy (Pharmacy_W86: street door, staff door, rear door). Lives on the hinge transform
    /// of the FBX (pivot = hinge at floor level, leaf + its UCX collider as children), swings by its local yaw between 0
    /// (closed) and <see cref="OpenYaw"/>. Players: E within reach toggles a Public door; a StaffOnly door stays locked for
    /// them ("STAFF ONLY" printed on its face, a short prompt). Staff (PharmacyStaffV01) open any door through
    /// <see cref="Hold"/> / <see cref="Release"/>. Never pushes anybody: the leaf's colliders are off while it moves, a door
    /// does not start swinging while a player or an NPC stands in its sweep, and its collider comes back only once the leaf
    /// is clear. Open Public doors close on their own after a while when nobody is near.
    /// Network (PharmacyNetV01): the server owns the leaf (target, swing, the never-push checks over every player body and
    /// NPC); E on any machine is an intent the server answers through <see cref="ServerRequest"/> (opening hours: at night
    /// the public doors stay shut for anybody outside - "Closed - opens at 8:00" - while somebody inside can always open
    /// them to leave; open public doors swing shut by themselves after closing time). Clients show the server's yaw.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PharmacyDoorV01 : MonoBehaviour
    {
        public enum Access : byte { Public = 0, StaffOnly = 1 }

        public Access Mode = Access.Public;
        [Tooltip("Signed local yaw of the open leaf (degrees); set by the integrator so the leaf swings to the intended side.")]
        public float OpenYaw = 90f;
        public float Speed = 140f;
        public float Reach = 2.0f;
        [Tooltip("Public doors: close after this many seconds open with nobody near (0 = never).")]
        public float AutoClose = 12f;
        public string Title = "дверь";

        public bool IsOpen => Mathf.Abs(Mathf.DeltaAngle(yaw, OpenYaw)) < 6f;
        public bool IsClosed => Mathf.Abs(yaw) < 0.5f;
        public bool Moving => Mathf.Abs(Mathf.DeltaAngle(yaw, target)) > 0.01f;
        /// <summary>The leaf's yaw now (server: simulated; client: as received).</summary>
        public float Yaw => yaw;
        /// <summary>The server wants this door open.</summary>
        public bool TargetOpen => Mathf.Abs(target) > 0.01f;

        private static readonly List<PharmacyDoorV01> all = new List<PharmacyDoorV01>();
        private readonly HashSet<Object> holders = new HashSet<Object>();
        private Collider[] colliders;
        private float yaw, target;
        private float leafLength = 1f, leafSign = 1f;
        private float lastNear;
        private string prompt = "";
        private GUIStyle style;
        private bool busy;
        private float serverYaw;
        private bool hasServerYaw;
        private readonly List<Vector3> players = new List<Vector3>();

        private void Awake()
        {
            colliders = GetComponentsInChildren<Collider>(true);
            // the leaf's free end, measured closed in the hinge frame (renderer bounds of the children)
            var b = new Bounds(Vector3.zero, Vector3.zero);
            bool any = false;
            foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
            {
                foreach (Vector3 c in Corners(r.bounds))
                {
                    Vector3 p = transform.InverseTransformPoint(c);
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            if (any)
            {
                leafSign = Mathf.Abs(b.max.x) >= Mathf.Abs(b.min.x) ? 1f : -1f;
                leafLength = Mathf.Max(Mathf.Abs(b.max.x), Mathf.Abs(b.min.x));
            }
            baseRotation = transform.localRotation;
            yaw = target = 0f;
        }

        private void OnEnable() => all.Add(this);
        private void OnDisable() => all.Remove(this);

        private static IEnumerable<Vector3> Corners(Bounds b)
        {
            for (int i = 0; i < 8; i++)
                yield return new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z);
        }

        /// <summary>The door nearest to p (any access) within maxDistance, or null.</summary>
        public static PharmacyDoorV01 Nearest(Vector3 p, float maxDistance)
        {
            PharmacyDoorV01 best = null;
            float bd = maxDistance * maxDistance;
            foreach (PharmacyDoorV01 d in all)
            {
                float dd = (d.Centre - p).sqrMagnitude;
                if (dd < bd) { bd = dd; best = d; }
            }
            return best;
        }

        /// <summary>Middle of the closed doorway, 1 m above the floor (world).</summary>
        public Vector3 Centre => transform.position + ClosedFrame * Vector3.right * (leafSign * leafLength * 0.5f) + Vector3.up;

        private Quaternion baseRotation = Quaternion.identity;
        private Quaternion ClosedFrame => (transform.parent != null ? transform.parent.rotation : Quaternion.identity) * baseRotation;

        // ---------- staff (server-side NPC walker) ----------

        /// <summary>Staff want to pass: the door opens (when its sweep is clear) and stays open while held.</summary>
        public void Hold(Object who)
        {
            holders.Add(who);
            target = OpenYaw;
        }

        public void Release(Object who)
        {
            holders.Remove(who);
        }

        // ---------- per frame ----------

        private void Update()
        {
            LocalInput();
            if (!PharmacyNetV01.Authority)
            {
                ClientFollow();
                return;
            }
            bool shopOpen = PharmacyNetV01.OpenNow;
            if (holders.Count > 0) target = OpenYaw;
            else if (Mode == Access.StaffOnly && !IsClosed && Mathf.Abs(target) > 0.01f) target = 0f;
            else if (PharmacyDoorRules.CloseForNight(Mode == Access.StaffOnly, shopOpen, TargetOpen) && !SomeoneNear(1.6f)) target = 0f;
            else if (Mode == Access.Public && AutoClose > 0f && Mathf.Abs(target) > 0.01f && IsOpen && Time.time - lastNear > AutoClose && !SomeoneNear(3f)) target = 0f;
            Swing();
        }

        /// <summary>The local player's E (every machine): an intent to the server, the answer as a toast.</summary>
        private void LocalInput()
        {
            Vector3? player = PlayerFeet();
            prompt = "";
            if (!player.HasValue || OnlyVolunteers.UI.OvMenuGate.Blocking) return;
            Vector3 c = Centre;
            bool near = (Flat(c) - Flat(player.Value)).sqrMagnitude < Reach * Reach && Mathf.Abs(c.y - 1f - player.Value.y) < 1.6f;
            if (near) lastNear = Time.time;
            if (!near || Nearest(player.Value + Vector3.up, Reach + 0.5f) != this) return;
            var key = OpsInput.Keyboard;
            bool e = key != null && key.eKey.wasPressedThisFrame && GreyboxInput.EFree && !busy;
            PharmacyNetV01 net = PharmacyNetV01.Instance;
            bool wantOpen = !TargetOpen;
            bool inside = net != null && net.Inside(player.Value);
            PharmacyDoorAnswer local = PharmacyDoorRules.Request(Mode == Access.StaffOnly, PharmacyNetV01.OpenNow, inside, wantOpen);
            if (local == PharmacyDoorAnswer.StaffOnly) prompt = "STAFF ONLY — служебная дверь, посторонним вход закрыт";
            else if (local == PharmacyDoorAnswer.ClosedForNight) prompt = PharmacyHours.ClosedText + "  ·  " + PharmacyHours.SignText;
            else prompt = "<b>E</b> — " + (wantOpen ? "открыть " : "закрыть ") + Title + (!PharmacyNetV01.OpenNow && wantOpen ? " (аптека закрыта — выйти можно)" : "");
            if (!e) return;
            GreyboxInput.UseE();
            if (net == null)
            {
                // no pharmacy service in this scene: the old local door
                if (local == PharmacyDoorAnswer.Allowed) target = wantOpen ? OpenYaw : 0f;
                else CaptureDirector.Instance?.Toast(PharmacyDoorRules.Explain(local), CaptureHud.Warn, 2.5f);
                return;
            }
            busy = true;
            net.Request(PharmacyRequestKind.Door, net.IndexOf(this).ToString(System.Globalization.CultureInfo.InvariantCulture), wantOpen ? 1 : 0, (ok, text) =>
            {
                busy = false;
                if (!ok && !string.IsNullOrEmpty(text)) CaptureDirector.Instance?.Toast(text, CaptureHud.Warn, 2.5f);
            });
        }

        /// <summary>Server: a player's E on this door (actor = the server's own measurement of that player).</summary>
        public (bool ok, string text) ServerRequest(bool wantOpen, Vector3 actor, bool shopOpen, bool actorInside)
        {
            Vector3 c = Centre;
            if ((Flat(c) - Flat(actor)).sqrMagnitude > (Reach + 1f) * (Reach + 1f) || Mathf.Abs(c.y - 1f - actor.y) > 2.2f) return (false, "Подойди к двери");
            PharmacyDoorAnswer a = PharmacyDoorRules.Request(Mode == Access.StaffOnly, shopOpen, actorInside, wantOpen);
            if (a != PharmacyDoorAnswer.Allowed) return (false, PharmacyDoorRules.Explain(a));
            if (!wantOpen && holders.Count > 0) return (false, "В дверях человек");
            target = wantOpen ? OpenYaw : 0f;
            lastNear = Time.time;
            return (true, "");
        }

        /// <summary>Client: the server's leaf as received.</summary>
        public void ApplyServer(float serverYawNow, bool serverTargetOpen)
        {
            serverYaw = serverYawNow;
            hasServerYaw = true;
            target = serverTargetOpen ? OpenYaw : 0f;
        }

        private void ClientFollow()
        {
            if (!hasServerYaw) return;
            float before = yaw;
            yaw = Mathf.MoveTowardsAngle(yaw, serverYaw, Speed * 1.5f * Time.deltaTime);
            if (Mathf.Abs(Mathf.DeltaAngle(before, yaw)) > 0.001f) transform.localRotation = baseRotation * Quaternion.Euler(0f, yaw, 0f);
            // the leaf's collider follows the server's rule: solid when closed, off while it swings, back once the leaf is clear
            bool swinging = Mathf.Abs(Mathf.DeltaAngle(yaw, serverYaw)) > 0.5f || Mathf.Abs(Mathf.DeltaAngle(yaw, target)) > 0.5f;
            SetColliders(IsClosed || !swinging && !LeafOccupied());
        }

        private void Swing()
        {
            bool move = Mathf.Abs(Mathf.DeltaAngle(yaw, target)) > 0.01f;
            if (move && IsClosed || move && IsOpen)
            {
                // starting a swing: wait while somebody stands in the sweep (no door ever shoves a body)
                if (SweepOccupied()) { SetColliders(IsClosed || !LeafOccupied()); return; }
            }
            if (move)
            {
                SetColliders(false);
                yaw = Mathf.MoveTowards(yaw, target, Speed * Time.deltaTime);
                transform.localRotation = baseRotation * Quaternion.Euler(0f, yaw, 0f);
                return;
            }
            // at rest: a closed door is always solid (it only closed with its sweep clear); an open leaf gets its collider back
            // once no body overlaps it
            SetColliders(IsClosed || !LeafOccupied());
        }

        private void SetColliders(bool on)
        {
            if (colliders == null) return;
            foreach (Collider c in colliders) if (c != null && c.enabled != on) c.enabled = on;
        }

        // ---------- bodies: the player and the NPCs ----------

        private static Vector3? PlayerFeet()
        {
            var capture = CaptureDirector.Instance;
            if (capture != null && capture.Pawn != null && capture.Pawn.Controlled) return capture.Pawn.Position;
            return null;
        }

        private static Vector2 Flat(Vector3 v) => new Vector2(v.x, v.z);

        private bool SomeoneNear(float r)
        {
            Vector3 c = Centre;
            foreach (Vector3 p in PlayerBodies())
                if ((Flat(p) - Flat(c)).sqrMagnitude < r * r) return true;
            foreach (GreyboxNpc n in GreyboxNpc.All)
                if (n != null && (Flat(n.transform.position) - Flat(c)).sqrMagnitude < r * r) return true;
            return false;
        }

        /// <summary>Every player body: on the server all of them (the host's pawn and each client's player object), on a
        /// client the local one.</summary>
        private List<Vector3> PlayerBodies()
        {
            players.Clear();
            var economy = TeamEconomy.Instance;
            if (economy != null && economy.IsServer) economy.ServerPlayerPositions(players);
            else { Vector3? p = PlayerFeet(); if (p.HasValue) players.Add(p.Value); }
            return players;
        }

        private IEnumerable<Vector3> Bodies()
        {
            foreach (Vector3 p in PlayerBodies().ToArray()) yield return p;
            Vector3 h = transform.position;
            foreach (GreyboxNpc n in GreyboxNpc.All)
                if (n != null && n.isActiveAndEnabled && (Flat(n.transform.position) - Flat(h)).sqrMagnitude < 9f) yield return n.transform.position;
        }

        /// <summary>A body inside the arc the free end sweeps between closed and open (+ body radius).</summary>
        private bool SweepOccupied() => Sweep(0.42f, 12f);

        private bool Sweep(float bodyRadius, float marginDeg)
        {
            Quaternion frame = ClosedFrame;
            Vector3 h = transform.position;
            float a0 = Mathf.Min(0f, OpenYaw) - marginDeg, a1 = Mathf.Max(0f, OpenYaw) + marginDeg;
            foreach (Vector3 b in Bodies())
            {
                if (b.y > h.y + 2.4f || b.y < h.y - 1.2f) continue;
                Vector3 local = Quaternion.Inverse(frame) * (b - h);
                local.y = 0f;
                float d = local.magnitude;
                if (d > leafLength + bodyRadius) continue;
                if (d < bodyRadius + 0.1f) return true;
                // yaw that brings the closed leaf direction (leafSign * x) onto this body (Unity: +yaw turns +x towards -z)
                float ang = Mathf.Atan2(-local.z, local.x * leafSign) * Mathf.Rad2Deg * leafSign;
                float pad = Mathf.Asin(Mathf.Clamp01(bodyRadius / Mathf.Max(d, 0.01f))) * Mathf.Rad2Deg;
                if (ang >= a0 - pad && ang <= a1 + pad) return true;
            }
            return false;
        }

        /// <summary>A body overlapping the leaf where it stands now.</summary>
        private bool LeafOccupied()
        {
            Quaternion rot = transform.rotation;
            Vector3 h = transform.position;
            foreach (Vector3 b in Bodies())
            {
                if (b.y > h.y + 2.4f || b.y < h.y - 1.2f) continue;
                Vector3 local = Quaternion.Inverse(rot) * (b - h);
                float along = local.x * leafSign;
                if (along > -0.4f && along < leafLength + 0.4f && Mathf.Abs(local.z) < 0.45f) return true;
            }
            return false;
        }

        private void OnGUI()
        {
            if (prompt.Length == 0) return;
            style ??= new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter, fontSize = 19, richText = true, wordWrap = true };
            var r = new Rect(Screen.width * 0.1f, Screen.height * 0.6f, Screen.width * 0.8f, 40f);
            style.normal.textColor = new Color(0f, 0f, 0f, 0.85f);
            GUI.Label(new Rect(r.x + 2f, r.y + 2f, r.width, r.height), System.Text.RegularExpressions.Regex.Replace(prompt, "<.*?>", ""), style);
            style.normal.textColor = Mode == Access.StaffOnly ? new Color(1f, 0.55f, 0.45f) : new Color(1f, 0.93f, 0.75f);
            GUI.Label(r, prompt, style);
        }
    }
}
