using System.Collections.Generic;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.Story
{
    /// <summary>
    /// A logical story-mission anchor (STORY_MISSIONS_SPEC v01 §17.2) placed by the scene-integration step
    /// (W85PlayIntegrator.PlaceWorkshopZoneInOpenScene): a named point with an optional box volume in this transform's
    /// frame (Size wide / long, from 1 m below to Size.y above the transform). Placeholder only: no collider, no material
    /// asset; corner posts and a floating title are built at runtime when ShowMarkers is on. Runtime systems find anchors
    /// by Id, never by scene path, so moving the workshop root later is one transform change.
    /// </summary>
    public sealed class StoryAnchor : MonoBehaviour
    {
        public const string WorkshopMechanic = "Workshop.Mechanic";
        public const string RivalHandIn = "M06.RivalHandIn";
        public const string RivalCanopy = "M06.RivalCanopy";
        public const string RivalOffShift = "M06.RivalOffShift";
        public const string C01ArrivalB02 = "C01.Arrival.hamlet_shed";

        public static readonly List<StoryAnchor> All = new List<StoryAnchor>();

        public string Id = "";
        public string Title = "";
        [Tooltip("Box volume (x wide, y high, z long). Zero size = a point anchor.")]
        public Vector3 Size = Vector3.zero;
        public bool ShowMarkers = true;
        public Color MarkerColor = new Color(0.35f, 0.8f, 1f);

        private bool markersBuilt;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => All.Clear();

        private void OnEnable() { if (!All.Contains(this)) All.Add(this); }
        private void OnDisable() => All.Remove(this);

        private void Start()
        {
            if (ShowMarkers && !markersBuilt) BuildMarkers();
        }

        public bool IsVolume => Size.x > 0.01f && Size.z > 0.01f;

        public bool Contains(Vector3 world)
        {
            if (!IsVolume) return false;
            Vector3 p = transform.InverseTransformPoint(world);
            return Mathf.Abs(p.x) <= Size.x * 0.5f && Mathf.Abs(p.z) <= Size.z * 0.5f && p.y >= -1f && p.y <= Size.y;
        }

        public static StoryAnchor Find(string id)
        {
            foreach (StoryAnchor a in All)
                if (a != null && a.isActiveAndEnabled && a.Id == id) return a;
            return null;
        }

        private void BuildMarkers()
        {
            markersBuilt = true;
            Transform old = transform.Find("Markers");
            if (old != null) Destroy(old.gameObject);
            var root = new GameObject("Markers").transform;
            root.SetParent(transform, false);
            var block = new MaterialPropertyBlock();
            block.SetColor("_BaseColor", MarkerColor);
            block.SetColor("_Color", MarkerColor);
            int mask = ~((1 << OvLayers.VehicleInterior) | (1 << OvLayers.Vehicle) | (1 << OvLayers.Player));
            int posts = IsVolume ? 4 : 1;
            for (int i = 0; i < posts; i++)
            {
                float x = IsVolume ? (i % 2 == 0 ? -0.5f : 0.5f) * Size.x : 0f, z = IsVolume ? (i < 2 ? -0.5f : 0.5f) * Size.z : 0f;
                Vector3 top = transform.TransformPoint(new Vector3(x, 3f, z));
                float groundY = Physics.Raycast(top, Vector3.down, out RaycastHit hit, 8f, mask, QueryTriggerInteraction.Ignore) ? hit.point.y : transform.position.y;
                GameObject post = GameObject.CreatePrimitive(PrimitiveType.Cube);
                post.name = "Post" + i;
                Destroy(post.GetComponent<Collider>());
                post.transform.SetParent(root, true);
                post.transform.position = new Vector3(top.x, groundY + (IsVolume ? 0.45f : 0.9f), top.z);
                post.transform.rotation = transform.rotation;
                post.transform.localScale = IsVolume ? new Vector3(0.1f, 0.9f, 0.1f) : new Vector3(0.12f, 1.8f, 0.12f);
                if (post.TryGetComponent(out Renderer r)) r.SetPropertyBlock(block);
            }
            if (!string.IsNullOrEmpty(Title))
                EconomyLabel.Create(root, Title.ToUpperInvariant(), transform.InverseTransformPoint(transform.position + Vector3.up * (IsVolume ? 2.6f : 2.2f)), 0.07f, MarkerColor);
        }

        private void OnDrawGizmos()
        {
            Gizmos.matrix = transform.localToWorldMatrix;
            Gizmos.color = new Color(MarkerColor.r, MarkerColor.g, MarkerColor.b, 0.4f);
            if (IsVolume) Gizmos.DrawWireCube(new Vector3(0f, (Size.y - 1f) * 0.5f, 0f), new Vector3(Size.x, Size.y + 1f, Size.z));
            else Gizmos.DrawWireSphere(Vector3.up * 0.9f, 0.4f);
        }
    }
}
