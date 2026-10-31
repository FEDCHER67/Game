using System.Collections.Generic;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>
    /// A displayed item of a V2 base shop (Fedya 31.10, plan P1 "physical purchases"): reusable for every later item and
    /// room. Put it on the item's root (its meshes and colliders below it) and set <see cref="ItemId"/> (GearCatalogV2).
    /// Aim at it within <see cref="Reach"/>: a restrained coloured outline appears on THIS item only (an inverted hull of
    /// its own meshes, two thin shells: a solid line and a faint wider halo; no screen pass, no bloom, no shimmer) and the
    /// existing aim hint line (GreyboxInteractor, via GreyboxUses) shows the name and price, with the effect one line
    /// above. Colour AND text say the state: amber = can buy (E), red = not enough money, green = the team owns it.
    /// E sends one purchase request through BaseV2DirectorV01 (server-authoritative TeamEconomy commit; the server measures
    /// reach and sight itself); the button is dead until the answer comes back. The display is not loot: buying never
    /// removes or duplicates it.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ShopDisplayItemV2 : MonoBehaviour, IGreyboxUse
    {
        private static readonly List<ShopDisplayItemV2> All = new List<ShopDisplayItemV2>();
        private static readonly int OutlineColorId = Shader.PropertyToID("_OutlineColor");
        private static readonly RaycastHit[] Hits = new RaycastHit[12];

        public string ItemId = GearCatalogV2.Baton;
        [Tooltip("Metres from the player's feet (flat) within which aiming at it offers the purchase.")]
        public float Reach = 2.6f;
        [Tooltip("The meshes that get the outline (empty = every MeshFilter below, except the stand).")]
        public MeshFilter[] OutlineMeshes = new MeshFilter[0];
        public Material OutlineMaterial;
        public Material HaloMaterial;
        public Color CanBuy = new Color(1f, 0.74f, 0.25f, 1f);
        public Color CannotAfford = new Color(0.88f, 0.3f, 0.22f, 1f);
        public Color Owned = new Color(0.45f, 0.86f, 0.5f, 1f);

        private readonly List<Renderer> hull = new List<Renderer>();
        private MaterialPropertyBlock block;
        private int hoverFrame = -10;
        private bool shown, busy;
        private string effectLine = "";
        private Color shownColor;

        public Vector3 AimPoint { get; private set; }
        public bool Hovered => Time.frameCount - hoverFrame <= 1;
        public bool Busy => busy;
        /// <summary>The last label the hint line showed (tests and the log).</summary>
        public string LastLabel { get; private set; } = "";
        public string LastEffect => effectLine;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => All.Clear();

        public static ShopDisplayItemV2 Find(string itemId)
        {
            foreach (ShopDisplayItemV2 d in All) if (d != null && d.isActiveAndEnabled && d.ItemId == itemId) return d;
            return null;
        }

        public bool Owns(Collider c) => c != null && c.transform.IsChildOf(transform);

        private void OnEnable()
        {
            if (!All.Contains(this)) All.Add(this);
            if (!GreyboxUses.All.Contains(this)) GreyboxUses.All.Add(this);
            AimPoint = Centre();
        }

        private void OnDisable()
        {
            All.Remove(this);
            GreyboxUses.All.Remove(this);
            Show(false, default);
        }

        private void Start()
        {
            AimPoint = Centre();
            BuildHull();
        }

        private Vector3 Centre()
        {
            var b = new Bounds();
            bool any = false;
            foreach (MeshFilter mf in Meshes())
            {
                Renderer r = mf.GetComponent<Renderer>();
                if (r == null) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            return any ? b.center : transform.position;
        }

        private IEnumerable<MeshFilter> Meshes()
        {
            if (OutlineMeshes != null && OutlineMeshes.Length > 0)
            {
                foreach (MeshFilter m in OutlineMeshes) if (m != null && m.sharedMesh != null) yield return m;
                yield break;
            }
            foreach (MeshFilter m in GetComponentsInChildren<MeshFilter>(true))
                if (m.sharedMesh != null && !m.name.StartsWith("Outline")) yield return m;
        }

        // ================================================================== outline (inverted hull of this item only)

        private void BuildHull()
        {
            if (hull.Count > 0 || OutlineMaterial == null) return;
            foreach (MeshFilter mf in new List<MeshFilter>(Meshes()))
            {
                var go = new GameObject("Outline " + mf.name);
                go.transform.SetParent(mf.transform, false);
                go.layer = mf.gameObject.layer;
                go.AddComponent<MeshFilter>().sharedMesh = SmoothNormals(mf.sharedMesh);
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterials = HaloMaterial != null ? new[] { OutlineMaterial, HaloMaterial } : new[] { OutlineMaterial };
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                r.receiveShadows = false;
                r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;
                r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
                Renderer src = mf.GetComponent<Renderer>();
                if (src != null) r.renderingLayerMask = src.renderingLayerMask;
                r.enabled = false;
                hull.Add(r);
            }
        }

        /// <summary>A copy whose normals are averaged over every vertex at the same place, so the pushed-out hull of a
        /// chunky faceted mesh stays closed at its corners (no cracks, no flicker along hard edges).</summary>
        public static Mesh SmoothNormals(Mesh src)
        {
            var m = Object.Instantiate(src);
            m.name = src.name + " (outline)";
            Vector3[] v = m.vertices, n = m.normals;
            if (n == null || n.Length != v.Length) { m.RecalculateNormals(); n = m.normals; }
            var sum = new Dictionary<Vector3Int, Vector3>();
            Vector3Int Key(Vector3 p) => new Vector3Int(Mathf.RoundToInt(p.x * 2000f), Mathf.RoundToInt(p.y * 2000f), Mathf.RoundToInt(p.z * 2000f));
            for (int i = 0; i < v.Length; i++)
            {
                Vector3Int k = Key(v[i]);
                sum[k] = (sum.TryGetValue(k, out Vector3 s) ? s : Vector3.zero) + n[i];
            }
            var outN = new Vector3[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                Vector3 s = sum[Key(v[i])];
                outN[i] = s.sqrMagnitude > 1e-8f ? s.normalized : n[i];
            }
            m.normals = outN;
            return m;
        }

        private void Show(bool on, Color c)
        {
            if (on == shown && (!on || c == shownColor)) return;
            shown = on;
            shownColor = c;
            block ??= new MaterialPropertyBlock();
            foreach (Renderer r in hull)
            {
                if (r == null) continue;
                r.enabled = on;
                if (!on) continue;
                for (int i = 0; i < r.sharedMaterials.Length; i++)
                {
                    block.Clear();
                    Color col = c;
                    if (i == 1) col.a = 0.22f; // the halo: the same hue, faint
                    block.SetColor(OutlineColorId, col);
                    r.SetPropertyBlock(block, i);
                }
            }
        }

        private void LateUpdate()
        {
            if (!Hovered) Show(false, default);
        }

        // ================================================================== aim + E (GreyboxInteractor asks every frame)

        /// <summary>The crosshair is on this item within reach (a thin ray first, then a 4 cm fat one, so a stick is easy).</summary>
        public bool AimedBy(GreyboxPawn pawn)
        {
            if (pawn == null || !pawn.Controlled) return false;
            Vector3 flat = AimPoint - pawn.Position;
            flat.y = 0f;
            if (flat.magnitude > Reach) return false;
            Camera cam = pawn.ViewCamera != null ? pawn.ViewCamera : Camera.main;
            if (cam == null) return false;
            var ray = new Ray(cam.transform.position, cam.transform.forward);
            float len = Reach + 1.2f;
            int mask = OvLayers.ShootMask & ~(1 << OvLayers.RemotePlayer);
            if (Physics.Raycast(ray, out RaycastHit hit, len, mask, QueryTriggerInteraction.Ignore)) return Owns(hit.collider);
            int n = Physics.SphereCastNonAlloc(ray, 0.04f, Hits, len, mask, QueryTriggerInteraction.Ignore);
            float best = float.MaxValue;
            Collider first = null;
            for (int i = 0; i < n; i++)
                if (Hits[i].collider != null && Hits[i].distance > 0f && Hits[i].distance < best) { best = Hits[i].distance; first = Hits[i].collider; }
            return Owns(first);
        }

        public bool Offer(GreyboxPawn pawn, out string label)
        {
            label = null;
            if (!AimedBy(pawn)) return false;
            hoverFrame = Time.frameCount;
            GearOfferV2 offer = GearCatalogV2.Find(ItemId);
            if (offer == null) { label = "Этого товара нет в каталоге"; Show(true, CannotAfford); LastLabel = label; return true; }
            string price = EconomyState.Money(offer.Price) + (offer.PriceNote.Length > 0 ? " (" + offer.PriceNote + ")" : "");
            effectLine = offer.Title + ": " + offer.Effect;
            if (!BaseV2DirectorV01.EconomyReady) { label = offer.Title + " · " + price + " · касса: секунду…"; Show(true, CannotAfford); }
            else if (BaseV2DirectorV01.TeamOwns(ItemId)) { label = "«" + offer.Title + "» — у команды уже есть · X — достать / убрать"; Show(true, Owned); }
            else if (busy) { label = "Покупка «" + offer.Title + "»… ждём кассу"; Show(true, CanBuy); }
            else if (BaseV2DirectorV01.Balance < offer.Price)
            {
                label = "Не хватает денег: «" + offer.Title + "» " + price + ", в общем фонде " + EconomyState.Money(BaseV2DirectorV01.Balance);
                Show(true, CannotAfford);
            }
            else { label = "E — купить «" + offer.Title + "» · " + price; Show(true, CanBuy); }
            LastLabel = label;
            return true;
        }

        public void Use(GreyboxPawn pawn)
        {
            GreyboxInput.UseE();
            if (busy || !AimedBy(pawn)) return;
            GearOfferV2 offer = GearCatalogV2.Find(ItemId);
            BaseV2DirectorV01 director = BaseV2DirectorV01.Instance;
            if (offer == null || director == null) return;
            if (BaseV2DirectorV01.TeamOwns(ItemId)) { Toast(false, "Уже куплено: " + offer.Title); return; }
            busy = true;
            director.RequestBuy(ItemId, offer.Price, (ok, text) =>
            {
                busy = false;
                Toast(ok, string.IsNullOrEmpty(text) ? (ok ? "Куплено" : "Не вышло — деньги не списаны") : text + (ok ? " · X — достать дубинку" : " — деньги не списаны"));
            });
        }

        /// <summary>Test hook: the same request E sends (one call = one request).</summary>
        public bool ScriptBuy(System.Action<bool, string> done)
        {
            GearOfferV2 offer = GearCatalogV2.Find(ItemId);
            BaseV2DirectorV01 director = BaseV2DirectorV01.Instance;
            if (busy || offer == null || director == null) return false;
            busy = true;
            director.RequestBuy(ItemId, offer.Price, (ok, text) => { busy = false; done?.Invoke(ok, text); });
            return true;
        }

        /// <summary>Test hook: show the hover outline as the given state (for review shots).</summary>
        public void ScriptHover(int state)
        {
            hoverFrame = Time.frameCount + 100000;
            Show(true, state == 2 ? Owned : state == 1 ? CannotAfford : CanBuy);
        }

        private static void Toast(bool ok, string text) =>
            CaptureDirector.Instance?.Toast(text, ok ? CaptureHud.Good : CaptureHud.Warn, 4f);

        private void OnGUI()
        {
            if (!Hovered || OnlyVolunteers.UI.OvMenuGate.Blocking || effectLine.Length == 0) return;
            // the effect, one line above the interactor's hint line (same place, same style)
            var style = new GUIStyle(GUI.skin.label) { fontSize = 16, alignment = TextAnchor.MiddleCenter, wordWrap = true };
            var rect = new Rect(40f, Screen.height - 128f, Screen.width - 420f, 54f);
            style.normal.textColor = new Color(0f, 0f, 0f, 0.8f);
            GUI.Label(new Rect(rect.x + 1.5f, rect.y + 1.5f, rect.width, rect.height), effectLine, style);
            style.normal.textColor = new Color(1f, 0.93f, 0.78f);
            GUI.Label(rect, effectLine, style);
        }
    }
}
