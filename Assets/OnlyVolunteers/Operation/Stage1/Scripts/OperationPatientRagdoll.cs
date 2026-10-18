using System;
using System.Collections.Generic;
using FishNet.Object;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Network;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Operation-only adapter for the existing 11-body NPC ragdoll (NpcRagdoll + Buddy_RagdollProfile, unchanged).
    /// The patient's normal NetworkPhysicsBody stays the grab handle; a free-rotation joint couples it to the bone nearest
    /// the hand. Only the server simulates the bones. Clients receive the bone poses relative to the patient root (which
    /// its NetworkTransform moves), only when they change, plus the last pose for late joiners, and show them on kinematic
    /// copies. When the table takes the patient (release over the pad, F9), the ragdoll hands the body back to the
    /// Animator: the root is re-seated under the ragdoll's hips, already turned like the table pose, and the NPC wake
    /// blend morphs the limbs into the table clip while the table slides him into PatientRest.</summary>
    [DefaultExecutionOrder(200)]
    [RequireComponent(typeof(NetworkPhysicsBody), typeof(NpcRagdoll))]
    public sealed class OperationPatientRagdoll : NetworkBehaviour
    {
        private const float PoseInterval = 0.05f, PoseHeartbeat = 1f, PoseMoveEpsilon = 0.002f, PoseTurnEpsilon = 0.6f;
        private NetworkPhysicsBody handle;
        private OperationPatientRig rig;
        private NpcRagdoll ragdoll;
        private ConfigurableJoint handleJoint;
        private bool tableState, observedActive, observedHeld, wasHeld;
        private float originalMass, nextPose, lastSent;
        private Vector3[] targetPositions, sentPositions;
        private Quaternion[] targetRotations, sentRotations;
        private Collider[] players = Array.Empty<Collider>();
        private bool ignoredPlayers;
        public bool Active => ragdoll != null && ragdoll.Active;
        public int DynamicBodies
        {
            get
            {
                int count = 0;
                if (Active) for (int i = 0; i < ragdoll.PartCount; i++) if (!ragdoll.BodyOf(i).isKinematic) count++;
                return count;
            }
        }
        public Transform Bone(int index) => ragdoll.BoneOf(index);
        public int BoneCount => ragdoll != null ? ragdoll.PartCount : 0;
        public Vector3 PlacementPoint => Active ? ragdoll.CenterOfMass : transform.position + Vector3.up * 0.1f;
        public float PoseReceivedAt { get; private set; }
        public int PosesSent { get; private set; }
        /// <summary>The NPC wake blend (ragdoll pose -> animation) is still running after a hand-back.</summary>
        public bool Blending => ragdoll != null && ragdoll.Blending;

        private void Awake()
        {
            handle = GetComponent<NetworkPhysicsBody>(); rig = GetComponent<OperationPatientRig>();
            ragdoll = GetComponent<NpcRagdoll>(); ragdoll.enabled = false;
        }

        public override void OnStartServer()
        {
            base.OnStartServer();
            originalMass = handle.Body.mass;
        }

        /// <summary>Called by the table at the same transition that makes its existing root kinematic.</summary>
        public void ServerTableState(bool onTable)
        {
            if (!IsServerInitialized) return;
            tableState = onTable;
            if (onTable && Active)
            {
                StopRagdoll(true, true);
                SendPose(false);
            }
        }

        private void StartRagdoll(bool server)
        {
            if (Active) return;
            if (!ragdoll.Ready)
            {
                Debug.LogError("[OPS RAGDOLL] " + ragdoll.Problem, this); return;
            }
            rig.SetPhysicsCollider(false);
            ragdoll.enabled = server;
            ragdoll.Activate(server ? handle.Body.linearVelocity : Vector3.zero, Vector3.zero);
            if (!Active) return;
            float total = 0f;
            for (int i = 0; i < ragdoll.PartCount; i++) total += ragdoll.BodyOf(i).mass;
            float mass = Mathf.Max(1f, originalMass > 0f ? originalMass : handle.Body.mass);
            // Preserve the approved 12 kg grab load: half on the existing handle, half over the profiled bones.
            // The root's rotational constraints never constrain the skeleton's rotation.
            if (server) handle.Body.mass = mass * 0.5f;
            for (int i = 0; i < ragdoll.PartCount; i++)
            {
                var body = ragdoll.BodyOf(i);
                body.mass *= mass * 0.5f / total;
                body.isKinematic = !server;
                body.useGravity = server;
                // Root and bone colliders do not collide with one another (the root has no active shape).
                if (!server) body.interpolation = RigidbodyInterpolation.None;
            }
            if (server) LinkHandle();
            Debug.Log("[OPS RAGDOLL] active server=" + server + " bodies=" + ragdoll.PartCount);
        }

        private void LinkHandle()
        {
            if (handleJoint != null) DestroyImmediate(handleJoint);
            Vector3 point = handle.GrabPoint;
            var bone = ragdoll.BodyOf(ragdoll.NearestPart(point));
            handleJoint = bone.gameObject.AddComponent<ConfigurableJoint>();
            handleJoint.autoConfigureConnectedAnchor = false;
            handleJoint.connectedBody = handle.Body;
            handleJoint.anchor = bone.transform.InverseTransformPoint(point);
            handleJoint.connectedAnchor = handle.transform.InverseTransformPoint(point);
            handleJoint.xMotion = handleJoint.yMotion = handleJoint.zMotion = ConfigurableJointMotion.Locked;
            handleJoint.angularXMotion = handleJoint.angularYMotion = handleJoint.angularZMotion = ConfigurableJointMotion.Free;
            handleJoint.projectionMode = JointProjectionMode.PositionAndRotation;
            handleJoint.projectionDistance = 0.04f; handleJoint.enableCollision = false;
        }

        private void StopRagdoll(bool onTable, bool reseat)
        {
            IgnorePlayers(false);
            if (handleJoint != null) DestroyImmediate(handleJoint);
            handleJoint = null;
            Transform hips = ragdoll.Hips;
            Vector3 lyingHips = hips != null ? hips.position : transform.position;
            // Deactivate keeps the lying pose as a snapshot and blends from it into the animation over the next
            // ~0.35-0.5 s (the existing NPC wake blend); the component stays enabled only for that blend.
            if (Active) ragdoll.Deactivate();
            ragdoll.enabled = true;
            if (IsServerInitialized && originalMass > 0f) handle.Body.mass = originalMass;
            rig.Animator.enabled = true;
            if (reseat && onTable)
            {
                // Turned like the table pose, the root goes under where the body actually lies, so the hand-back is a
                // smooth morph and slide instead of a jump to the handle.
                var table = FindTable();
                if (table != null) transform.rotation = table.RestPose.rotation;
            }
            rig.SnapState(onTable ? OperationPatientRig.StateTableAwake : OperationPatientRig.StateKnockedOut);
            if (reseat && onTable && hips != null)
            {
                Vector3 seat = transform.position + (lyingHips - hips.position);
                transform.position = seat;
                if (handle.Body != null) { handle.Body.position = seat; handle.Body.rotation = transform.rotation; }
            }
            rig.SetPhysicsCollider(!onTable);
        }

        private NetworkOperationTable FindTable()
        {
            foreach (var t in FindObjectsByType<NetworkOperationTable>())
                if (t.PatientObject != null && t.PatientObject == NetworkObject) return t;
            return null;
        }

        private void FixedUpdate()
        {
            if (!IsServerInitialized || handle == null || handle.Body == null) return;
            if (!tableState && handle.HasHolder && !Active) StartRagdoll(true);
            if (!Active) return;
            bool held = handle.HasHolder;
            if (held && !wasHeld) LinkHandle();
            // Held: the handle carries half of the approved load. Let go: it rides along weightless on its joint, so
            // it never drags the resting body into the floor (a collider-less 6 kg handle made the ragdoll jitter).
            float want = held ? Mathf.Max(1f, originalMass) * 0.5f : 0.05f;
            if (!Mathf.Approximately(handle.Body.mass, want)) { handle.Body.mass = want; handle.Body.useGravity = held; }
            wasHeld = held;
            IgnorePlayers(held);
            if (Time.time >= nextPose) { nextPose = Time.time + PoseInterval; SendPose(true); }
        }

        private void LateUpdate()
        {
            // The NPC wake blend has finished: the NPC's own per-frame tracking is not needed on the patient.
            if (!Active && ragdoll != null && ragdoll.enabled && !ragdoll.Blending) ragdoll.enabled = false;
            if (!IsServerInitialized && observedActive) ApplyRemote(1f - Mathf.Exp(-30f * Time.deltaTime));
        }

        private void IgnorePlayers(bool ignore)
        {
            if (ignore == ignoredPlayers) return;
            ignoredPlayers = ignore;
            if (ignore)
            {
                var list = new List<Collider>();
                foreach (var player in FindObjectsByType<NetworkPlayer>()) list.AddRange(player.GetComponentsInChildren<Collider>());
                players = list.ToArray();
            }
            foreach (var own in ragdoll.Colliders)
                foreach (var player in players) if (own != null && player != null) Physics.IgnoreCollision(own, player, ignore);
        }

        /// <summary>Root-relative bone poses; skipped while nothing moved (a body at rest costs a heartbeat a second).</summary>
        private void SendPose(bool active)
        {
            int count = active ? ragdoll.PartCount : 0;
            var positions = new Vector3[count]; var rotations = new Quaternion[count];
            bool moved = !active || sentPositions == null || sentPositions.Length != count || Time.time - lastSent >= PoseHeartbeat;
            Quaternion inverse = Quaternion.Inverse(transform.rotation);
            for (int i = 0; i < count; i++)
            {
                var bone = ragdoll.BoneOf(i);
                positions[i] = transform.InverseTransformPoint(bone.position); rotations[i] = inverse * bone.rotation;
                if (!moved && ((positions[i] - sentPositions[i]).sqrMagnitude > PoseMoveEpsilon * PoseMoveEpsilon ||
                    Quaternion.Angle(rotations[i], sentRotations[i]) > PoseTurnEpsilon)) moved = true;
            }
            if (!moved) return;
            sentPositions = positions; sentRotations = rotations; lastSent = Time.time; PosesSent++;
            ObserversPose(active, tableState, handle.HasHolder, positions, rotations);
        }

        [ObserversRpc(BufferLast = true, ExcludeServer = true)]
        private void ObserversPose(bool active, bool onTable, bool held, Vector3[] positions, Quaternion[] rotations)
        {
            if (IsServerInitialized) return;
            if (active)
            {
                // Ready resolves the rig and its profile first (PartCount is 0 until then on a client).
                if (!ragdoll.Ready || positions == null || rotations == null || positions.Length != ragdoll.PartCount ||
                    rotations.Length != positions.Length) return;
                bool first = !observedActive;
                StartRagdoll(false);
                targetPositions = positions; targetRotations = rotations;
                if (first) ApplyRemote(1f);
                // Mirror the server: a carried body passes through players, a lying one is an obstacle.
                if (held != observedHeld) IgnorePlayers(held);
                observedHeld = held;
            }
            else if (observedActive) { StopRagdoll(onTable, false); observedHeld = false; }
            observedActive = active; PoseReceivedAt = Time.time;
        }

        private void ApplyRemote(float blend)
        {
            if (!Active || targetPositions == null) return;
            Quaternion root = transform.rotation;
            for (int i = 0; i < targetPositions.Length; i++)
            {
                var bone = ragdoll.BoneOf(i);
                Vector3 local = Vector3.Lerp(transform.InverseTransformPoint(bone.position), targetPositions[i], blend);
                Quaternion turn = Quaternion.Slerp(Quaternion.Inverse(root) * bone.rotation, targetRotations[i], blend);
                bone.SetPositionAndRotation(transform.TransformPoint(local), root * turn);
            }
        }
    }
}
