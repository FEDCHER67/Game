using System;
using System.Collections;
using FishNet.Connection;
using FishNet.Object;
using FishNet.Transporting;
using OnlyVolunteers.Player.Physics;
using UnityEngine;

namespace OnlyVolunteers.Network
{
    [RequireComponent(typeof(NetworkPlayer))]
    public sealed class NetworkGrabber : NetworkBehaviour
    {
        private const float SendInterval = 0.05f;

        [SerializeField] private GrabPhysicsProfile profile;
        private NetworkPlayer player;
        private NetworkPhysicsBody serverHeld;
        private NetworkObject clientHeld;
        private bool pending;
        private bool targetLogged;
        private bool smokeHolding;
        private Vector3 smokeTarget;
        private float nextSend;

        public Collider PlayerCollider => player != null ? player.PlayerCollider : null;
        public bool IsValidHolder => IsServerStarted && Owner != null && Owner.IsActive;

        private void Awake()
        {
            player = GetComponent<NetworkPlayer>();
            if (profile == null)
                Debug.LogError("NetworkGrabber requires a GrabPhysicsProfile", this);
        }

        public override void OnStartClient()
        {
            base.OnStartClient();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if (IsOwner && Array.Exists(Environment.GetCommandLineArgs(), x => x == "-ov-smoke-grab"))
                StartCoroutine(GrabProbe());
#endif
        }

        public override void OnStopServer()
        {
            if (serverHeld != null) serverHeld.Release(this);
            base.OnStopServer();
        }

        public override void OnStopClient()
        {
            clientHeld = null;
            pending = false;
            smokeHolding = false;
            base.OnStopClient();
        }

        private void Update()
        {
            if (!IsOwner || player == null || player.ViewCamera == null || profile == null) return;
            if (Cursor.lockState != CursorLockMode.Locked && !smokeHolding)
            {
                if (clientHeld != null || pending) ReleaseClient();
                return;
            }

            if (Input.GetMouseButtonUp(0) ||
                (clientHeld != null && !Input.GetMouseButton(0) && !smokeHolding))
            {
                ReleaseClient();
                return;
            }

            if (Input.GetMouseButtonDown(0) && clientHeld == null && !pending)
                TryGrabRay(new Ray(player.ViewCamera.transform.position, player.ViewCamera.transform.forward));

            if (clientHeld != null && Time.unscaledTime >= nextSend)
            {
                nextSend = Time.unscaledTime + SendInterval;
                Vector3 target = smokeHolding ? smokeTarget : player.ViewCamera.transform.position +
                    player.ViewCamera.transform.forward * profile.HoldDistance;
                ServerHoldTarget(target, Channel.Unreliable);
            }
        }

        private void TryGrabRay(Ray ray)
        {
            Debug.Log($"[OV Grab] request input owner={OwnerId}, cursor={Cursor.lockState}, origin={ray.origin}, direction={ray.direction}");
            if (Physics.Raycast(ray, out RaycastHit hit, profile.AcquireDistance,
                profile.AcquisitionLayers, QueryTriggerInteraction.Ignore))
            {
                var networkBody = hit.rigidbody != null
                    ? hit.rigidbody.GetComponent<NetworkPhysicsBody>() : null;
                Debug.Log($"[OV Grab] client hit={hit.collider.name}, rigidbody={hit.rigidbody?.name}, " +
                    $"networkBody={networkBody?.name}, spawned={networkBody != null && networkBody.NetworkObject.IsSpawned}");
                if (networkBody != null && networkBody.NetworkObject.IsSpawned)
                {
                    pending = true;
                    Debug.Log($"[OV Grab] request sent owner={OwnerId}, body={networkBody.name}");
                    ServerTryGrab(networkBody.NetworkObject, ray.origin, ray.direction);
                }
            }
            else Debug.Log("[OV Grab] client ray missed");
        }

        private void ReleaseClient()
        {
            clientHeld = null;
            pending = false;
            smokeHolding = false;
            if (IsClientStarted) ServerRelease();
        }

        [ServerRpc]
        private void ServerTryGrab(NetworkObject candidate, Vector3 origin, Vector3 direction,
            NetworkConnection sender = null)
        {
            if (sender == null || sender != Owner || !sender.IsActive ||
                profile == null || serverHeld != null || candidate == null || !candidate.IsSpawned ||
                !GrabPhysicsSolver.IsFinite(origin) || !GrabPhysicsSolver.IsFinite(direction) ||
                direction.sqrMagnitude < 0.9f || direction.sqrMagnitude > 1.1f ||
                Vector3.Distance(origin, player.MotorPosition) > 2.4f)
            {
                Debug.Log($"[OV Grab] server preflight rejected: sender={sender?.ClientId}, owner={OwnerId}, " +
                    $"held={serverHeld != null}, spawned={candidate != null && candidate.IsSpawned}, " +
                    $"origin={origin}, motor={player.MotorPosition}, distance={Vector3.Distance(origin, player.MotorPosition):F2}");
                if (sender != null && sender.IsActive) TargetGrabResult(sender, null);
                return;
            }

            var body = candidate.GetComponent<NetworkPhysicsBody>();
            if (body == null || !body.IsServerStarted || body.Body == null ||
                NetworkSession.Active == null || !NetworkSession.Active.IsAllowedBody(body) ||
                body.transform.IsChildOf(transform) ||
                Vector3.Distance(body.transform.position, player.MotorPosition) > profile.AcquireDistance + 2f)
            {
                Debug.Log($"[OV Grab] server target rejected: body={body?.name}, " +
                    $"allowed={body != null && NetworkSession.Active != null && NetworkSession.Active.IsAllowedBody(body)}, " +
                    $"distance={((body != null) ? Vector3.Distance(body.transform.position, player.MotorPosition) : -1f):F2}");
                TargetGrabResult(sender, null);
                return;
            }

            Ray ray = new Ray(origin, direction.normalized);
            bool hitBody = Physics.Raycast(ray, out RaycastHit hit, profile.AcquireDistance,
                profile.AcquisitionLayers, QueryTriggerInteraction.Ignore);
            if (!hitBody || hit.rigidbody != body.Body)
            {
                Debug.Log($"[OV Grab] server ray rejected: hit={hitBody}, collider={(hitBody ? hit.collider.name : "none")}, " +
                    $"rigidbody={(hitBody ? hit.rigidbody?.name : "none")}, requested={body.name}");
                TargetGrabResult(sender, null);
                return;
            }

            if (!body.TryAcquire(this, hit.point, origin + direction.normalized * profile.HoldDistance))
            {
                Debug.Log($"[OV Grab] server acquire rejected: body={body.name}, held={body.HasHolder}");
                TargetGrabResult(sender, null);
                return;
            }

            serverHeld = body;
            targetLogged = false;
            TargetGrabResult(sender, candidate);
        }

        [TargetRpc]
        private void TargetGrabResult(NetworkConnection target, NetworkObject body)
        {
            pending = false;
            Debug.Log($"[OV Grab] client result: granted={body != null}, owner={OwnerId}");
            if (body != null && IsOwner && (smokeHolding ||
                (Input.GetMouseButton(0) && Cursor.lockState == CursorLockMode.Locked)))
            {
                clientHeld = body;
                nextSend = 0f;
            }
            else if (body != null)
            {
                ServerRelease();
            }
            else smokeHolding = false;
        }

        [ServerRpc]
        private void ServerHoldTarget(Vector3 target, Channel channel = Channel.Unreliable)
        {
            if (serverHeld == null || Owner == null || !Owner.IsActive ||
                !GrabPhysicsSolver.IsFinite(target) ||
                Vector3.Distance(target, player.MotorPosition) > 5f)
                return;
            serverHeld.SetTarget(this, target);
            if (!targetLogged)
            {
                targetLogged = true;
                Debug.Log($"[OV Grab] server hold target received: body={serverHeld.name}, target={target}");
            }
        }

        [ServerRpc]
        private void ServerRelease()
        {
            if (serverHeld != null) serverHeld.Release(this);
        }

        public void ServerBodyReleased(NetworkPhysicsBody body)
        {
            if (serverHeld != body) return;
            serverHeld = null;
            targetLogged = false;
            if (Owner != null && Owner.IsActive)
                TargetReleased(Owner);
        }

        [TargetRpc]
        private void TargetReleased(NetworkConnection target)
        {
            clientHeld = null;
            pending = false;
            smokeHolding = false;
        }

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator GrabProbe()
        {
            if (OwnerId > 1) yield break;
            yield return new WaitForSeconds(OwnerId == 1 ? 5f : 10f);
            yield return ProbeAttempt();
            if (OwnerId == 1)
            {
                yield return new WaitForSeconds(5f);
                Debug.Log("[OV Smoke] holder disconnect requested");
                NetworkSession.Active?.StopSession();
            }
            else
            {
                yield return new WaitForSeconds(7f);
                yield return ProbeAttempt();
                yield return new WaitForSeconds(4f);
                Debug.Log("[OV Smoke] host release requested");
                ReleaseClient();
            }
        }

        private IEnumerator ProbeAttempt()
        {
            NetworkPhysicsBody targetBody = null;
            foreach (var body in FindObjectsByType<NetworkPhysicsBody>(FindObjectsSortMode.None))
                if (body.NetworkObject.IsSpawned && body.NetworkObject.ObjectId == 0)
                    targetBody = body;
            if (targetBody == null)
            {
                Debug.Log("[OV Smoke] target body 0 unavailable");
                yield break;
            }

            var input = GetComponent<OnlyVolunteers.Player.KccFirstPersonInput>();
            var motor = input.Character.Motor;
            var foot = targetBody.transform.position + new Vector3(OwnerId == 0 ? 1.25f : -1.25f,
                -targetBody.transform.position.y + 0.02f, -1.5f);
            motor.SetPosition(foot);
            yield return new WaitForSeconds(1f);
            smokeHolding = true;
            smokeTarget = targetBody.transform.position + Vector3.up * 1.2f + Vector3.forward * 1.5f;
            var camera = player.ViewCamera.transform;
            var ray = new Ray(camera.position, (targetBody.transform.position - camera.position).normalized);
            Debug.Log($"[OV Smoke] grab attempt owner={OwnerId}, motor={player.MotorPosition}, body={targetBody.transform.position}");
            TryGrabRay(ray);
        }
#endif
    }
}
