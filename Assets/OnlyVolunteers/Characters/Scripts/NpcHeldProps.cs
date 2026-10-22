using System.Collections.Generic;
using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.Characters
{
    /// <summary>
    /// Things an NPC type carries in its hands (TASK-000277: only the stash courier, the drunk, the car flipper, the
    /// streamer and the vaper carry anything). The type FBX (ArtSource/Characters/SAUSAGE_BUDDY_01/Types) exports them as
    /// skinned meshes "Props_LeftHand" / "Props_RightHand", rigid on the hand bone. At the slightest danger the NPC drops
    /// them: each one becomes a loose physics object at its current pose and falls to the floor, the hand mesh is hidden.
    /// Danger = the GreyboxNpc of this NPC flees or is no longer free (stunned, held, in the cargo bay); anything else
    /// can call Drop() itself. Presentation only and local to each machine (a networked NPC would drop on the server).
    /// Types with crowd LODs (TASK-000900) also carry "Props_*Hand_LOD1/2": they are hidden on Drop, only LOD0 falls.
    /// </summary>
    public sealed class NpcHeldProps : MonoBehaviour
    {
        [SerializeField, Min(0.01f)] private float massPerProp = 0.4f;
        [Tooltip("Push away from the body when the props are dropped, m/s.")]
        [SerializeField, Min(0f)] private float toss = 0.8f;
        [Tooltip("Dropped props are removed after this many seconds (0 = they stay).")]
        [SerializeField, Min(0f)] private float despawnAfter = 60f;

        private SkinnedMeshRenderer[] held;
        private GreyboxNpc npc;
        private readonly List<GameObject> dropped = new List<GameObject>();

        public bool Dropped { get; private set; }
        public IReadOnlyList<GameObject> DroppedProps => dropped;

        private void Awake() => Collect();

        private void LateUpdate()
        {
            if (Dropped || npc == null || held == null || held.Length == 0)
                return;
            if (npc.Fleeing || npc.State != NpcState.Free)
                Drop();
        }

        /// <summary>Lets go of everything in the hands. Safe to call more than once.</summary>
        public void Drop()
        {
            if (Dropped)
                return;
            if (held == null)
                Collect();
            Dropped = true;
            foreach (SkinnedMeshRenderer smr in held)
            {
                if (smr == null || !smr.enabled || !smr.gameObject.activeInHierarchy)
                    continue;
                if (Level(smr.name) > 0)
                {
                    smr.enabled = false;                                         // a crowd LOD of a prop: hidden, the LOD0 one falls
                    continue;
                }
                // The current pose of the prop, in the renderer's space with its scale applied.
                var mesh = new Mesh { name = smr.name + "_Dropped" };
                smr.BakeMesh(mesh, true);
                var go = new GameObject(smr.name + "_Dropped");
                go.transform.SetPositionAndRotation(smr.transform.position, smr.transform.rotation);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterials = smr.sharedMaterials;
                go.AddComponent<BoxCollider>();                              // sized to the baked mesh
                var body = go.AddComponent<Rigidbody>();
                body.mass = massPerProp;
                body.interpolation = RigidbodyInterpolation.Interpolate;
                body.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
                Vector3 away = smr.bounds.center - transform.position;
                away.y = 0f;
                body.linearVelocity = (away.sqrMagnitude > 1e-6f ? away.normalized * toss : Vector3.zero) + Vector3.up * 0.5f;
                body.angularVelocity = Random.insideUnitSphere * 4f;
                smr.enabled = false;
                dropped.Add(go);
                if (despawnAfter > 0f && Application.isPlaying)
                    Destroy(go, despawnAfter);
            }
        }

        private void Collect()
        {
            var list = new List<SkinnedMeshRenderer>();
            foreach (SkinnedMeshRenderer smr in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                string part = smr.name;
                if (Level(part) >= 0 && part.Contains("_LOD"))
                    part = part.Substring(0, part.LastIndexOf("_LOD", System.StringComparison.Ordinal));
                if (part.StartsWith("Props_") && part.EndsWith("Hand"))
                    list.Add(smr);
            }
            held = list.ToArray();
            npc = GetComponentInParent<GreyboxNpc>();
            if (npc == null)
                npc = GetComponentInChildren<GreyboxNpc>();
        }

        // Crowd LODs of the types (TASK-000900): "Props_RightHand" / "Props_RightHand_LOD0" = 0, "Props_RightHand_LODn" = n,
        // -1 = a name without a level suffix that still ends in "_LOD" (kept as it is).
        private static int Level(string name)
        {
            int i = name.LastIndexOf("_LOD", System.StringComparison.Ordinal);
            if (i < 0) return 0;
            return int.TryParse(name.Substring(i + 4), out int lod) ? lod : -1;
        }
    }
}
