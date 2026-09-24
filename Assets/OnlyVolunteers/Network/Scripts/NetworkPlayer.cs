using FishNet.Object;
using FishNet.Transporting;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Debugging;
using OnlyVolunteers.Player.Physics;
using UnityEngine;

namespace OnlyVolunteers.Network
{
    [RequireComponent(typeof(NetworkObject))]
    public sealed class NetworkPlayer : NetworkBehaviour
    {
        private KccFirstPersonInput input;
        private ExampleCharacterController character;
        private PhysicsGrabber localPhysicsGrabber;
        private Camera viewCamera;
        private AudioListener listener;
        private Transform visualRoot;
        private Transform visualHead;
        private GameObject localHud;
        private GameObject localCrosshair;
        private float nextPitchSend;

        public bool LocalControlEnabled => input != null && input.enabled;
        public Camera ViewCamera => viewCamera;
        public Collider PlayerCollider => character != null && character.Motor != null
            ? character.Motor.Capsule : null;

        private void Awake()
        {
            input = GetComponent<KccFirstPersonInput>();
            character = input != null ? input.Character : GetComponent<ExampleCharacterController>();
            localPhysicsGrabber = GetComponent<PhysicsGrabber>();
            viewCamera = input != null ? input.ViewCamera : GetComponentInChildren<Camera>(true);
            listener = viewCamera != null ? viewCamera.GetComponent<AudioListener>() : null;
            visualRoot = transform.Find("RemoteVisual");
            visualHead = transform.Find("RemoteVisual/Head");
            SetLocalControl(false);
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
            SetLocalControl(IsOwner);
            Debug.Log($"[OV Network] observed player={OwnerId}, owner={IsOwner}, " +
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
                NetworkSession.Active?.LocalPlayerChanged(this);
            }
            else
            {
                ApplyDebugColor();
            }
        }

        public override void OnStopClient()
        {
            Debug.Log($"[OV Network] player removed={OwnerId}, owner={IsOwner}");
            if (IsOwner)
                NetworkSession.Active?.LocalPlayerChanged(null);
            SetLocalControl(false);
            if (localHud != null) Destroy(localHud);
            if (localCrosshair != null) Destroy(localCrosshair);
            base.OnStopClient();
        }

        public void SetPanelOpen(bool open)
        {
            if (IsOwner && input != null)
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
            if (!IsOwner || viewCamera == null || Time.unscaledTime < nextPitchSend)
                return;
            nextPitchSend = Time.unscaledTime + 0.1f;
            ServerViewPitch(Mathf.DeltaAngle(0f, viewCamera.transform.eulerAngles.x), Channel.Unreliable);
        }

        [ServerRpc]
        private void ServerViewPitch(float pitch, Channel channel = Channel.Unreliable)
        {
            if (Owner == null || !Owner.IsActive || float.IsNaN(pitch) ||
                float.IsInfinity(pitch) || Mathf.Abs(pitch) > 86f)
                return;
            ObserversViewPitch(pitch, Channel.Unreliable);
        }

        [ObserversRpc(ExcludeOwner = true)]
        private void ObserversViewPitch(float pitch, Channel channel = Channel.Unreliable)
        {
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
    }
}
