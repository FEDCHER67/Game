using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Builds what a dropped item looks like and collides with: its world model (or a grey box when it has none),
    /// fitted to ItemDefinition.WorldModelSize, plus one collider sized to the model. Shared by offline drops
    /// (OfflineWorldItem, with a Rigidbody) and networked ones (WorldItem, trigger only, no physics).
    /// </summary>
    public static class ItemWorldModel
    {
        public const string ChildName = "WorldModel";
        private const float FallbackSize = 0.3f;

        private static readonly Dictionary<ItemDefinition, PhysicsMaterial> Materials = new();

        /// <summary>
        /// Adds a "WorldModel" child to <paramref name="root"/> with the model and its collider; returns the scaled model.
        /// groundAligned puts the model's bottom at the root pivot (for items placed on the floor), otherwise its centre.
        /// </summary>
        public static Transform Build(ItemDefinition item, Transform root, bool groundAligned, bool trigger)
        {
            var holder = new GameObject(ChildName).transform;
            holder.SetParent(root, false);

            GameObject model = item != null && item.WorldModel != null
                ? Object.Instantiate(item.WorldModel, holder, false)
                : GameObject.CreatePrimitive(PrimitiveType.Cube);
            model.name = item != null && item.WorldModel != null ? item.WorldModel.name : "FallbackBox";
            model.transform.SetParent(holder, false);
            model.transform.localPosition = Vector3.zero;
            // Models carry no colliders of their own here: one fitted collider below is enough and stays predictable.
            foreach (Collider c in model.GetComponentsInChildren<Collider>(true))
            {
                c.enabled = false;
                if (Application.isPlaying) Object.Destroy(c);
                else Object.DestroyImmediate(c);
            }

            // Renderer.bounds is a world AABB: measure with the root unrotated, or a yawed drop (networked ones face
            // the dropper) grows the box and shrinks the fitted model by up to ~30%.
            Quaternion rootRotation = root.rotation;
            root.rotation = Quaternion.identity;
            Bounds local = LocalBounds(model.transform, holder);
            root.rotation = rootRotation;
            float largest = Mathf.Max(local.size.x, local.size.y, local.size.z);
            float target = item == null || item.WorldModel == null
                ? (item != null && item.WorldModelSize > 0f ? item.WorldModelSize : FallbackSize)
                : item.WorldModelSize;
            if (target > 0f && largest > 1e-4f)
            {
                float k = target / largest;
                model.transform.localScale *= k;
                local = new Bounds(local.center * k, local.size * k);
            }
            if (local.size.sqrMagnitude < 1e-8f) local = new Bounds(Vector3.zero, Vector3.one * FallbackSize);

            Vector3 shift = -local.center + (groundAligned ? Vector3.up * local.extents.y : Vector3.zero);
            model.transform.localPosition += shift;
            local.center += shift;

            Collider collider = AddCollider(holder.gameObject, item != null ? item.ColliderShape : ItemColliderShape.Auto, local);
            collider.isTrigger = trigger;
            if (!trigger) collider.sharedMaterial = MaterialFor(item);
            return model.transform;
        }

        /// <summary>Makes an offline drop a light physics body: small mass, a bit of bounce, damped so it does not roll away.</summary>
        public static Rigidbody AddPhysics(GameObject root, ItemDefinition item, Transform model)
        {
            var body = root.AddComponent<Rigidbody>();
            body.mass = item != null ? item.DropMass : 0.4f;
            body.linearDamping = 0.2f;
            body.angularDamping = 1.5f;
            body.interpolation = RigidbodyInterpolation.Interpolate;
            body.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            float squish = item != null ? item.DropSquish : 0f;
            if (squish > 0f && model != null)
                root.AddComponent<SquishOnImpact>().Setup(model, squish);
            return body;
        }

        private static Collider AddCollider(GameObject holder, ItemColliderShape shape, Bounds b)
        {
            Vector3 s = b.size;
            int longAxis = s.x >= s.y && s.x >= s.z ? 0 : s.y >= s.z ? 1 : 2;
            float longest = s[longAxis];
            float middle = Mathf.Max(s[(longAxis + 1) % 3], s[(longAxis + 2) % 3]);
            if (shape == ItemColliderShape.Auto)
                shape = longest > 1.6f * middle ? ItemColliderShape.Capsule : ItemColliderShape.Box;

            switch (shape)
            {
                case ItemColliderShape.Sphere:
                    var sphere = holder.AddComponent<SphereCollider>();
                    sphere.center = b.center;
                    // Average of the sides: a full-size sphere would float a flat item above the ground.
                    sphere.radius = (s.x + s.y + s.z) / 6f;
                    return sphere;
                case ItemColliderShape.Capsule:
                    var capsule = holder.AddComponent<CapsuleCollider>();
                    capsule.center = b.center;
                    capsule.direction = longAxis;
                    capsule.radius = middle * 0.5f;
                    capsule.height = longest;
                    return capsule;
                default:
                    var box = holder.AddComponent<BoxCollider>();
                    box.center = b.center;
                    box.size = s;
                    return box;
            }
        }

        private static PhysicsMaterial MaterialFor(ItemDefinition item)
        {
            if (item != null && Materials.TryGetValue(item, out PhysicsMaterial cached) && cached != null) return cached;
            var material = new PhysicsMaterial(item != null ? $"Drop_{item.name}" : "Drop_Fallback")
            {
                // Soft wet things: grippy, so they stop instead of sliding; Maximum keeps the bounce on any floor.
                dynamicFriction = 0.8f,
                staticFriction = 0.9f,
                frictionCombine = PhysicsMaterialCombine.Maximum,
                bounciness = item != null ? item.DropBounciness : 0.3f,
                bounceCombine = PhysicsMaterialCombine.Maximum,
            };
            if (item != null) Materials[item] = material;
            return material;
        }

        private static Bounds LocalBounds(Transform model, Transform space)
        {
            bool any = false;
            var bounds = new Bounds();
            foreach (Renderer r in model.GetComponentsInChildren<Renderer>(true))
            {
                Bounds w = r.bounds;
                Vector3 min = w.min, max = w.max;
                for (int i = 0; i < 8; i++)
                {
                    var corner = new Vector3((i & 1) == 0 ? min.x : max.x, (i & 2) == 0 ? min.y : max.y, (i & 4) == 0 ? min.z : max.z);
                    Vector3 p = space.InverseTransformPoint(corner);
                    if (!any)
                    {
                        bounds = new Bounds(p, Vector3.zero);
                        any = true;
                    }
                    else bounds.Encapsulate(p);
                }
            }
            return bounds;
        }
    }
}
