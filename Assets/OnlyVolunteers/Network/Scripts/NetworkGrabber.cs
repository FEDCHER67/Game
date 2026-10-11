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
        private uint serverHoldId;
        private uint lastServerRequestId;
        private NetworkObject clientHeld;
        private uint clientHoldId;
        private uint pendingId;
        private uint nextRequestId;
        private uint targetSequence;
        private float pendingHoldDistance;
        private float clientHoldDistance;
        private float pendingHoldHeight;
        private float clientHoldHeight;
        private bool pendingGroundPlaneFollow;
        private bool clientGroundPlaneFollow;
        private bool pending;
        private bool targetLogged;
        private bool smokeHolding;
        private Vector3 smokeTarget;
        private float nextSend;

        public Collider PlayerCollider => player != null ? player.PlayerCollider : null;
        public Vector3 MotorPosition => player != null ? player.MotorPosition : Vector3.positiveInfinity;
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
            if (IsOwner)
            {
                string[] args = Environment.GetCommandLineArgs();
                if (Array.Exists(args, x => x == "-ov-smoke-gurney-sprint-z"))
                    StartCoroutine(GurneySprintProbe(true));
                else if (Array.Exists(args, x => x == "-ov-smoke-gurney-sprint"))
                    StartCoroutine(GurneySprintProbe(false));
                else if (Array.Exists(args, x => x == "-ov-smoke-feel-opposed"))
                    StartCoroutine(CoopFeelProbe(true));
                else if (Array.Exists(args, x => x == "-ov-smoke-feel"))
                    StartCoroutine(CoopFeelProbe(false));
                else if (Array.Exists(args, x => x == "-ov-smoke-coop"))
                    StartCoroutine(CoopGrabProbe());
                else if (Array.Exists(args, x => x == "-ov-smoke-grab"))
                    StartCoroutine(GrabProbe());
            }
#endif
        }

        public override void OnStopServer()
        {
            if (serverHeld != null) serverHeld.Release(this, serverHoldId);
            base.OnStopServer();
        }

        public override void OnStopClient()
        {
            clientHeld = null;
            clientHoldId = 0;
            pendingId = 0;
            targetSequence = 0;
            pendingHoldDistance = 0f;
            clientHoldDistance = 0f;
            pendingHoldHeight = 0f;
            clientHoldHeight = 0f;
            pendingGroundPlaneFollow = false;
            clientGroundPlaneFollow = false;
            pending = false;
            smokeHolding = false;
            base.OnStopClient();
        }

        private void Update()
        {
            if (!IsOwner || player == null || player.ViewCamera == null || profile == null) return;
            if ((Cursor.lockState != CursorLockMode.Locked || player.HandsBusy) && !smokeHolding)
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
                Transform camera = player.ViewCamera.transform;
                Vector3 target = smokeHolding ? smokeTarget : clientGroundPlaneFollow
                    ? GroundPlaneTarget(camera.position, camera.forward, camera.right,
                        clientHoldDistance, clientHoldHeight)
                    : camera.position + camera.forward * clientHoldDistance;
                targetSequence++;
                if (targetSequence == 0) targetSequence++;
                ServerHoldTarget(clientHoldId, targetSequence, target, Channel.Unreliable);
            }
        }

        private static Vector3 GroundPlaneTarget(Vector3 cameraPosition, Vector3 cameraForward,
            Vector3 cameraRight, float horizontalDistance, float holdHeight)
        {
            Vector3 horizontalForward = Vector3.ProjectOnPlane(cameraForward, Vector3.up);
            if (horizontalForward.sqrMagnitude < 0.0001f)
                horizontalForward = Vector3.Cross(cameraRight, Vector3.up);
            horizontalForward.Normalize();
            return new Vector3(cameraPosition.x + horizontalForward.x * horizontalDistance,
                holdHeight, cameraPosition.z + horizontalForward.z * horizontalDistance);
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
                    // A request ID is also the hold identity for all later packets.
                    nextRequestId++;
                    if (nextRequestId == 0) nextRequestId++;
                    pendingId = nextRequestId;
                    pendingGroundPlaneFollow = networkBody.GroundPlaneFollow;
                    pendingHoldDistance = pendingGroundPlaneFollow
                        ? Vector2.Distance(new Vector2(ray.origin.x, ray.origin.z),
                            new Vector2(hit.point.x, hit.point.z))
                        : hit.distance;
                    pendingHoldHeight = hit.point.y;
                    pending = true;
                    Debug.Log($"[OV Grab] request sent owner={OwnerId}, body={networkBody.name}");
                    ServerTryGrab(pendingId, networkBody.NetworkObject, ray.origin, ray.direction);
                }
            }
            else Debug.Log("[OV Grab] client ray missed");
        }

        private void ReleaseClient()
        {
            uint releasedId = clientHeld != null ? clientHoldId : pendingId;
            clientHeld = null;
            clientHoldId = 0;
            pendingId = 0;
            targetSequence = 0;
            pendingHoldDistance = 0f;
            clientHoldDistance = 0f;
            pendingHoldHeight = 0f;
            clientHoldHeight = 0f;
            pendingGroundPlaneFollow = false;
            clientGroundPlaneFollow = false;
            pending = false;
            smokeHolding = false;
            if (IsClientStarted && releasedId != 0) ServerRelease(releasedId);
        }

        [ServerRpc]
        private void ServerTryGrab(uint requestId, NetworkObject candidate, Vector3 origin, Vector3 direction,
            NetworkConnection sender = null)
        {
            if (sender == null || sender != Owner || !sender.IsActive) return;
            if (requestId == 0 || requestId <= lastServerRequestId) return;
            lastServerRequestId = requestId;
            if (profile == null || player == null || serverHeld != null || candidate == null || !candidate.IsSpawned ||
                !GrabPhysicsSolver.IsFinite(origin) || !GrabPhysicsSolver.IsFinite(direction) ||
                !GrabPhysicsSolver.IsFinite(MotorPosition) ||
                direction.sqrMagnitude < 0.9f || direction.sqrMagnitude > 1.1f ||
                Vector3.Distance(origin, player.MotorPosition) > 2.4f)
            {
                Debug.Log($"[OV Grab] server preflight rejected: sender={sender?.ClientId}, owner={OwnerId}, " +
                    $"held={serverHeld != null}, spawned={candidate != null && candidate.IsSpawned}, " +
                    $"origin={origin}, motor={MotorPosition}, distance={Vector3.Distance(origin, MotorPosition):F2}");
                if (sender != null && sender.IsActive && sender == Owner)
                    TargetGrabResult(sender, requestId, null);
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
                TargetGrabResult(sender, requestId, null);
                return;
            }

            Ray ray = new Ray(origin, direction.normalized);
            bool hitBody = Physics.Raycast(ray, out RaycastHit hit, profile.AcquireDistance,
                profile.AcquisitionLayers, QueryTriggerInteraction.Ignore);
            if (!hitBody || hit.rigidbody != body.Body)
            {
                Debug.Log($"[OV Grab] server ray rejected: hit={hitBody}, collider={(hitBody ? hit.collider.name : "none")}, " +
                    $"rigidbody={(hitBody ? hit.rigidbody?.name : "none")}, requested={body.name}");
                TargetGrabResult(sender, requestId, null);
                return;
            }

            if (!body.TryAcquire(this, requestId, hit.point, hit.point))
            {
                Debug.Log($"[OV Grab] server acquire rejected: body={body.name}, held={body.HasHolder}");
                TargetGrabResult(sender, requestId, null);
                return;
            }

            serverHeld = body;
            serverHoldId = requestId;
            targetLogged = false;
            TargetGrabResult(sender, requestId, candidate);
        }

        [TargetRpc]
        private void TargetGrabResult(NetworkConnection target, uint requestId, NetworkObject body)
        {
            if (requestId != pendingId) return;
            pending = false;
            pendingId = 0;
            Debug.Log($"[OV Grab] client result: granted={body != null}, owner={OwnerId}");
            if (body != null && IsOwner && (smokeHolding ||
                (Input.GetMouseButton(0) && Cursor.lockState == CursorLockMode.Locked)))
            {
                clientHeld = body;
                clientHoldId = requestId;
                clientHoldDistance = pendingHoldDistance;
                clientHoldHeight = pendingHoldHeight;
                clientGroundPlaneFollow = pendingGroundPlaneFollow;
                targetSequence = 0;
                nextSend = 0f;
            }
            else if (body != null)
            {
                ServerRelease(requestId);
            }
            else smokeHolding = false;
            pendingHoldDistance = 0f;
            pendingHoldHeight = 0f;
            pendingGroundPlaneFollow = false;
        }

        [ServerRpc]
        private void ServerHoldTarget(uint holdId, uint sequence, Vector3 target,
            Channel channel = Channel.Unreliable)
        {
            if (serverHeld == null || holdId == 0 || holdId != serverHoldId || sequence == 0 ||
                Owner == null || !Owner.IsActive || player == null ||
                !GrabPhysicsSolver.IsFinite(target) ||
                !GrabPhysicsSolver.IsFinite(player.MotorPosition) ||
                Vector3.Distance(target, player.MotorPosition) > 5f)
                return;
            serverHeld.SetTarget(this, holdId, sequence, target);
            if (!targetLogged)
            {
                targetLogged = true;
                Debug.Log($"[OV Grab] server hold target received: body={serverHeld.name}, target={target}");
            }
        }

        [ServerRpc]
        private void ServerRelease(uint holdId)
        {
            if (serverHeld != null && holdId == serverHoldId)
                serverHeld.Release(this, holdId);
        }

        public void ServerBodyReleased(NetworkPhysicsBody body, uint holdId)
        {
            if (serverHeld != body || serverHoldId != holdId) return;
            serverHeld = null;
            serverHoldId = 0;
            targetLogged = false;
            if (Owner != null && Owner.IsActive)
                TargetReleased(Owner, holdId);
        }

        [TargetRpc]
        private void TargetReleased(NetworkConnection target, uint holdId)
        {
            if (holdId != clientHoldId && holdId != pendingId) return;
            clientHeld = null;
            clientHoldId = 0;
            pendingId = 0;
            targetSequence = 0;
            pendingHoldDistance = 0f;
            clientHoldDistance = 0f;
            pendingHoldHeight = 0f;
            clientHoldHeight = 0f;
            pendingGroundPlaneFollow = false;
            clientGroundPlaneFollow = false;
            pending = false;
            smokeHolding = false;
        }

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator GurneySprintProbe(bool longitudinal)
        {
            if (OwnerId != 0 || !IsServerStarted) yield break;
            yield return new WaitForSecondsRealtime(3f);

            NetworkPhysicsBody table = null;
            foreach (var candidate in FindObjectsByType<NetworkPhysicsBody>(FindObjectsSortMode.None))
                if (candidate.NetworkObject.IsSpawned && candidate.name.StartsWith("NetworkTableAstra"))
                {
                    table = candidate;
                    break;
                }
            if (table == null)
            {
                Debug.Log("[OV Gurney Sprint] table unavailable");
                yield break;
            }
            if (table.HasHolder)
            {
                Debug.Log("[OV Gurney Sprint] table already held");
                yield break;
            }

            var input = GetComponent<OnlyVolunteers.Player.KccFirstPersonInput>();
            var motor = input.Character.Motor;
            Vector3 foot = table.transform.position + (longitudinal
                ? new Vector3(0f, -table.transform.position.y + 0.02f, -1.75f)
                : new Vector3(1.25f, -table.transform.position.y + 0.02f, 0f));
            motor.SetPosition(foot);
            yield return new WaitForSecondsRealtime(0.5f);

            Vector3 localGrabPoint = Vector3.zero;
            Vector3 aimDirection = Vector3.forward;
            float attemptsEnd = Time.unscaledTime + 5f;
            while (IsClientStarted && clientHeld == null && Time.unscaledTime < attemptsEnd)
            {
                if (!pending)
                {
                    Transform camera = player.ViewCamera.transform;
                    Vector3 aim = table.transform.position + Vector3.up * 0.7f;
                    Ray ray = new Ray(camera.position, (aim - camera.position).normalized);
                    if (Physics.Raycast(ray, out RaycastHit hit, profile.AcquireDistance,
                        profile.AcquisitionLayers, QueryTriggerInteraction.Ignore) &&
                        hit.rigidbody == table.Body)
                    {
                        localGrabPoint = table.transform.InverseTransformPoint(hit.point);
                        aimDirection = ray.direction;
                        smokeHolding = true;
                        smokeTarget = hit.point;
                        TryGrabRay(ray);
                    }
                }
                yield return new WaitForSecondsRealtime(0.25f);
            }
            if (clientHeld != table.NetworkObject)
            {
                Debug.Log($"[OV Gurney Sprint] acquire failed, held={clientHeld != null}");
                ReleaseClient();
                yield break;
            }
            if (table.ActiveHolderCount != 1)
            {
                Debug.Log($"[OV Gurney Sprint] expected one holder, actual={table.ActiveHolderCount}");
                ReleaseClient();
                yield break;
            }

            Vector3 bodyStart = table.transform.position;
            Vector3 motorStart = motor.transform.position;
            Vector3 cameraStart = player.ViewCamera.transform.position;
            Vector3 away = Vector3.ProjectOnPlane(motorStart - bodyStart, Vector3.up).normalized;
            Vector3 aimRight = Vector3.Cross(Vector3.up, aimDirection).normalized;
            float maxError = 0f;
            float releaseAt = -1f;
            const float sprintSpeed = 8.229375f; // Current movement baseline from TASK-000001.
            const float sprintDuration = 1.5f;
            float started = Time.unscaledTime;
            Debug.Log($"[OV Gurney Sprint] acquired axis={(longitudinal ? "Z" : "X")}, " +
                $"body={bodyStart}, motor={motorStart}, " +
                $"holdDistance={clientHoldDistance:F3}, holdHeight={clientHoldHeight:F3}");
            while (IsClientStarted && Time.unscaledTime - started < sprintDuration)
            {
                float elapsed = Mathf.Min(sprintDuration, Time.unscaledTime - started);
                if (clientHeld == null)
                {
                    releaseAt = elapsed;
                    break;
                }
                Vector3 displacement = away * (elapsed * sprintSpeed);
                motor.SetPosition(motorStart + displacement);
                smokeTarget = GroundPlaneTarget(cameraStart + displacement, aimDirection,
                    aimRight, clientHoldDistance, clientHoldHeight);
                float error = Vector3.Distance(smokeTarget,
                    table.transform.TransformPoint(localGrabPoint));
                maxError = Mathf.Max(maxError, error);
                yield return null;
            }

            motor.BaseVelocity = Vector3.zero;
            Vector3 bodyDisplacement = table.transform.position - bodyStart;
            Debug.Log($"[OV Gurney Sprint] result axis={(longitudinal ? "Z" : "X")}, " +
                $"held={clientHeld != null}, " +
                $"releasedAt={releaseAt:F2}s, maxGrabError={maxError:F3}m, " +
                $"tableDisplacement={bodyDisplacement}, distance={bodyDisplacement.magnitude:F3}m, " +
                $"motorDisplacement={Vector3.Distance(motor.transform.position, motorStart):F3}m");
            ReleaseClient();
        }

        private IEnumerator CoopFeelProbe(bool opposed)
        {
            if (OwnerId > 1) yield break;
            yield return new WaitForSecondsRealtime(OwnerId == 0 ? 3f : 4f);
            float attemptsEnd = Time.unscaledTime + 5f;
            while (IsClientStarted && clientHeld == null && Time.unscaledTime < attemptsEnd)
            {
                if (!pending)
                {
                    NetworkPhysicsBody table = null;
                    foreach (var candidate in FindObjectsByType<NetworkPhysicsBody>(FindObjectsSortMode.None))
                        if (candidate.NetworkObject.IsSpawned && candidate.name.StartsWith("NetworkTableAstra"))
                        {
                            table = candidate;
                            break;
                        }
                    if (table != null)
                    {
                        var input = GetComponent<OnlyVolunteers.Player.KccFirstPersonInput>();
                        input.Character.Motor.SetPosition(table.transform.position +
                            new Vector3(OwnerId == 0 ? 1.25f : -1.25f,
                                -table.transform.position.y + 0.02f, 0f));
                        yield return new WaitForSecondsRealtime(0.5f);
                        var camera = player.ViewCamera.transform;
                        var aim = table.transform.position + Vector3.up * 0.7f;
                        var ray = new Ray(camera.position, (aim - camera.position).normalized);
                        if (Physics.Raycast(ray, out RaycastHit hit, profile.AcquireDistance,
                            profile.AcquisitionLayers, QueryTriggerInteraction.Ignore) &&
                            hit.rigidbody == table.Body)
                        {
                            smokeHolding = true;
                            smokeTarget = hit.point;
                            Debug.Log($"[OV Feel] request owner={OwnerId}, hit={hit.point}, body={table.transform.position}");
                            TryGrabRay(ray);
                        }
                    }
                }
                yield return new WaitForSecondsRealtime(0.5f);
            }
            Debug.Log($"[OV Feel] result owner={OwnerId}, held={clientHeld != null}");
            if (clientHeld == null) { smokeHolding = false; yield break; }
            yield return new WaitForSecondsRealtime(2f);
            Vector3 startTarget = smokeTarget;
            Vector3 direction = opposed && OwnerId == 1 ? Vector3.back : Vector3.forward;
            float targetSpeed = opposed ? 0.6f : 1.2f;
            float moveStart = Time.unscaledTime;
            while (IsClientStarted && clientHeld != null && Time.unscaledTime - moveStart < 4f)
            {
                smokeTarget = startTarget + direction *
                    (Mathf.Min(4f, Time.unscaledTime - moveStart) * targetSpeed);
                yield return null;
            }
            Debug.Log($"[OV Feel] move done owner={OwnerId}, held={clientHeld != null}, target={smokeTarget}");
            if (clientHeld != null && targetSequence > 2)
            {
                ServerHoldTarget(clientHoldId, 1, startTarget, Channel.Unreliable);
                Debug.Log($"[OV Feel] stale target sent owner={OwnerId}, sequence=1");
            }
            yield return new WaitForSecondsRealtime(0.5f);
            ReleaseClient();
            Debug.Log($"[OV Feel] release owner={OwnerId}");
        }

        private IEnumerator CoopGrabProbe()
        {
            if (OwnerId > 1) yield break;
            float started = Time.unscaledTime;
            float firstAttempt = started + (OwnerId == 0 ? 5f : 7f);
            float releaseAt = started + (OwnerId == 0 ? 17f : 12f);
            while (Time.unscaledTime < firstAttempt)
                yield return null;

            // Retry a missed ray or late spawn for a short window across process startup skew.
            while (IsClientStarted && Time.unscaledTime < releaseAt - 1f && clientHeld == null)
            {
                if (!pending)
                {
                    Debug.Log($"[OV Coop] request owner={OwnerId}, elapsed={Time.unscaledTime - started:F1}");
                    yield return ProbeAttempt();
                }
                yield return new WaitForSecondsRealtime(0.5f);
            }
            Debug.Log($"[OV Coop] result owner={OwnerId}, held={clientHeld != null}, elapsed={Time.unscaledTime - started:F1}");
            while (IsClientStarted && Time.unscaledTime < releaseAt)
                yield return null;
            if (!IsClientStarted) yield break;
            Debug.Log($"[OV Coop] release owner={OwnerId}, held={clientHeld != null}, elapsed={Time.unscaledTime - started:F1}");
            ReleaseClient();
        }

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
