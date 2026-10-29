using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using FishNet.Broadcast;
using FishNet.Connection;
using FishNet.Managing;
using FishNet.Managing.Server;
using FishNet.Transporting;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Session;
using UnityEngine;

namespace OnlyVolunteers.UI.MainMenu
{
    /// <summary>Client → host: who joins the lobby (stable id, display name, his OWN look as the appearance wire text).</summary>
    public struct MenuLobbyHelloBroadcast : IBroadcast { public string PlayerId; public string Name; public string Look; }
    /// <summary>Client → host: ready / not ready.</summary>
    public struct MenuLobbyReadyBroadcast : IBroadcast { public bool Ready; }
    /// <summary>Host → clients: the lobby as it is (world name, mode, members "id|name|host|ready|look" joined by '\n').</summary>
    public struct MenuLobbyStateBroadcast : IBroadcast { public string World; public byte Mode; public string Members; }
    /// <summary>Host → one/all clients: 1 refused (reason), 2 the host started the world, 3 the host closed the lobby.</summary>
    public struct MenuLobbyNoticeBroadcast : IBroadcast { public byte Kind; public string Text; }

    /// <summary>
    /// The start menu's lobby (29.10) on the menu scene's own FishNet NetworkManager (Tugboat, the existing transport: direct
    /// IP:port, LAN or a forwarded port; no Steam/relay service exists in the project). The host runs a server on every
    /// interface; each client connects, says Hello (stable id, name, own look) and toggles Ready; the host sees the roster
    /// (LobbyRoster: up to 4, a reconnect with the same id is the same member) and starts when every guest is ready.
    /// Real errors come from the transport (no answer / refused / kicked) plus the host's stated reason (full, solo).
    /// Starting: the host tells everyone, stops this server and loads the world; remote players do NOT follow into the map
    /// yet (players of remote clients on the map = network milestone M1, NETWORK_MAP_PLAN_v01), and their menu says so.
    /// This NetworkManager is not DontDestroyOnLoad and is shut down before the map loads (the map has its own).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class W86MenuLobbyV01 : MonoBehaviour
    {
        public NetworkManager Manager;
        public float ConnectTimeoutSeconds = 8f;

        public enum Role { None, Host, Client }
        public Role Current { get; private set; }
        public LobbyRoster Roster { get; private set; } = new LobbyRoster();
        /// <summary>The members' looks by id (host side and as received by clients), for the lobby list.</summary>
        public readonly Dictionary<string, PlayerAppearance> Looks = new Dictionary<string, PlayerAppearance>();
        public string WorldName { get; private set; } = "";
        public ushort Port { get; private set; } = WorldLaunchV01.DefaultPort;
        public string Address { get; private set; } = "";
        public event Action<MenuInputV2> Report;
        public event Action Changed;

        readonly Dictionary<int, string> idByConnection = new Dictionary<int, string>();
        bool bound, clientStarted, clientInLobby, noticeReceived;
        string noticeText = "";
        float connectDeadline = -1f;

        public static string LocalName
        {
            get
            {
                string n = "";
                try { n = Environment.UserName; } catch (Exception) { }
                n = MainMenuFlowV2.CleanName(n, 0);
                return n.Length > 20 ? n.Substring(0, 20) : n;
            }
        }

        void OnDestroy() => Shutdown(false);

        void Bind()
        {
            if (bound || Manager == null) return;
            bound = true;
            Manager.ServerManager.RegisterBroadcast<MenuLobbyHelloBroadcast>(OnHello);
            Manager.ServerManager.RegisterBroadcast<MenuLobbyReadyBroadcast>(OnReady);
            Manager.ClientManager.RegisterBroadcast<MenuLobbyStateBroadcast>(OnState);
            Manager.ClientManager.RegisterBroadcast<MenuLobbyNoticeBroadcast>(OnNotice);
            Manager.ServerManager.OnRemoteConnectionState += OnRemote;
            Manager.ServerManager.OnServerConnectionState += OnServerState;
            Manager.ClientManager.OnClientConnectionState += OnClientState;
        }

        void Unbind()
        {
            if (!bound || Manager == null) { bound = false; return; }
            bound = false;
            Manager.ServerManager.UnregisterBroadcast<MenuLobbyHelloBroadcast>(OnHello);
            Manager.ServerManager.UnregisterBroadcast<MenuLobbyReadyBroadcast>(OnReady);
            Manager.ClientManager.UnregisterBroadcast<MenuLobbyStateBroadcast>(OnState);
            Manager.ClientManager.UnregisterBroadcast<MenuLobbyNoticeBroadcast>(OnNotice);
            Manager.ServerManager.OnRemoteConnectionState -= OnRemote;
            Manager.ServerManager.OnServerConnectionState -= OnServerState;
            Manager.ClientManager.OnClientConnectionState -= OnClientState;
        }

        // ================================================================== host

        public bool Host(ushort port, string worldName, out string error)
        {
            error = "";
            if (Manager == null) { error = "В сцене меню нет сетевого менеджера."; return false; }
            Shutdown(false);
            Bind();
            Port = port == 0 ? WorldLaunchV01.DefaultPort : port;
            WorldName = worldName ?? "";
            Roster = new LobbyRoster();
            Looks.Clear();
            idByConnection.Clear();
            Roster.Join(PlayerIds.Host, LocalName, true);
            Looks[PlayerIds.Host] = AppearanceProfileV01.Load();
            var t = Manager.TransportManager.Transport;
            t.SetServerBindAddress("0.0.0.0", IPAddressType.IPv4);
            t.SetMaximumClients(WorldModeRules.MaxParticipants - 1);
            if (!Manager.ServerManager.StartConnection(Port))
            {
                error = "Не удалось открыть порт " + Port + " (занят другой программой?).";
                Shutdown(false);
                return false;
            }
            Current = Role.Host;
            Debug.Log($"[OV Lobby] hosting '{WorldName}' on 0.0.0.0:{Port}");
            Changed?.Invoke();
            return true;
        }

        void OnServerState(ServerConnectionStateArgs args)
        {
            if (args.ConnectionState == LocalConnectionState.Stopped && Current == Role.Host)
            {
                Debug.Log("[OV Lobby] server stopped");
                Current = Role.None;
                Changed?.Invoke();
            }
        }

        void OnRemote(NetworkConnection c, RemoteConnectionStateArgs args)
        {
            if (args.ConnectionState != RemoteConnectionState.Stopped || c == null) return;
            if (idByConnection.TryGetValue(c.ClientId, out string id))
            {
                idByConnection.Remove(c.ClientId);
                Roster.Leave(id);
                Looks.Remove(id);
                Debug.Log($"[OV Lobby] {id} left");
                PushState();
            }
        }

        void OnHello(NetworkConnection c, MenuLobbyHelloBroadcast m, Channel channel)
        {
            if (Current != Role.Host || c == null || !c.IsActive) return;
            string id = m.PlayerId ?? "";
            if (!PlayerIds.IsValid(id) || id == PlayerIds.Host) { Refuse(c, "Неверный идентификатор игрока."); return; }
            bool known = false;
            foreach (var member in Roster.Members) if (member.PlayerId == id) known = true;
            if (!known)
            {
                // the immutable-mode join rule (a lobby is only ever hosted for a co-op world) and the 4-player cap
                JoinVerdict v = WorldModeRules.DecideJoin(WorldModeStatus.Multiplayer, false, Roster.Count);
                if (v != JoinVerdict.Accept) { Refuse(c, WorldModeRules.Explain(v)); return; }
            }
            string name = MainMenuFlowV2.CleanName(m.Name, 0);
            if (name.Length > 20) name = name.Substring(0, 20);
            if (!Roster.Join(id, name, false)) { Refuse(c, "Лобби заполнено."); return; }
            idByConnection[c.ClientId] = id;
            AppearanceRules.TryDecode(m.Look, out PlayerAppearance look);
            Looks[id] = look;
            Debug.Log($"[OV Lobby] {name} ({id}) joined from client {c.ClientId}");
            PushState();
        }

        void OnReady(NetworkConnection c, MenuLobbyReadyBroadcast m, Channel channel)
        {
            if (Current != Role.Host || c == null || !idByConnection.TryGetValue(c.ClientId, out string id)) return;
            Roster.SetReady(id, m.Ready);
            PushState();
        }

        void Refuse(NetworkConnection c, string reason)
        {
            Debug.Log($"[OV Lobby] client {c.ClientId} refused: {reason}");
            Manager.ServerManager.Broadcast(c, new MenuLobbyNoticeBroadcast { Kind = 1, Text = reason }, false);
            StartCoroutine(KickSoon(c));
        }

        IEnumerator KickSoon(NetworkConnection c)
        {
            yield return new WaitForSecondsRealtime(0.35f);
            if (c != null && c.IsActive) Manager.ServerManager.Kick(c, KickReason.UnexpectedProblem);
        }

        void PushState()
        {
            Changed?.Invoke();
            if (Current != Role.Host || Manager == null || !Manager.ServerManager.Started) return;
            var s = new MenuLobbyStateBroadcast { World = WorldName, Mode = (byte)WorldMode.Multiplayer, Members = EncodeMembers() };
            foreach (var kv in idByConnection)
                if (Manager.ServerManager.Clients.TryGetValue(kv.Key, out NetworkConnection c) && c.IsActive) Manager.ServerManager.Broadcast(c, s, false);
        }

        string EncodeMembers()
        {
            var sb = new StringBuilder();
            foreach (var m in Roster.Members)
            {
                if (sb.Length > 0) sb.Append('\n');
                string look = Looks.TryGetValue(m.PlayerId, out var a) ? AppearanceRules.Encode(a) : "";
                sb.Append(m.PlayerId).Append('|').Append((m.Name ?? "").Replace("|", "").Replace("\n", "")).Append('|')
                  .Append(m.IsHost ? '1' : '0').Append('|').Append(m.Ready ? '1' : '0').Append('|').Append(look);
            }
            return sb.ToString();
        }

        /// <summary>Host: tells everyone the world starts, then stops this server (the map has its own) and calls back.</summary>
        public void HostStart(Action then)
        {
            if (Current != Role.Host) { then?.Invoke(); return; }
            int guests = Roster.Count - 1;
            if (guests > 0)
                foreach (var kv in idByConnection)
                    if (Manager.ServerManager.Clients.TryGetValue(kv.Key, out NetworkConnection c) && c.IsActive)
                        Manager.ServerManager.Broadcast(c, new MenuLobbyNoticeBroadcast
                        {
                            Kind = 2,
                            Text = "Хост запустил мир «" + WorldName + "». Совместная игра на карте появится с сетевым этапом M1 (игроки на карте): пока мир открыт только у хоста.",
                        }, false);
            StartCoroutine(StartThen(then, guests > 0 ? 0.4f : 0f));
        }

        IEnumerator StartThen(Action then, float delay)
        {
            if (delay > 0f) yield return new WaitForSecondsRealtime(delay);
            Shutdown(false);
            then?.Invoke();
        }

        /// <summary>The LAN addresses friends can type (IPv4 of the up interfaces), for the host's lobby screen.</summary>
        public static List<string> LocalAddresses()
        {
            var list = new List<string>();
            try
            {
                foreach (NetworkInterface ni in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (ni.OperationalStatus != OperationalStatus.Up || ni.NetworkInterfaceType == NetworkInterfaceType.Loopback) continue;
                    foreach (UnicastIPAddressInformation ua in ni.GetIPProperties().UnicastAddresses)
                        if (ua.Address.AddressFamily == AddressFamily.InterNetwork && !IPAddress.IsLoopback(ua.Address) && !list.Contains(ua.Address.ToString()))
                            list.Add(ua.Address.ToString());
                }
            }
            catch (Exception) { }
            return list;
        }

        // ================================================================== client

        public bool Connect(string address, ushort port, out string error)
        {
            error = "";
            if (Manager == null) { error = "В сцене меню нет сетевого менеджера."; return false; }
            Shutdown(false);
            Bind();
            Address = (address ?? "").Trim();
            Port = port;
            Roster = new LobbyRoster();
            Looks.Clear();
            clientStarted = false; clientInLobby = false; noticeReceived = false; noticeText = "";
            Manager.TransportManager.Transport.SetClientAddress(Address);
            if (!Manager.ClientManager.StartConnection(Address, Port))
            {
                error = "Не удалось начать подключение к " + Address + ":" + Port + " (адрес?).";
                return false;
            }
            Current = Role.Client;
            connectDeadline = Time.unscaledTime + ConnectTimeoutSeconds;
            Debug.Log($"[OV Lobby] connecting to {Address}:{Port}");
            return true;
        }

        public void SetReady(bool ready)
        {
            if (Current != Role.Client || Manager == null || !Manager.ClientManager.Started) return;
            Manager.ClientManager.Broadcast(new MenuLobbyReadyBroadcast { Ready = ready });
        }

        void OnClientState(ClientConnectionStateArgs args)
        {
            if (Current != Role.Client) return;
            if (args.ConnectionState == LocalConnectionState.Started)
            {
                clientStarted = true;
                Manager.ClientManager.Broadcast(new MenuLobbyHelloBroadcast { PlayerId = TeamEconomy.LocalPlayerGuid, Name = LocalName, Look = AppearanceProfileV01.LocalWire });
                Debug.Log("[OV Lobby] connected, hello sent");
            }
            else if (args.ConnectionState == LocalConnectionState.Stopped)
            {
                Role was = Current;
                Current = Role.None;
                connectDeadline = -1f;
                if (was != Role.Client) return;
                string where = Address + ":" + Port;
                if (noticeReceived) Report?.Invoke(MenuInputV2.WithText(clientInLobby ? MenuActionV2.LobbyEnded : MenuActionV2.ConnectFailed, noticeText));
                else if (!clientStarted) Report?.Invoke(MenuInputV2.WithText(MenuActionV2.ConnectFailed, "Хост не отвечает (" + where + "): проверьте адрес и порт, запущено ли у него лобби и не закрыт ли порт брандмауэром."));
                else if (!clientInLobby) Report?.Invoke(MenuInputV2.WithText(MenuActionV2.ConnectFailed, "Хост разорвал соединение до входа в лобби (" + where + ")."));
                else Report?.Invoke(MenuInputV2.WithText(MenuActionV2.Disconnected, "Соединение с хостом потеряно (" + where + ")."));
                Changed?.Invoke();
            }
        }

        void OnState(MenuLobbyStateBroadcast s, Channel channel)
        {
            if (Current != Role.Client) return;
            WorldName = s.World ?? "";
            Roster = new LobbyRoster();
            Looks.Clear();
            foreach (string line in (s.Members ?? "").Split('\n'))
            {
                string[] p = line.Split('|');
                if (p.Length < 4) continue;
                Roster.Join(p[0], p[1], p[2] == "1");
                if (p[2] != "1") Roster.SetReady(p[0], p[3] == "1");
                if (p.Length > 4 && AppearanceRules.TryDecode(p[4], out var look)) Looks[p[0]] = look;
            }
            if (!clientInLobby)
            {
                clientInLobby = true;
                connectDeadline = -1f;
                Report?.Invoke(MenuInputV2.Of(MenuActionV2.Connected));
            }
            Changed?.Invoke();
        }

        void OnNotice(MenuLobbyNoticeBroadcast n, Channel channel)
        {
            if (Current != Role.Client) return;
            noticeReceived = true;
            noticeText = n.Text ?? "";
            Debug.Log($"[OV Lobby] host notice {n.Kind}: {noticeText}");
            if (n.Kind == 2 || n.Kind == 3) Manager.ClientManager.StopConnection();
        }

        void Update()
        {
            if (Current == Role.Client && connectDeadline > 0f && !clientInLobby && Time.unscaledTime > connectDeadline)
            {
                connectDeadline = -1f;
                Debug.Log("[OV Lobby] connect timeout");
                Manager.ClientManager.StopConnection(); // reported through OnClientState (Stopped, not started)
            }
        }

        // ================================================================== both

        /// <summary>Leaves / closes whatever is running (Back from a lobby). notify = tell the guests the lobby closed.</summary>
        public void Shutdown(bool notify)
        {
            if (Manager == null) return;
            if (Current == Role.Host && notify && Manager.ServerManager.Started)
                foreach (var kv in idByConnection)
                    if (Manager.ServerManager.Clients.TryGetValue(kv.Key, out NetworkConnection c) && c.IsActive)
                        Manager.ServerManager.Broadcast(c, new MenuLobbyNoticeBroadcast { Kind = 3, Text = "Хост закрыл лобби." }, false);
            Role was = Current;
            Current = Role.None; // so the Stopped events below report nothing
            connectDeadline = -1f;
            if (Manager.ClientManager.Started) Manager.ClientManager.StopConnection();
            if (Manager.ServerManager.Started) Manager.ServerManager.StopConnection(true);
            idByConnection.Clear();
            if (was != Role.None) Changed?.Invoke();
        }

        /// <summary>Before the map loads: stop everything and remove this menu's NetworkManager (the map brings its own).</summary>
        public void ReleaseForWorld()
        {
            Shutdown(false);
            Unbind();
            if (Manager != null) Destroy(Manager.gameObject);
            Manager = null;
        }
    }
}
