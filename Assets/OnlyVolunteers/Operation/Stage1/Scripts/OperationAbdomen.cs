using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>v04 prepared cartoon opening over the unchanged patient mesh, local presentation of server-owned rule state
    /// on every peer. Anatomy still comes from the INC_* markers: the organs, the kidney cords and the liver loop stay on
    /// them. Shows the one belly guide (dashes, pulsing start dot, direction chevrons, cut trail), then the one opening
    /// (cavity, wound lip, pulled-back skin) and the guided loop round the liver. The server uses the same Point/Local/
    /// Coordinates for its checks, so what is drawn is what is validated.</summary>
    [DefaultExecutionOrder(100)]
    public sealed class OperationAbdomen : MonoBehaviour
    {
        private const float LiverModelScale = 1.3f;
        private OperationOpeningV02 approvedOpening;
        public bool OpeningContains(Ray ray) => approvedOpening != null && approvedOpening.Contains(ray);
        private static readonly Color GuideColor = new(0.25f, 0.95f, 0.85f);
        private NetworkOperationTable table;
        private Transform patient, zone, opening;
        private Guide belly, liver;
        /// <summary>Round 3: the seam (sutured v05 meshes) and its guide along the incision line (thread colour).</summary>
        private OperationSutureV05 suture;
        private Guide sutureGuide;
        private OperationTableView viewCache;
        public OperationSutureV05 Suture => suture;
        private int StitchesFor(OperationState s) => s.sutured ? Mathf.Max(1, table.Tuning.sutureStitches) : Mathf.FloorToInt(s.zoneSuture * Mathf.Max(1, table.Tuning.sutureStitches) + 0.0001f);
        private Material skin, cavity, lip, guideMaterial, trailMaterial, startMaterial;
        private bool liverTurned, wasOpened, wasClosed;
        private float openedAt = -10f;

        private sealed class Guide
        {
            public Transform root, start;
            public Transform[] arrows;
            public float[] arrowAt;
            public LineRenderer trail;
            public int index;
        }

        public void ReleasePatientVisuals()
        {
            // Round 2: the body leaves the table with its opening (the cut stays) but without the table's guides (the
            // dashes, the start dot and the liver loop are operation UI, not part of him).
            if (belly?.root != null) belly.root.gameObject.SetActive(false);
            if (liver?.root != null) liver.root.gameObject.SetActive(false);
            if (sutureGuide?.root != null) sutureGuide.root.gameObject.SetActive(false);
            belly = null; sutureGuide = null;
            // Round 3 (lead rule): off the table an opened belly is always closed: the seam if he was sewn up, else the
            // plain skin patch with blood and no stitches (a dead body may leave unsewn), never a see-through cavity.
            var st = table.State;
            if (st != null && st.zoneOpened && suture != null)
            {
                if (zone != null) zone.gameObject.SetActive(true);
                if (opening != null) { opening.gameObject.SetActive(true); opening.localScale = Vector3.one; }
                approvedOpening?.SetCavityVisible(false);
                suture.Show(true, st.sutured ? suture.StitchCount : 0);
                suture.SetClosure(1f, true); // off the table always fully closed (the patch or the finished seam)
            }
            suture = null;
            if (zone != null && table.Anchors != null && table.Anchors.Abdomen != null) zone.SetParent(table.Anchors.Abdomen, true);
            zone = null; opening = null; patient = null; liver = null; approvedOpening = null;
        }

        public void Bind(NetworkOperationTable owner) => table = owner;

        /// <summary>Opening frame: z along the table's up, y toward the head, centred between the kidney markers.</summary>
        public Pose ZonePose
        {
            get
            {
                var anchors = table.Anchors;
                if (table.Tuning.anatomicalLayout && anchors.Abdomen != null) return new Pose(anchors.Abdomen.position, anchors.Abdomen.rotation);
                Vector2 offset = table.Tuning.abdomenOffset;
                Vector3 p = (anchors.Marker(0).position + anchors.Marker(1).position) * 0.5f +
                    table.transform.forward * offset.x + table.transform.up * offset.y;
                return new Pose(p, Quaternion.LookRotation(table.transform.up, table.transform.forward));
            }
        }
        public Vector3 Point(int guide, Vector3 metres)
        {
            if (guide != OperationAbdomenGeometry.ZoneGuide) return table.Anchors.Point(guide, metres);
            var pose = ZonePose; return pose.position + pose.rotation * metres;
        }
        public Vector3 Local(int guide, Vector3 world)
        {
            if (guide != OperationAbdomenGeometry.ZoneGuide) return table.Anchors.LocalMetres(guide, world);
            var pose = ZonePose; return Quaternion.Inverse(pose.rotation) * (world - pose.position);
        }
        public Vector3 Normal(int guide) => guide == OperationAbdomenGeometry.ZoneGuide ? (table.Tuning.anatomicalLayout ? table.Anchors.Normal(3) : table.transform.up) : table.Anchors.Normal(guide);
        public float Progress(int guide) => guide == OperationAbdomenGeometry.ZoneGuide ? (table.State.BellyClosed ? table.State.zoneReopen : table.State.zoneCut) : table.State.organs[2].connectionCut;
        public int Direction(int guide) => guide == 2 && table.State.organs[2].connectionDirection < 0 ? -1 : 1;
        public Vector2 Coordinates(int guide, Vector3 local) => OperationAbdomenGeometry.Coordinates(table.Tuning, guide, local);
        public bool IsGuide(int guide) => guide == OperationAbdomenGeometry.ZoneGuide || guide == 2;
        /// <summary>Where a stroke on this guide continues (the start dot), in world space.</summary>
        public Vector3 ResumePoint(int guide) => Point(guide, OperationAbdomenGeometry.Point(table.Tuning, guide, Progress(guide), Direction(guide)));

        private void LateUpdate()
        {
            if (table == null || !table.AnatomyReady || table.State == null) return;
            var current = table.PatientObject.transform;
            if (patient != current)
            {
                if (zone != null) Destroy(zone.gameObject);
                if (liver?.root != null) Destroy(liver.root.gameObject);
                patient = current; liverTurned = false;
                Build();
                wasOpened = table.State.zoneOpened;
                wasClosed = table.State.BellyClosed;
            }
            if (!table.Tuning.anatomicalLayout && !liverTurned) liverTurned = TurnLiverFaceUp();
            var pose = ZonePose;
            zone.SetPositionAndRotation(pose.position, pose.rotation);
            var state = table.State;
            bool shown = state.onTable;
            zone.gameObject.SetActive(shown);
            opening.gameObject.SetActive(shown && state.zoneOpened);
            // Round 4: from the first stitch the two skin edges close toward the line stitch by stitch (SetClosure); the
            // cavity stays visible under the still open part until the seam is finished. The dead-body patch is closed at once.
            bool closedFully = state.zoneOpened && (state.sutured || state.skinPatched);
            bool patched = state.zoneOpened && (closedFully || state.zoneSuture > 0f);
            bool closing = suture != null && suture.CanClose;
            if (suture != null && patched)
            {
                if (!suture.Shown) suture.SetClosure(closedFully ? 1f : state.zoneSuture, true);
                suture.SetClosure(closedFully ? 1f : state.zoneSuture, !shown);
            }
            approvedOpening?.SetCavityVisible(closing ? !(closedFully && suture.ShownClosure >= 0.999f) : !patched);
            suture?.Show(shown && patched, StitchesFor(state));
            if (state.zoneOpened && wasClosed && !closedFully && state.zoneSuture <= 0f) openedAt = Time.time; // reopened: the same pop
            wasClosed = closedFully || (state.zoneOpened && state.zoneSuture > 0f);
            var localView = viewCache != null ? viewCache : viewCache = table.GetComponent<OperationTableView>();
            bool sewing = localView != null && localView.Active && localView.LocalSlot == ToolSlot.Suture;
            UpdateGuide(sutureGuide, shown && state.zoneOpened && !state.sutured && (sewing || state.zoneSuture > 0f), state.zoneSuture, 1);
            if (state.zoneOpened && !wasOpened) openedAt = Time.time;
            wasOpened = state.zoneOpened;
            float t = Mathf.Clamp01((Time.time - openedAt) / 0.3f);
            float pop = t < 1f ? Mathf.Lerp(0.55f, 1f, Mathf.Sin(t * Mathf.PI * 0.5f)) * (1f + 0.08f * Mathf.Sin(t * Mathf.PI)) : 1f;
            opening.localScale = new Vector3(pop, pop, 1f);
            // Round 4: the same dashed line reopens a closed belly (with the scalpel in hand, or always over the finished patch).
            bool reopenable = state.BellyClosed && (closedFully || (localView != null && localView.LocalSlot == ToolSlot.Scalpel));
            UpdateGuide(belly, shown && (!state.zoneOpened || reopenable), Progress(OperationAbdomenGeometry.ZoneGuide), 1);
            UpdateGuide(liver, shown && state.zoneOpened && !patched && !state.organs[2].removed && !state.organs[2].Released,
                state.organs[2].connectionCut, Direction(2));
        }

        // ---------- build ----------
        private void Build()
        {
            var tuning = table.Tuning;
            // Plain skin tone (the generated bands have no UVs for the body texture).
            skin = OperationVisuals.Lit("abdomen skin", new Color(0.88f, 0.56f, 0.40f), 0.3f);
            cavity = OperationVisuals.Lit("cartoon cavity", new Color(0.30f, 0.12f, 0.22f), 0.25f);
            lip = OperationVisuals.Lit("wound lip", new Color(0.86f, 0.42f, 0.45f), 0.45f);
            guideMaterial = OperationVisuals.Unlit("shared guide", GuideColor);
            trailMaterial = OperationVisuals.Unlit("shared cut trail", new Color(0.75f, 0.06f, 0.12f));
            startMaterial = OperationVisuals.Unlit("shared start", new Color(0.3f, 1f, 0.35f));
            zone = new GameObject("SharedAbdomen_v04").transform;
            zone.SetParent(patient, false);
            var pose = ZonePose; zone.SetPositionAndRotation(pose.position, pose.rotation);
            zone.localScale = Vector3.one / Mathf.Max(0.0001f, patient.lossyScale.x);
            opening = new GameObject("One opening").transform; opening.SetParent(zone, false);
            Vector2 half = tuning.abdomenHalfSize;
            if (tuning.anatomicalLayout && tuning.abdomenModel != null)
            {
                approvedOpening = OperationOpeningV02.Create(tuning, zone, patient);
                opening = approvedOpening.transform;
            }
            else
            {
            Oval("Cavity", opening, cavity, half, 0.002f);
            // Wound lip (pink) round the cavity, then the pulled-back skin: thin at the head and feet ends, rolled
            // wider at both sides, all inside the belly outline so nothing sticks out over the arms.
            Ring("Wound lip", opening, lip, half, 0f, 0.006f, 0.0045f, 0.0035f);
            Ring("Pulled-back skin", opening, skin, half + Vector2.one * 0.005f, 0.004f, 0.013f, 0.0075f, 0.005f);
            }
            belly = BuildGuide(zone, OperationAbdomenGeometry.ZoneGuide);
            // Round 3: the seam guide on the same line, in thread colour (shown with the needle holder in hand).
            var cutColours = (guideMaterial, trailMaterial, startMaterial);
            guideMaterial = OperationVisuals.Unlit("suture guide", new Color(0.55f, 0.65f, 1f));
            trailMaterial = OperationVisuals.Unlit("suture thread", new Color(0.12f, 0.15f, 0.34f));
            startMaterial = OperationVisuals.Unlit("suture start", new Color(0.45f, 0.75f, 1f));
            sutureGuide = BuildGuide(zone, OperationAbdomenGeometry.ZoneGuide);
            sutureGuide.root.name = "Guide_Suture";
            sutureGuide.root.gameObject.SetActive(false);
            (guideMaterial, trailMaterial, startMaterial) = cutColours;
            if (table.Tuning.anatomicalLayout && table.Tuning.suturedModel != null)
                suture = OperationSutureV05.Create(table.Tuning, zone, approvedOpening != null ? approvedOpening.OriginalSkin : null);
            var marker = table.Anchors.Marker(2);
            var liverRoot = new GameObject("LiverAttachmentLoop_v04").transform;
            liverRoot.SetParent(marker, false);
            liverRoot.localScale = Vector3.one / Mathf.Max(0.0001f, marker.lossyScale.x);
            liver = BuildGuide(liverRoot, 2);
            opening.gameObject.SetActive(false);
        }

        private static Transform Oval(string name, Transform parent, Material material, Vector2 half, float height)
        {
            var oval = OperationVisuals.Primitive(PrimitiveType.Cylinder, name, parent, material).transform;
            oval.localPosition = Vector3.forward * height;
            oval.localRotation = Quaternion.Euler(90f, 0f, 0f);
            oval.localScale = new Vector3(half.x * 2f, 0.0012f, half.y * 2f);
            return oval;
        }

        /// <summary>A flat elliptical band from 'half' outward: width = base + sides * |cos| (wider left and right).</summary>
        private static void Ring(string name, Transform parent, Material material, Vector2 half, float widthBase, float widthSides,
            float heightInner, float heightOuter)
        {
            var mesh = new Mesh { name = name + " v04" };
            const int segments = 64;
            var vertices = new Vector3[segments * 2]; var triangles = new int[segments * 12];
            for (int i = 0; i < segments; i++)
            {
                float angle = i * Mathf.PI * 2f / segments;
                var direction = new Vector2(Mathf.Cos(angle), Mathf.Sin(angle));
                float width = widthBase + widthSides * Mathf.Pow(Mathf.Abs(direction.x), 1.5f);
                vertices[i * 2] = new Vector3(direction.x * half.x, direction.y * half.y, heightInner);
                vertices[i * 2 + 1] = new Vector3(direction.x * (half.x + width), direction.y * (half.y + width), heightOuter);
                int j = ((i + 1) % segments) * 2, t = i * 6, k = i * 2;
                // Both windings: the band reads from the camera whatever the zone frame's handedness.
                triangles[t] = k; triangles[t + 1] = j; triangles[t + 2] = k + 1;
                triangles[t + 3] = k + 1; triangles[t + 4] = j; triangles[t + 5] = j + 1;
                int u = segments * 6 + t;
                triangles[u] = k; triangles[u + 1] = k + 1; triangles[u + 2] = j;
                triangles[u + 3] = k + 1; triangles[u + 4] = j + 1; triangles[u + 5] = j;
            }
            var normals = new Vector3[vertices.Length];
            for (int i = 0; i < normals.Length; i++) normals[i] = Vector3.forward;
            mesh.vertices = vertices; mesh.triangles = triangles; mesh.normals = normals; mesh.RecalculateBounds();
            var ring = new GameObject(name); ring.transform.SetParent(parent, false);
            ring.AddComponent<MeshFilter>().sharedMesh = mesh;
            ring.AddComponent<MeshRenderer>().sharedMaterial = material;
        }

        private Guide BuildGuide(Transform parent, int index)
        {
            var tuning = table.Tuning;
            bool loop = index != OperationAbdomenGeometry.ZoneGuide;
            var g = new Guide { index = index, root = new GameObject("Guide_" + index).transform };
            g.root.SetParent(parent, false);
            int count = loop ? 36 : 18;
            float band = OperationAbdomenGeometry.Tolerance(tuning, index);
            for (int i = 0; i < count; i++)
            {
                Vector3 a = OperationAbdomenGeometry.Point(tuning, index, (i + 0.15f) / count) + Vector3.forward * 0.008f;
                Vector3 b = OperationAbdomenGeometry.Point(tuning, index, (i + 0.75f) / count) + Vector3.forward * 0.008f;
                var dash = OperationVisuals.Primitive(PrimitiveType.Cube, "Dash", g.root, guideMaterial).transform;
                dash.localPosition = (a + b) * 0.5f;
                dash.localRotation = Quaternion.LookRotation(Vector3.forward, (b - a).normalized);
                dash.localScale = new Vector3(0.0045f, Vector3.Distance(a, b), 0.002f);
                // Hit volume: the whole length (no gaps between dashes), about the forgiving band wide, and tall
                // enough to be nearer the camera than the organ it surrounds, so a press near the line starts a stroke
                // instead of stabbing the liver.
                Vector3 c0 = OperationAbdomenGeometry.Point(tuning, index, (float)i / count), c1 = OperationAbdomenGeometry.Point(tuning, index, (i + 1f) / count);
                var hit = new GameObject("Hit_Guide"); hit.transform.SetParent(g.root, false);
                hit.transform.localPosition = (c0 + c1) * 0.5f + Vector3.forward * (loop ? 0.03f : 0.012f);
                hit.transform.localRotation = Quaternion.LookRotation(Vector3.forward, (c1 - c0).normalized);
                var collider = hit.AddComponent<BoxCollider>(); collider.isTrigger = true;
                collider.size = new Vector3(loop ? band * 1.4f : 0.045f, Vector3.Distance(c0, c1) + 0.004f, loop ? 0.075f : 0.035f);
                var tag = hit.AddComponent<OperationTargetTag>(); tag.kind = TargetKind.Incision; tag.index = index;
            }
            g.start = OperationVisuals.Primitive(PrimitiveType.Sphere, "StartDot", g.root, startMaterial).transform;
            var startHit = new GameObject("Hit_Start"); startHit.transform.SetParent(g.start, false);
            var sphere = startHit.AddComponent<SphereCollider>(); sphere.isTrigger = true; sphere.radius = 0.9f;
            var startTag = startHit.AddComponent<OperationTargetTag>(); startTag.kind = TargetKind.Incision; startTag.index = index;
            g.trail = OperationVisuals.Line("Cut trail", g.root, trailMaterial, 0.0065f, 2);
            g.trail.useWorldSpace = false;
            // A TransformZ-aligned line shows its front face along -Z: turn it over so it faces the camera above.
            g.trail.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            // Direction chevrons ahead of the blade.
            g.arrowAt = loop ? new[] { 0.09f, 0.26f, 0.43f, 0.6f, 0.77f, 0.92f } : new[] { 0.2f, 0.45f, 0.7f };
            g.arrows = new Transform[g.arrowAt.Length];
            for (int i = 0; i < g.arrows.Length; i++)
            {
                var arrow = new GameObject("Chevron").transform; arrow.SetParent(g.root, false);
                foreach (float side in new[] { -1f, 1f })
                {
                    var bar = OperationVisuals.Primitive(PrimitiveType.Cube, "Bar", arrow, guideMaterial).transform;
                    bar.localScale = new Vector3(0.0035f, 0.012f, 0.002f);
                    bar.localRotation = Quaternion.Euler(0f, 0f, side * 40f);
                    bar.localPosition = new Vector3(side * 0.0038f, -0.0045f, 0f);
                }
                g.arrows[i] = arrow;
            }
            return g;
        }

        private void UpdateGuide(Guide g, bool shown, float progress, int direction)
        {
            if (g == null) return;
            g.root.gameObject.SetActive(shown);
            if (!shown) return;
            var tuning = table.Tuning;
            bool loop = g.index != OperationAbdomenGeometry.ZoneGuide;
            float pulse = (loop ? 0.02f : 0.022f) + Mathf.Sin(Time.time * 6f) * 0.005f;
            g.start.localScale = new Vector3(pulse, pulse, pulse);
            g.start.localPosition = OperationAbdomenGeometry.Point(tuning, g.index, progress, direction) + Vector3.forward * 0.011f;
            g.trail.gameObject.SetActive(progress > 0.001f);
            int count = loop ? Mathf.Max(2, Mathf.CeilToInt(progress * 72f) + 1) : 2;
            g.trail.positionCount = count;
            for (int i = 0; i < count; i++)
            {
                Vector3 p = OperationAbdomenGeometry.Point(tuning, g.index, progress * i / (count - 1f), direction) + Vector3.forward * 0.0095f;
                g.trail.SetPosition(i, new Vector3(-p.x, p.y, -p.z));
            }
            // Before the loop has a direction, the chevrons suggest the positive way (counter-clockwise on screen); either way works.
            for (int i = 0; i < g.arrows.Length; i++)
            {
                float at = g.arrowAt[i];
                bool ahead = at > progress + 0.03f;
                g.arrows[i].gameObject.SetActive(ahead);
                if (!ahead) continue;
                Vector3 p = OperationAbdomenGeometry.Point(tuning, g.index, at, direction);
                Vector3 q = OperationAbdomenGeometry.Point(tuning, g.index, at + 0.01f, direction);
                g.arrows[i].localPosition = p + Vector3.forward * 0.0105f;
                g.arrows[i].localRotation = Quaternion.LookRotation(Vector3.forward, (q - p).normalized);
            }
        }

        /// <summary>The liver world model's broad face points along the marker's Y, so the top camera saw it edge-on.
        /// Turn it face-up inside its own site (presentation only; the site, its hit volume and the rules are unchanged).</summary>
        private bool TurnLiverFaceUp()
        {
            var site = FindChild(table.Anchors.Marker(2), "Site_LIVER");
            var organ = site != null ? FindChild(site, "Organ") : null;
            if (organ == null) return false;
            Transform model = null;
            for (int i = 0; i < organ.childCount; i++) if (organ.GetChild(i).GetComponentInChildren<Renderer>(true) != null) { model = organ.GetChild(i); break; }
            if (model == null) return false;
            var turn = Quaternion.Euler(-90f, 0f, 0f);
            model.localRotation = turn * model.localRotation;
            model.localPosition = turn * model.localPosition * LiverModelScale;
            model.localScale *= LiverModelScale;
            return true;
        }
        private static Transform FindChild(Transform root, string name)
        {
            for (int i = 0; i < root.childCount; i++) if (root.GetChild(i).name == name) return root.GetChild(i);
            return null;
        }
    }
}
