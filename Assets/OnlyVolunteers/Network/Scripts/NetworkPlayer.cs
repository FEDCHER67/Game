using System;
using System.Collections;
using FishNet.Component.Transforming;
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
        private float nextViewSend;

        public bool LocalControlEnabled => input != null && input.enabled;
        public Camera ViewCamera => viewCamera;
        public Vector3 MotorPosition => character != null && character.Motor != null
            ? character.Motor.transform.position : transform.position;
        public Collider PlayerCollider => character != null && character.Motor != null
            ? character.Motor.Capsule : null;

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
            SetLocalControl(false);
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
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
                NetworkSession.Active?.LocalPlayerChanged(this);
            }
            else
            {
                ApplyDebugColor();
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
            if (!IsOwner || viewCamera == null || Time.unscaledTime < nextViewSend)
                return;
            nextViewSend = Time.unscaledTime + 0.1f;
            ServerViewOrientation(Mathf.DeltaAngle(0f, viewCamera.transform.eulerAngles.x),
                viewCamera.transform.eulerAngles.y, Channel.Unreliable);
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
