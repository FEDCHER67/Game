using System.Collections.Generic;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using OnlyVolunteers.Player.Physics;
using UnityEngine;

namespace OnlyVolunteers.Player.Hands
{
    /// <summary>Where one hand should be (world grip point = the palm centre).</summary>
    public struct HandGoalV01
    {
        public bool Active;
        public Vector3 Grip;
    }

    /// <summary>What the local player's hands should do this frame, read from the game's own holding systems.</summary>
    public struct ArmsIntentV01
    {
        public HandGoalV01 Right, Left;
        public ArmsPoseV01 Pose;
        public float Heft;
        public bool TwoHanded;
        /// <summary>Which system the hold came from (debug, screenshots, the playtest list).</summary>
        public string Source;

        public bool Any => Right.Active || Left.Active;
        public HandGoalV01 this[int side] => side == 0 ? Right : Left;

        public static ArmsIntentV01 Idle => new ArmsIntentV01 { Pose = ArmsPoseV01.Idle, Source = "idle" };
    }

    /// <summary>
    /// PLAYER HANDS v01: reads, never writes, what the local player holds, in priority order:
    /// 1. the map's PhysicsGrabber (LMB drag: an NPC body = both fists on the held point; a big prop such as a crate or a
    ///    cooler = both hands on its sides; a small one = the right fist on the grab point),
    /// 2. the operation's NetworkGrabber (the gurney = both hands on the bar; the patient, operation items),
    /// 3. the body bag carried with E (CaptureCorpseHands: both arms under it),
    /// 4. the physical inventory item (an organ or a blood bag on the right palm; a body bag in both arms),
    /// 5. the field kit's first-person tool (syringes, zip ties: right fist on the model),
    /// 6. the van paint brush / can held in the view (right / left).
    /// Reach distances, hold points, physics and authority stay exactly as those systems have them.
    /// </summary>
    public sealed class PlayerArmsIntentV01
    {
        public const string FieldKitViewModel = "[Capture] Field kit view model";
        public const string PaintBrushHand = "G20 Held brush", PaintCanHand = "G20 Held can";
        /// <summary>A prop is held with both hands from this bounds diagonal up (m).</summary>
        public const float TwoHandSize = 0.55f;
        /// <summary>From the NPC body's axis (the held point) out to where the fists close on it (m).</summary>
        public const float NpcSurface = 0.11f;
        /// <summary>Hands never spread wider than this from the middle of a held object (m).</summary>
        public const float MaxHalfSpan = 0.32f;

        private readonly PhysicsGrabber grabber;
        private readonly NetworkGrabber networkGrabber;
        private readonly NetworkInventory inventory;
        private readonly Dictionary<Rigidbody, Collider[]> colliders = new Dictionary<Rigidbody, Collider[]>();
        private Transform cameraSeen, kitModel, brushHand, canHand;
        private float nextFind;

        public PlayerArmsIntentV01(NetworkPlayer owner)
        {
            if (owner == null) return;
            grabber = owner.GetComponent<PhysicsGrabber>();
            networkGrabber = owner.GetComponent<NetworkGrabber>();
            inventory = owner.GetComponent<NetworkInventory>();
        }

        public ArmsIntentV01 Read(Camera camera)
        {
            if (camera == null) return ArmsIntentV01.Idle;
            Transform view = camera.transform;
            Vector3 right = Flat(view.right);
            Vector3 up = Vector3.up;

            // 1. the map's LMB drag
            if (grabber != null && grabber.isActiveAndEnabled && grabber.IsHolding && grabber.GrabbedBody != null)
            {
                Rigidbody body = grabber.GrabbedBody;
                Vector3 point = grabber.HeldWorldPoint;
                if (grabber.IsPointHold)
                {
                    // The held point is on the body's axis: the fists close on its near side, not inside the torso.
                    bool ragdoll = body.TryGetComponent<IGrabPointBodyGroup>(out _);
                    Vector3 toward = view.position - point;
                    Vector3 near = point + (toward.sqrMagnitude > 1e-4f ? toward.normalized * NpcSurface : Vector3.zero);
                    return Around(near, right, 0.11f, ArmsPoseV01.Grab, ragdoll ? 1f : 0.85f, "npc");
                }
                return Prop(body, point, right, "prop");
            }

            // 2. the operation's NetworkGrabber (gurney, patient, operation items)
            if (networkGrabber != null && networkGrabber.ClientHeld != null)
            {
                var held = networkGrabber.ClientHeld;
                Vector3 point = networkGrabber.ClientHeldPoint;
                var networkBody = held.GetComponent<NetworkPhysicsBody>();
                if (networkBody != null && networkBody.GroundPlaneFollow)
                    return Around(point, right, 0.24f, ArmsPoseV01.Push, 0.45f, "gurney");
                if (networkBody != null && networkBody.Body != null) return Prop(networkBody.Body, point, right, "network body");
                return One(point, ArmsPoseV01.Grab, 0.2f, "network object");
            }

            // 3. the body bag in the arms (E)
            var director = CaptureDirector.Instance;
            var hands = director != null && director.Disposal != null ? director.Disposal.Hands : null;
            if (hands != null && hands.Carrying != null)
                return Around(hands.HandPoint - up * 0.12f, right, 0.26f, ArmsPoseV01.Carry, 1f, "body bag");

            // 4. the physical inventory item (organ, blood bag, body bag)
            WorldItem item = inventory != null ? inventory.PhysicalItem : null;
            if (item != null)
            {
                Vector3 at = item.transform.position;
                if (item.TryGetComponent<CaptureBodyBag>(out _))
                    return Around(at - up * 0.12f, right, 0.26f, ArmsPoseV01.Carry, 1f, "bag item");
                return One(at - up * 0.035f, ArmsPoseV01.PalmUp, 0.15f, "item");
            }

            // 5./6. tools shown in the view (field kit; van paint brush and can)
            if (cameraSeen != view || Time.unscaledTime >= nextFind)
            {
                cameraSeen = view;
                nextFind = Time.unscaledTime + 1f;
                kitModel = view.Find(FieldKitViewModel);
                brushHand = view.Find(PaintBrushHand);
                canHand = view.Find(PaintCanHand);
            }
            var intent = ArmsIntentV01.Idle;
            if (kitModel != null && kitModel.gameObject.activeInHierarchy)
            {
                intent.Right = new HandGoalV01 { Active = true, Grip = kitModel.TransformPoint(new Vector3(0f, -0.012f, -0.035f)) };
                intent.Pose = ArmsPoseV01.Tool; intent.Heft = 0.05f; intent.Source = "field kit";
            }
            else if (brushHand != null && brushHand.childCount > 0 && brushHand.gameObject.activeInHierarchy)
            {
                intent.Right = new HandGoalV01 { Active = true, Grip = brushHand.position };
                intent.Pose = ArmsPoseV01.Tool; intent.Heft = 0.05f; intent.Source = "paint";
            }
            if (canHand != null && canHand.childCount > 0 && canHand.gameObject.activeInHierarchy)
            {
                intent.Left = new HandGoalV01 { Active = true, Grip = canHand.position + Vector3.down * 0.03f };
                intent.Pose = ArmsPoseV01.Tool; intent.Heft = Mathf.Max(intent.Heft, 0.1f); intent.Source = "paint";
            }
            return intent;
        }

        private static ArmsIntentV01 Around(Vector3 middle, Vector3 right, float half, ArmsPoseV01 pose, float heft, string source) =>
            new ArmsIntentV01
            {
                Right = new HandGoalV01 { Active = true, Grip = middle + right * half },
                Left = new HandGoalV01 { Active = true, Grip = middle - right * half },
                Pose = pose, Heft = Mathf.Clamp01(heft), TwoHanded = true, Source = source,
            };

        private static ArmsIntentV01 One(Vector3 grip, ArmsPoseV01 pose, float heft, string source) =>
            new ArmsIntentV01
            {
                Right = new HandGoalV01 { Active = true, Grip = grip },
                Pose = pose, Heft = Mathf.Clamp01(heft), Source = source,
            };

        /// <summary>A plain rigidbody: big (a crate, a cooler, a fridge) = both hands on its sides at the grab height,
        /// small = the right fist on the grab point. Heft from its mass.</summary>
        private ArmsIntentV01 Prop(Rigidbody body, Vector3 point, Vector3 right, string source)
        {
            if (!TryBounds(body, out Bounds bounds)) return One(point, ArmsPoseV01.Grab, Mathf.Clamp01(body.mass / 15f) * 0.6f, source);
            float heft = Mathf.Clamp01(body.mass / 30f);
            Vector3 e = bounds.extents;
            float halfSpan = Mathf.Abs(right.x) * e.x + Mathf.Abs(right.z) * e.z;
            if (bounds.size.magnitude < TwoHandSize || halfSpan < 0.1f)
                return One(point, ArmsPoseV01.Grab, heft * 0.6f, source);
            Vector3 middle = bounds.center;
            middle.y = Mathf.Lerp(bounds.center.y, point.y, 0.5f);
            return Around(middle, right, Mathf.Min(halfSpan + 0.02f, MaxHalfSpan), ArmsPoseV01.Grab, Mathf.Max(0.25f, heft),
                source + " (two hands)");
        }

        private bool TryBounds(Rigidbody body, out Bounds bounds)
        {
            bounds = default;
            if (!colliders.TryGetValue(body, out var list) || list == null)
            {
                if (colliders.Count > 64) colliders.Clear();
                colliders[body] = list = body.GetComponentsInChildren<Collider>(true);
            }
            bool any = false;
            foreach (var c in list)
            {
                if (c == null || !c.enabled || c.isTrigger || c.attachedRigidbody != body) continue;
                if (!any) { bounds = c.bounds; any = true; }
                else bounds.Encapsulate(c.bounds);
            }
            return any;
        }

        private static Vector3 Flat(Vector3 v)
        {
            v.y = 0f;
            return v.sqrMagnitude > 1e-6f ? v.normalized : Vector3.right;
        }
    }
}
