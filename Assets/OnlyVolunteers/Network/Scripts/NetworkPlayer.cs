using System;
using System.Collections;
using FishNet.Component.Transforming;
using FishNet.Object;
using FishNet.Object.Synchronizing;
using FishNet.Transporting;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Debugging;
using OnlyVolunteers.Player.Physics;
using OnlyVolunteers.Session;
using UnityEngine;

namespace OnlyVolunteers.Network
{
    [RequireComponent(typeof(NetworkObject))]
    public sealed class NetworkPlayer : NetworkBehaviour
    {
        [Tooltip("Capture → delivery stage A (map scene as a solo host): this NetworkPlayer sits on the map's own KCC pawn, " +
                 "which keeps its own control, camera, HUD and phone. The NetworkPlayer then never switches them and only " +
                 "gives the networked operation code a player identity. Off on every network prefab.")]
        [SerializeField] private bool externalControl;
        private KccFirstPersonInput input;
        private ExampleCharacterController character;
        private PhysicsGrabber localPhysicsGrabber;
        private Camera viewCamera;
        private AudioListener listener;
        private Transform visualRoot;
        private Transform visualHead;
        private GameObject localHud;
        private GameObject localCrosshair;
        private PhoneController phone;
        private float nextViewSend;
        /// <summary>PLAYER stage: this player's look as the server accepted it (AppearanceRules wire text). Only the server
        /// writes it, only from the OWNER's own submission; observers and late joiners receive it with the object, so every
        /// friend sees each player's own look and a rejoin never copies the host's.</summary>
        private readonly SyncVar<string> appearanceWire = new SyncVar<string>("");

        /// <summary>The look of this player (default until the server accepted his own).</summary>
        public PlayerAppearance Appearance { get; private set; } = AppearanceRules.Default();
        public event Action<NetworkPlayer> AppearanceChanged;

        public bool LocalControlEnabled => input != null && input.enabled;
        // The phone occupies the hands: no grabbing while it is out.
        public bool HandsBusy => phone != null && phone.IsOpen;
        public Camera ViewCamera => viewCamera;
        public Vector3 MotorPosition => character != null && character.Motor != null
            ? character.Motor.transform.position : transform.position;
        public Collider PlayerCollider => character != null && character.Motor != null
            ? character.Motor.Capsule : null;
        /// <summary>Horizontal facing of the moving body (replicated with the motor), for carried objects.</summary>
        public Vector3 MotorForward => character != null && character.Motor != null
            ? character.Motor.transform.forward : transform.forward;

        /// <summary>Owner only: hides the first-person crosshair and the physics HUD (e.g. while the operation table
        /// view owns the screen) and shows them again.</summary>
        public void SetLocalHudVisible(bool visible)
        {
            if (localHud != null) localHud.SetActive(visible);
            if (localCrosshair != null) localCrosshair.SetActive(visible && (phone == null || !phone.IsOpen));
        }

        private void Awake()
        {
            input = GetComponent<KccFirstPersonInput>();
            character = input != null ? input.Character : GetComponent<ExampleCharacterController>();
            localPhysicsGrabber = GetComponent<PhysicsGrabber>();
            viewCamera = input != null ? input.ViewCamera : GetComponentInChildren<Camera>(true);
            listener = viewCamera != null ? viewCamera.GetComponent<AudioListener>() : null;
            visualRoot = character != null && character.Motor != null
                ? character.Motor.transform.Find("RemoteVisual") : null;
            visualHead = visualRoot != null ? visualRoot.Find("Head") : null;
            appearanceWire.OnChange += OnAppearanceWire;
            if (!externalControl) SetLocalControl(false);
        }

        private void OnDestroy() => appearanceWire.OnChange -= OnAppearanceWire;

        public bool ExternalControl => externalControl;

        public override void OnStartClient()
        {
            base.OnStartClient();
            if (externalControl)
            {
                Debug.Log($"[OV Network] observed external-control player={OwnerId}, owner={IsOwner}, motor={MotorPosition}");
                if (IsOwner) { NetworkSession.Active?.LocalPlayerChanged(this); ServerSubmitAppearance(AppearanceProfileV01.LocalWire); }
                return;
            }
            SetLocalControl(IsOwner);
            Debug.Log($"[OV Network] observed player={OwnerId}, owner={IsOwner}, root={transform.position}, motor={MotorPosition}, " +
                $"input={LocalControlEnabled}, camera={viewCamera != null && viewCamera.enabled}, " +
                $"listener={listener != null && listener.enabled}, motor={character != null && character.Motor != null && character.Motor.enabled}");
            if (visualRoot != null)
                visualRoot.gameObject.SetActive(!IsOwner);
            if (IsOwner)
            {
                localHud = new GameObject("[Network] Physics HUD");
                localHud.AddComponent<PhysicsDiagnosticsHud>();
                localCrosshair = new GameObject("[Network] Crosshair");
                localCrosshair.AddComponent<TestCrosshairHud>();
                phone = PhoneController.Create(viewCamera, input);
                phone.OpenChanged += open => { if (localCrosshair != null) localCrosshair.SetActive(!open); };
                NetworkSession.Active?.LocalPlayerChanged(this);
                ServerSubmitAppearance(AppearanceProfileV01.LocalWire); // my own look, from my own profile
            }
            else
            {
                ApplyDebugColor();
                if (!string.IsNullOrEmpty(appearanceWire.Value)) OnAppearanceWire("", appearanceWire.Value, false); // late join
            }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (Array.Exists(Environment.GetCommandLineArgs(), x => x == "-ov-smoke-move"))
                StartCoroutine(ReplicationProbe());
#endif
        }

        public override void OnStopClient()
        {
            Debug.Log($"[OV Network] player removed={OwnerId}, owner={IsOwner}");
            if (IsOwner)
                NetworkSession.Active?.LocalPlayerChanged(null);
            if (!externalControl) SetLocalControl(false);
            if (localHud != null) Destroy(localHud);
            if (localCrosshair != null) Destroy(localCrosshair);
            if (phone != null) Destroy(phone.gameObject);
            base.OnStopClient();
        }

        public void SetPanelOpen(bool open)
        {
            if (IsOwner && input != null && !externalControl)
                input.enabled = !open;
        }

        private void SetLocalControl(bool enabled)
        {
            if (input != null) input.enabled = enabled;
            if (localPhysicsGrabber != null) localPhysicsGrabber.enabled = false;
            if (character != null)
            {
                character.enabled = enabled;
                if (character.Motor != null) character.Motor.enabled = enabled;
            }
            if (viewCamera != null) viewCamera.enabled = enabled;
            if (listener != null) listener.enabled = enabled;
        }

        private void Update()
        {
            if (!IsOwner || viewCamera == null || Time.unscaledTime < nextViewSend)
                return;
            nextViewSend = Time.unscaledTime + 0.1f;
            ServerViewOrientation(Mathf.DeltaAngle(0f, viewCamera.transform.eulerAngles.x),
                viewCamera.transform.eulerAngles.y, Channel.Unreliable);
        }

        /// <summary>Owner → server: his own look. Validated (unknown cosmetics → defaults, garbage → the default look, never
        /// another player's), recorded under his stable participant id, then replicated to everyone through the SyncVar.</summary>
        [ServerRpc]
        private void ServerSubmitAppearance(string wire)
        {
            if (Owner == null || !Owner.IsActive) return;
            AppearanceRules.TryDecode(wire, out var look);
            string encoded = AppearanceRules.Encode(look);
            var economy = OnlyVolunteers.Economy.TeamEconomy.Instance;
            string playerId = economy != null ? economy.ServerParticipantId(Owner) : (Owner.IsLocalClient ? PlayerIds.Host : "client:" + Owner.ClientId);
            AppearanceProfileV01.ServerBook.Submit(playerId, encoded, out _); // a not-yet-identified client ("client:N") is not stored
            appearanceWire.Value = encoded;
            Debug.Log($"[OV Network] appearance player={OwnerId} id={playerId}: {encoded}");
        }

        private void OnAppearanceWire(string previous, string next, bool asServer)
        {
            if (asServer) return; // the host also gets the client-side callback; a dedicated server has nothing to show
            AppearanceRules.TryDecode(next, out var look);
            Appearance = look;
            ApplyAppearanceToRemoteVisual();
            AppearanceChanged?.Invoke(this);
        }

        /// <summary>First pass until the chosen avatar model exists: the remote placeholder body wears the top colour and
        /// the head the skin colour. The avatar binding (stage 2) replaces this with real parts.</summary>
        private void ApplyAppearanceToRemoteVisual()
        {
            if (visualRoot == null || IsOwner) return;
            var block = new MaterialPropertyBlock();
            Color top = AppearanceProfileV01.Swatch(Appearance, AppearanceSlot.TopColour, Color.grey);
            Color skin = AppearanceProfileV01.Swatch(Appearance, AppearanceSlot.Skin, Color.white);
            foreach (var renderer in visualRoot.GetComponentsInChildren<Renderer>(true))
            {
                bool head = visualHead != null && renderer.transform.IsChildOf(visualHead);
                block.SetColor("_BaseColor", head ? skin : top);
                renderer.SetPropertyBlock(block);
            }
        }

        [ServerRpc]
        private void ServerViewOrientation(float pitch, float yaw, Channel channel = Channel.Unreliable)
        {
            if (Owner == null || !Owner.IsActive || float.IsNaN(pitch) ||
                float.IsInfinity(pitch) || Mathf.Abs(pitch) > 86f ||
                float.IsNaN(yaw) || float.IsInfinity(yaw) || yaw < 0f || yaw >= 360f)
                return;
            ObserversViewOrientation(pitch, yaw, Channel.Unreliable);
        }

        [ObserversRpc(ExcludeOwner = true)]
        private void ObserversViewOrientation(float pitch, float yaw, Channel channel = Channel.Unreliable)
        {
            if (visualRoot != null)
                visualRoot.rotation = Quaternion.Euler(0f, yaw, 0f);
            if (visualHead != null)
                visualHead.localRotation = Quaternion.Euler(pitch, 0f, 0f);
        }

        private void ApplyDebugColor()
        {
            if (visualRoot == null) return;
            Color color = Color.HSVToRGB(Mathf.Repeat(OwnerId * 0.23f, 1f), 0.65f, 0.9f);
            var block = new MaterialPropertyBlock();
            block.SetColor("_BaseColor", color);
            foreach (var renderer in visualRoot.GetComponentsInChildren<Renderer>(true))
                renderer.SetPropertyBlock(block);
        }

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator ReplicationProbe()
        {
            yield return new WaitForSeconds(2f);
            LogReplicationPose("before");
            yield return new WaitForSeconds(6f);
            if (IsOwner && character != null && character.Motor != null)
            {
                character.Motor.SetPosition(MotorPosition + Vector3.forward * 4f);
                var yawField = typeof(KccFirstPersonInput).GetField("_yaw",
                    System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                if (yawField != null && input != null)
                    yawField.SetValue(input, Mathf.Repeat((float)yawField.GetValue(input) + 45f, 360f));
                yield return null;
                LogReplicationPose("owner-moved");
            }
            yield return new WaitForSeconds(4f);
            LogReplicationPose("after");
        }

        private void LogReplicationPose(string stage)
        {
            var motor = character != null ? character.Motor : null;
            var networkTransform = GetComponentInChildren<NetworkTransform>(true);
            Debug.Log($"[OV Smoke] player stage={stage}, id={OwnerId}, owner={IsOwner}, server={IsServerStarted}, " +
                $"root={transform.position}, motor={MotorPosition}, transient={motor?.TransientPosition}, " +
                $"networkTarget={networkTransform?.transform.position}, visual={visualRoot?.position}, " +
                $"yaw={(motor != null ? motor.transform.eulerAngles.y : 0f):F1}, " +
                $"cameraYaw={(viewCamera != null ? viewCamera.transform.eulerAngles.y : 0f):F1}, " +
                $"visualYaw={(visualRoot != null ? visualRoot.eulerAngles.y : 0f):F1}");
        }
#endif
    }
}
