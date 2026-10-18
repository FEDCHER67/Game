using System.Collections.Generic;
using KinematicCharacterController;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Network;
using OnlyVolunteers.Operation.Stage1;
using OnlyVolunteers.Police;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Player.Physics
{
    /// <summary>What may move the player character (Fedya, 2026-10-18, after the operations v04 playtest: "you can stand
    /// on the held liver, pull up and fly"; "the patient's ragdoll pushes the player").
    ///
    /// RULE: no held, carried or loose physics object moves the player: items, organs, tools, the patient's or an NPC's
    /// ragdoll or capsule, props. Only the ALLOW-LIST below may push the player, stand him up on itself or carry him:
    ///   1. vehicles: the van (VanController, layer Vehicle, its doors and interior), police cars (PoliceCarMotor);
    ///   2. other characters (a KinematicCharacterMotor capsule: teammates);
    ///   3. anything registered at runtime with RegisterMover (later: a knocked-out / ragdolled teammate).
    /// Everything else, per collider the KCC motor probes (ExampleCharacterController.ColliderPolicy, used for its sweeps,
    /// its ground probing and its overlap depenetration alike):
    ///   - items (inventory / organ / blood items, operation tools): never solid for the player;
    ///   - anything held (a NetworkPhysicsBody with a holder, an operation item in a hand) and for HeldGrace seconds after
    ///     it was last seen held: never solid;
    ///   - bodies (NPC ragdoll bones and capsules, the patient): never solid for the player's motor; he wades through
    ///     them (PhysX still lets his kinematic capsule nudge the limbs aside) and never stands on them;
    ///   - query-only interaction targets (operation table strap bands/buckles): never solid;
    ///   - the operating gurney (OperationTableBrake): always solid, held or moving; it never moves into the player;
    ///   - other props: solid only while they lie still (slower than RestSpeed) or are kinematic (a frozen gurney); a
    ///     moving one passes through the player instead of shoving him.
    /// Physics between those objects and the world, the van and each other is untouched (this only filters the player's
    /// motor). The motor's tuning is unchanged. The offline map grab (PhysicsGrabber) additionally keeps its own
    /// per-hold KCC ignore list; the networked grab (NetworkGrabber / NetworkPhysicsBody) is covered by the held rule.</summary>
    public static class PlayerPushPolicy
    {
        public const float RestSpeed = 0.3f;
        public const float RestSpin = 1.5f;
        public const float HeldGrace = 0.75f;
        private const int CacheLimit = 4096;

        private enum Kind : byte { Mover, Item, Body, Prop }

        private sealed class Info
        {
            public Kind Kind;
            public NetworkPhysicsBody Network;
            public OperationPhysicalItem OperationItem;
            public float HeldUntil = -1f;
        }

        private static readonly Dictionary<Rigidbody, Info> Cache = new Dictionary<Rigidbody, Info>();
        private static readonly HashSet<Rigidbody> ExtraMovers = new HashSet<Rigidbody>();
        private static int vehicleLayer = -2;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void Install()
        {
            Cache.Clear();
            ExtraMovers.Clear();
            vehicleLayer = -2;
            ExampleCharacterController.ColliderPolicy = Allows;
        }

        /// <summary>Allow-list entry 3: a body that may push the player (e.g. a knocked-out teammate's ragdoll later).</summary>
        public static void RegisterMover(Rigidbody body)
        {
            if (body == null) return;
            ExtraMovers.Add(body);
            Cache.Remove(body);
        }

        public static void UnregisterMover(Rigidbody body)
        {
            if (body == null) return;
            ExtraMovers.Remove(body);
            Cache.Remove(body);
        }

        public static bool IsAllowListedMover(Rigidbody body) => body != null && Get(body).Kind == Kind.Mover;

        /// <summary>Whether the player's motor may treat this collider as solid (block, ground, push).</summary>
        public static bool Allows(Collider collider)
        {
            if (collider == null) return true;
            // Query-only interaction targets (the table's strap bands/buckles): raycast targets, never solid. An open strap
            // swings out over the table edge and must not shove the player standing there (review G35 M3).
            if (collider.TryGetComponent(out OperationTargetTag tag) && tag.kind == TargetKind.Strap) return false;
            Rigidbody body = collider.attachedRigidbody;
            if (body == null) return true;
            // The operating gurney is always solid, held or moving (Fedya, round 2: "with LMB he walks through it"). It never
            // pushes the player: its walking push and its brake never move it into a touching player (OperationTableBrake).
            if (body.TryGetComponent(out OperationTableBrake _)) return true;
            Info info = Get(body);
            if (info.Kind == Kind.Mover) return true;
            float now = Time.time;
            if (Held(info))
            {
                info.HeldUntil = now + HeldGrace;
                return false;
            }
            if (now < info.HeldUntil || info.Kind == Kind.Item || info.Kind == Kind.Body) return false;
            if (body.isKinematic) return true;
            return body.linearVelocity.sqrMagnitude < RestSpeed * RestSpeed && body.angularVelocity.sqrMagnitude < RestSpin * RestSpin;
        }

        private static bool Held(Info info) =>
            (info.Network != null && info.Network.HasHolder) ||
            (info.OperationItem != null && info.OperationItem.Holder != null);

        private static Info Get(Rigidbody body)
        {
            if (Cache.TryGetValue(body, out Info info)) return info;
            if (Cache.Count > CacheLimit) Cache.Clear();
            info = new Info
            {
                Kind = Classify(body),
                Network = body.GetComponentInParent<NetworkPhysicsBody>(),
                OperationItem = body.GetComponentInParent<OperationPhysicalItem>(),
            };
            Cache[body] = info;
            return info;
        }

        private static Kind Classify(Rigidbody body)
        {
            if (ExtraMovers.Contains(body)) return Kind.Mover;
            if (vehicleLayer == -2) vehicleLayer = LayerMask.NameToLayer("Vehicle");
            if (body.GetComponent<KinematicCharacterMotor>() != null) return Kind.Mover;
            if (vehicleLayer >= 0 && body.gameObject.layer == vehicleLayer) return Kind.Mover;
            if (body.GetComponentInParent<VanController>() != null || body.GetComponentInParent<PoliceCarMotor>() != null) return Kind.Mover;
            if (body.GetComponentInParent<WorldItem>() != null || body.GetComponentInParent<OfflineWorldItem>() != null ||
                body.GetComponentInParent<OperationTool>() != null || body.GetComponentInParent<OperationPhysicalItem>() != null)
                return Kind.Item;
            if (body.GetComponent<NpcRagdollPart>() != null || body.GetComponentInParent<GreyboxNpcBody>() != null ||
                body.GetComponentInParent<NpcRagdoll>() != null || body.GetComponentInParent<OperationPatientRagdoll>() != null)
                return Kind.Body;
            return Kind.Prop;
        }
    }
}
