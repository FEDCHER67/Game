using System;
using System.Collections.Generic;
using FishNet;
using FishNet.Broadcast;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Transporting;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using UnityEngine;

namespace OnlyVolunteers.Economy.Pharmacy
{
    public enum PharmacyRequestKind : byte
    {
        /// <summary>A client's pharmacy came up: send it the current state (late join).</summary>
        Hello = 0,
        /// <summary>Arg = catalogue key, Expected = the price on the buyer's card, Key = the request id (idempotent).</summary>
        Buy = 1,
        /// <summary>Arg = door index (PharmacyNetV01.Doors), Expected = 1 open / 0 close.</summary>
        Door = 2,
    }

    /// <summary>Client -> server: an intent (never an amount or a result).</summary>
    public struct PharmacyRequestBroadcast : IBroadcast
    {
        public byte Kind;
        public string Key;
        public string Arg;
        public int Expected;
    }

    /// <summary>Server -> the requester: the outcome of one request.</summary>
    public struct PharmacyResultBroadcast : IBroadcast
    {
        public string Key;
        public bool Ok;
        public string Message;
    }

    /// <summary>Server -> clients: the pharmacy's shared state (opening hours, door leaves, the pharmacist's pose).</summary>
    public struct PharmacyStateBroadcast : IBroadcast
    {
        public uint Seq;
        public bool Open;
        public float[] DoorYaw;
        public bool[] DoorTarget;
        public bool StaffVisible;
        public Vector3 StaffPosition;
        public float StaffYaw;
        public float StaffSpeed;
        public string StaffTemplate;
    }

    /// <summary>
    /// The city pharmacy on the network (Pharmacy_W86, FishNet broadcasts like TeamEconomy: no NetworkObject, no spawnable
    /// list, works in the solo host the same way). The server owns everything: the opening hours (PharmacyHours on the
    /// server's game clock), the door leaves (PharmacyDoorV01 swings and its never-push checks run only there), the
    /// purchases (PharmacyCounterV01.ServerBuy: shared fund, idempotent request id, goods to the REQUESTER) and the
    /// pharmacist (PharmacyStaffV01 drives him). Any machine sends intents (E on a door, Buy at the counter) and gets the
    /// answer back; clients receive the state at 10 Hz while something moves, else 1 Hz, and on joining (Hello), and show
    /// it: doors at the server's yaw, a presentation-only copy of the pharmacist. Lives on W86_Pharmacy_Anchors (integrator
    /// step 8b); <see cref="InsideCentre"/> / <see cref="InsideSize"/> = the unit's floor box in that root's frame.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class PharmacyNetV01 : MonoBehaviour
    {
        public static PharmacyNetV01 Instance { get; private set; }

        [Tooltip("The shop's inside (sales floor + stockroom) in this transform's frame: a box from the floor up.")]
        public Vector3 InsideCentre = new Vector3(0f, 1.3f, 6.4f);
        public Vector3 InsideSize = new Vector3(10.3f, 2.8f, 12.8f);
        [Tooltip("The building's doors (index = Door request Arg); found under the pharmacy building when empty.")]
        public PharmacyDoorV01[] Doors = new PharmacyDoorV01[0];
        public PharmacyStaffV01 Staff;

        private NetworkManager manager;
        private bool bound;
        private uint seq;
        private bool open = true;
        private float nextPush, nextBeat;
        private string lastSignature = "";
        private readonly Dictionary<string, Action<bool, string>> pending = new Dictionary<string, Action<bool, string>>();
        // client view
        private bool viewOpen = true;
        private PharmacyStateBroadcast? view;
        private GameObject staffProxy;
        private string proxyTemplate = "";
        private NpcAnimDriver proxyAnim;
        private Vector3 proxyPos;
        private float proxyYaw, proxySpeed;
        private TextMesh closedSign;

        /// <summary>No network running, or this machine is the server: it owns the pharmacy's state.</summary>
        public static bool Authority
        {
            get
            {
                NetworkManager nm = InstanceFinder.NetworkManager;
                return nm == null || nm.IsServerStarted || !nm.IsClientStarted;
            }
        }

        /// <summary>Open now (the server's clock; on a client the last state received).</summary>
        public bool ShopOpen => Authority ? open : viewOpen;
        public static bool OpenNow => Instance == null || Instance.ShopOpen;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Instance = null;

        /// <summary>The one pharmacy service of the scene (an old scene without the integrator's component gets one at the
        /// cash desk's root at runtime).</summary>
        public static PharmacyNetV01 Ensure(Component near)
        {
            if (Instance != null) return Instance;
            var found = FindAnyObjectByType<PharmacyNetV01>();
            if (found != null) return found;
            if (near == null) return null;
            Transform root = near.transform.root;
            return root.gameObject.AddComponent<PharmacyNetV01>();
        }

        private void OnEnable()
        {
            Instance = this;
            if (Doors == null || Doors.Length == 0) Doors = FindDoors();
            if (Staff == null) Staff = GetComponentInChildren<PharmacyStaffV01>(true);
        }

        private void OnDisable()
        {
            Unbind();
            if (Instance == this) Instance = null;
            if (staffProxy != null) Destroy(staffProxy);
        }

        private static PharmacyDoorV01[] FindDoors()
        {
            var list = new List<PharmacyDoorV01>(FindObjectsByType<PharmacyDoorV01>(FindObjectsInactive.Include));
            // a stable order on every machine: street, staff, rear (by name), then the rest
            list.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
            return list.ToArray();
        }

        public int IndexOf(PharmacyDoorV01 door) => Array.IndexOf(Doors, door);

        /// <summary>A world position inside the shop (sales floor or stockroom).</summary>
        public bool Inside(Vector3 world)
        {
            Vector3 p = transform.InverseTransformPoint(world) - InsideCentre;
            Vector3 h = InsideSize * 0.5f;
            return Mathf.Abs(p.x) <= h.x && Mathf.Abs(p.z) <= h.z && p.y >= -h.y - 0.5f && p.y <= h.y;
        }

        // ================================================================== binding

        private void Bind()
        {
            NetworkManager nm = InstanceFinder.NetworkManager;
            if (nm == null || bound && nm == manager) return;
            Unbind();
            manager = nm;
            manager.ServerManager.RegisterBroadcast<PharmacyRequestBroadcast>(OnServerRequest);
            manager.ClientManager.RegisterBroadcast<PharmacyResultBroadcast>(OnClientResult);
            manager.ClientManager.RegisterBroadcast<PharmacyStateBroadcast>(OnClientState);
            manager.ClientManager.OnClientConnectionState += OnClientConnection;
            bound = true;
            if (manager.IsClientStarted && !manager.IsServerStarted) SendHello();
        }

        private void Unbind()
        {
            if (!bound || manager == null) { bound = false; return; }
            manager.ServerManager.UnregisterBroadcast<PharmacyRequestBroadcast>(OnServerRequest);
            manager.ClientManager.UnregisterBroadcast<PharmacyResultBroadcast>(OnClientResult);
            manager.ClientManager.UnregisterBroadcast<PharmacyStateBroadcast>(OnClientState);
            manager.ClientManager.OnClientConnectionState -= OnClientConnection;
            bound = false;
        }

        private void OnClientConnection(ClientConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Started && manager != null && !manager.IsServerStarted) SendHello();
        }

        private void SendHello()
        {
            if (manager != null && manager.IsClientStarted)
                manager.ClientManager.Broadcast(new PharmacyRequestBroadcast { Kind = (byte)PharmacyRequestKind.Hello, Key = "", Arg = "" });
        }

        // ================================================================== requests (any machine)

        /// <summary>Ask the server; done(ok, message) runs here when the answer arrives (at once on the host).</summary>
        public string Request(PharmacyRequestKind kind, string arg, int expected, Action<bool, string> done, string key = null)
        {
            Bind();
            key = string.IsNullOrEmpty(key) ? Guid.NewGuid().ToString("N") : key;
            var m = new PharmacyRequestBroadcast { Kind = (byte)kind, Key = key, Arg = arg ?? "", Expected = expected };
            if (Authority)
            {
                (bool ok, string text) = Process(m, manager != null ? manager.ClientManager.Connection : null);
                done?.Invoke(ok, text);
            }
            else if (manager != null && manager.IsClientStarted)
            {
                if (done != null) pending[key] = done;
                manager.ClientManager.Broadcast(m);
            }
            else done?.Invoke(false, "Нет связи с хостом");
            return key;
        }

        private void OnServerRequest(NetworkConnection connection, PharmacyRequestBroadcast m, Channel channel)
        {
            if (connection == null || !connection.IsActive) return;
            if (m.Kind == (byte)PharmacyRequestKind.Hello) { SendState(connection); return; }
            (bool ok, string text) = Process(m, connection);
            manager.ServerManager.Broadcast(connection, new PharmacyResultBroadcast { Key = m.Key, Ok = ok, Message = text });
        }

        private void OnClientResult(PharmacyResultBroadcast r, Channel channel)
        {
            if (Authority) return;
            if (r.Key != null && pending.TryGetValue(r.Key, out Action<bool, string> done))
            {
                pending.Remove(r.Key);
                try { done(r.Ok, r.Message); } catch (Exception e) { Debug.LogException(e, this); }
            }
        }

        // ================================================================== server

        private (bool, string) Process(PharmacyRequestBroadcast m, NetworkConnection from)
        {
            if (string.IsNullOrEmpty(m.Key) || m.Key.Length > 64 || (m.Arg != null && m.Arg.Length > 64)) return (false, "Неверный запрос");
            switch ((PharmacyRequestKind)m.Kind)
            {
                case PharmacyRequestKind.Buy:
                    return PharmacyCounterV01.ServerBuy(m.Arg, m.Expected, m.Key, from, HourNow());
                case PharmacyRequestKind.Door:
                {
                    if (!int.TryParse(m.Arg, out int i) || i < 0 || i >= Doors.Length || Doors[i] == null) return (false, "Неверный запрос");
                    Vector3? actor = TeamEconomy.ServerActorPosition(from);
                    if (!actor.HasValue) return (false, "Нет игрока на сервере");
                    return Doors[i].ServerRequest(m.Expected != 0, actor.Value, open, Inside(actor.Value));
                }
                default:
                    return (false, "Неверный запрос");
            }
        }

        /// <summary>The server's hour of day (the economy's saved calendar observes the sky clock; -1 = unknown = open).</summary>
        public static double HourNow()
        {
            var state = TeamEconomy.Instance != null ? TeamEconomy.Instance.ServerState : null;
            if (state != null && state.TimeOfDay >= 0) return state.TimeOfDay;
            var clock = FindAnyObjectByType<OnlyVolunteers.Sky22V04.SkyClock22>();
            return clock != null ? clock.Hour : -1.0;
        }

        private void Update()
        {
            Bind();
            if (Authority)
            {
                bool now = PharmacyHours.IsOpen(HourNow());
                if (now != open)
                {
                    open = now;
                    Debug.Log($"[PHARMACY] {(open ? "opened (08:00)" : "closed for the night (20:00): " + PharmacyHours.ClosedText)}", this);
                }
                ServerPush();
            }
            else ClientTick();
            UpdateClosedSign();
        }

        private bool Moving()
        {
            foreach (PharmacyDoorV01 d in Doors) if (d != null && d.Moving) return true;
            return Staff != null && Staff.Npc != null && Staff.Walking;
        }

        private void ServerPush()
        {
            if (manager == null || !manager.IsServerStarted) return;
            float now = Time.unscaledTime;
            bool moving = Moving();
            string signature = Signature();
            bool changed = signature != lastSignature;
            if (!(changed && now >= nextPush || moving && now >= nextPush || now >= nextBeat)) return;
            lastSignature = signature;
            nextPush = now + 0.1f;
            nextBeat = now + 1f;
            if (manager.ServerManager.Clients.Count <= 1) return; // the host alone: nobody to tell
            PharmacyStateBroadcast s = Snapshot();
            foreach (NetworkConnection c in manager.ServerManager.Clients.Values)
                if (c != null && c.IsActive && !c.IsLocalClient) manager.ServerManager.Broadcast(c, s);
        }

        private string Signature()
        {
            var sb = new System.Text.StringBuilder(open ? "o" : "c");
            foreach (PharmacyDoorV01 d in Doors) sb.Append(d != null && d.TargetOpen ? '1' : '0');
            sb.Append(Staff != null && Staff.Npc != null ? 's' : '-');
            return sb.ToString();
        }

        private PharmacyStateBroadcast Snapshot()
        {
            var s = new PharmacyStateBroadcast { Seq = ++seq, Open = open, DoorYaw = new float[Doors.Length], DoorTarget = new bool[Doors.Length], StaffTemplate = "" };
            for (int i = 0; i < Doors.Length; i++)
                if (Doors[i] != null) { s.DoorYaw[i] = Doors[i].Yaw; s.DoorTarget[i] = Doors[i].TargetOpen; }
            GreyboxNpc npc = Staff != null ? Staff.Npc : null;
            if (npc != null)
            {
                s.StaffVisible = true;
                s.StaffPosition = npc.transform.position;
                s.StaffYaw = npc.transform.eulerAngles.y;
                s.StaffSpeed = Staff.Speed;
                s.StaffTemplate = Staff.TemplateName ?? "";
            }
            return s;
        }

        private void SendState(NetworkConnection c)
        {
            if (manager == null || c == null || !c.IsActive) return;
            manager.ServerManager.Broadcast(c, Snapshot());
        }

        // ================================================================== client view

        private void OnClientState(PharmacyStateBroadcast s, Channel channel)
        {
            if (Authority) return;
            if (view.HasValue && s.Seq != 0 && s.Seq < view.Value.Seq && view.Value.Seq - s.Seq < 1000000) return; // stale
            view = s;
            viewOpen = s.Open;
            if (s.DoorYaw != null)
                for (int i = 0; i < Doors.Length && i < s.DoorYaw.Length; i++)
                    if (Doors[i] != null) Doors[i].ApplyServer(s.DoorYaw[i], s.DoorTarget != null && i < s.DoorTarget.Length && s.DoorTarget[i]);
        }

        private void ClientTick()
        {
            if (!view.HasValue) return;
            PharmacyStateBroadcast s = view.Value;
            if (!s.StaffVisible)
            {
                if (staffProxy != null) { Destroy(staffProxy); staffProxy = null; }
                return;
            }
            if (staffProxy == null || proxyTemplate != s.StaffTemplate)
            {
                if (staffProxy != null) Destroy(staffProxy);
                staffProxy = MakeProxy(s.StaffTemplate, s.StaffPosition, s.StaffYaw);
                proxyTemplate = s.StaffTemplate;
                proxyPos = s.StaffPosition; proxyYaw = s.StaffYaw;
                if (staffProxy == null) return;
            }
            float k = 1f - Mathf.Exp(-12f * Time.deltaTime);
            proxyPos = Vector3.Lerp(staffProxy.transform.position, s.StaffPosition, k);
            proxyYaw = Mathf.LerpAngle(staffProxy.transform.eulerAngles.y, s.StaffYaw, k);
            proxySpeed = Mathf.Lerp(proxySpeed, s.StaffSpeed, k);
            staffProxy.transform.SetPositionAndRotation(proxyPos, Quaternion.Euler(0f, proxyYaw, 0f));
            if (proxyAnim != null) proxyAnim.SetMove(proxySpeed);
        }

        /// <summary>A presentation-only copy of the server's pharmacist: the same crowd template (every peer loads the same
        /// scene), its NPC brain, controller and colliders off; the server's pose and walk speed drive it.</summary>
        private GameObject MakeProxy(string template, Vector3 at, float yaw)
        {
            GameObject source = null;
            var crowd = CrowdDirector.Instance;
            if (crowd != null && crowd.Templates != null)
                foreach (GameObject t in crowd.Templates) if (t != null && t.name == template) { source = t; break; }
            source ??= PharmacyStaffV01.PickTemplate();
            if (source == null) return null;
            GameObject go = Instantiate(source, at, Quaternion.Euler(0f, yaw, 0f));
            go.name = "Pharmacy_Staff_01 (view of the server's pharmacist)";
            if (go.TryGetComponent(out CrowdWalker walker)) Destroy(walker);
            if (go.TryGetComponent(out GreyboxNpc npc)) npc.enabled = false;
            if (go.TryGetComponent(out CharacterController cc)) cc.enabled = false;
            foreach (Collider c in go.GetComponentsInChildren<Collider>(true)) c.enabled = false;
            go.SetActive(true);
            proxyAnim = go.GetComponent<NpcAnimDriver>();
            return go;
        }

        // ================================================================== night sign

        /// <summary>A readable sign behind the street door's glass at night: "Closed — opens at 8:00".</summary>
        private void UpdateClosedSign()
        {
            bool show = !ShopOpen;
            if (closedSign == null)
            {
                if (!show) return;
                PharmacyDoorV01 street = null;
                foreach (PharmacyDoorV01 d in Doors) if (d != null && d.name.IndexOf("Street", StringComparison.OrdinalIgnoreCase) >= 0) { street = d; break; }
                if (street == null) return;
                closedSign = EconomyLabel.Create(transform, PharmacyHours.ClosedText, transform.InverseTransformPoint(street.Centre + Vector3.up * 0.75f), 0.045f, new Color(1f, 0.82f, 0.45f));
                closedSign.gameObject.name = "Closed sign (night)";
            }
            if (closedSign.gameObject.activeSelf != show) closedSign.gameObject.SetActive(show);
        }
    }
}
