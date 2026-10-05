using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Faceted stand-ins for the street kit, trees and rocks until the cloud-made FBX land in the registry.
    // Props are built at real size with the origin on the ground and +Z as their front; trees are 1 m tall
    // (TreeInstance height scale = tree height); rocks fill a unit cube (scaled by the json sx, sy, sz).
    public static class PlaceholderKit
    {
        public static MeshDraft Prop(string type, out bool collide)
        {
            var d = new MeshDraft();
            collide = true;
            int metal = d.Slot("mat/metal"), wood = d.Slot("mat/wood"), conc = d.Slot("mat/concrete");
            Quaternion id = Quaternion.identity;
            switch (type)
            {
                case "lamp_street":
                    d.Cylinder(metal, Vector3.zero, 0.09f, 6.2f, 6, true);
                    d.Beam(metal, new Vector3(0f, 0f, 0f), new Vector3(0f, 0f, 1.5f), 0.08f, 6.0f, 6.1f);
                    d.Box(metal, new Vector3(0f, 5.95f, 1.55f), new Vector3(0.35f, 0.16f, 0.6f), id, true);
                    d.Box(d.Slot("mat/glass_lit"), new Vector3(0f, 5.85f, 1.55f), new Vector3(0.28f, 0.04f, 0.5f), id, true);
                    break;
                case "lamp_iron":
                    d.Box(d.Slot("mat/iron"), new Vector3(0f, 0.3f, 0f), new Vector3(0.4f, 0.6f, 0.4f), id);
                    d.Cylinder(d.Slot("mat/iron"), Vector3.zero, 0.07f, 3.6f, 6, false);
                    d.Box(d.Slot("mat/glass_lit"), new Vector3(0f, 3.85f, 0f), new Vector3(0.36f, 0.5f, 0.36f), id);
                    d.Lathe(d.Slot("mat/iron"), new Vector3(0f, 4.1f, 0f), new[] { 0.32f, 0f }, new[] { 0f, 0.3f }, 4, Mathf.PI / 4f);
                    break;
                case "lamp_bollard":
                    d.Cylinder(d.Slot("mat/iron"), Vector3.zero, 0.12f, 0.9f, 8, true);
                    d.Cylinder(d.Slot("mat/glass_lit"), new Vector3(0f, 0.7f, 0f), 0.125f, 0.12f, 8, false);
                    break;
                case "power_pole":
                    d.Cylinder(d.Slot("mat/wood/dark"), Vector3.zero, 0.13f, 8.5f, 6, true);
                    d.Box(d.Slot("mat/wood/dark"), new Vector3(0f, 7.9f, 0f), new Vector3(1.8f, 0.12f, 0.12f), id);
                    for (int k = -1; k <= 1; k++) d.Box(d.Slot("mat/white"), new Vector3(k * 0.75f, 8.05f, 0f), new Vector3(0.08f, 0.18f, 0.08f), id);
                    break;
                case "bench":
                    d.Box(wood, new Vector3(0f, 0.45f, 0f), new Vector3(1.8f, 0.06f, 0.45f), id);
                    d.Box(wood, new Vector3(0f, 0.75f, -0.22f), new Vector3(1.8f, 0.35f, 0.05f), Quaternion.Euler(-12f, 0f, 0f));
                    for (int k = -1; k <= 1; k += 2) d.Box(metal, new Vector3(k * 0.75f, 0.22f, 0f), new Vector3(0.06f, 0.44f, 0.4f), id);
                    break;
                case "bin":
                    d.Cylinder(d.Slot("mat/metal", "#4E6E5A"), Vector3.zero, 0.25f, 0.9f, 8, true);
                    break;
                case "garbage_container":
                    d.Box(d.Slot("mat/metal", "#4E6E5A"), new Vector3(0f, 0.65f, 0f), new Vector3(1.8f, 1.1f, 1.0f), id);
                    d.Box(d.Slot("mat/metal", "#3E4E44"), new Vector3(0f, 1.25f, 0f), new Vector3(1.85f, 0.1f, 1.05f), Quaternion.Euler(-6f, 0f, 0f));
                    for (int k = -1; k <= 1; k += 2) d.Box(metal, new Vector3(k * 0.7f, 0.05f, 0f), new Vector3(0.12f, 0.1f, 0.12f), id);
                    break;
                case "bus_stop":
                    d.Box(d.Slot("mat/glass"), new Vector3(0f, 1.3f, -0.7f), new Vector3(3.6f, 2.2f, 0.06f), id);
                    for (int k = -1; k <= 1; k += 2) d.Box(d.Slot("mat/glass"), new Vector3(k * 1.8f, 1.3f, -0.2f), new Vector3(0.06f, 2.2f, 1.0f), id);
                    d.Box(d.Slot("mat/roof/sheet", "#6E7478"), new Vector3(0f, 2.5f, -0.2f), new Vector3(4.0f, 0.14f, 1.8f), id, true);
                    d.Box(wood, new Vector3(0f, 0.45f, -0.45f), new Vector3(2.6f, 0.07f, 0.4f), id, true);
                    for (int k = -1; k <= 1; k += 2) d.Box(metal, new Vector3(k * 1.85f, 1.25f, -0.7f), new Vector3(0.1f, 2.5f, 0.1f), id);
                    break;
                case "bus_stop_sign":
                    collide = true;
                    d.Cylinder(metal, Vector3.zero, 0.04f, 2.6f, 6, true);
                    d.Box(d.Slot("mat/neon/yellow"), new Vector3(0f, 2.5f, 0f), new Vector3(0.5f, 0.5f, 0.04f), id);
                    break;
                case "sign_crossing":
                    d.Cylinder(metal, Vector3.zero, 0.04f, 2.4f, 6, true);
                    d.Box(d.Slot("mat/canvas/blue"), new Vector3(0f, 2.35f, 0f), new Vector3(0.6f, 0.6f, 0.04f), id);
                    d.Tri(d.Slot("mat/white"), new Vector3(-0.22f, 2.17f, 0.025f), new Vector3(0f, 2.55f, 0.025f), new Vector3(0.22f, 2.17f, 0.025f));
                    break;
                case "sign_no_swimming":
                    d.Cylinder(metal, Vector3.zero, 0.04f, 2.0f, 6, true);
                    d.Box(d.Slot("mat/white"), new Vector3(0f, 1.9f, 0f), new Vector3(0.7f, 0.5f, 0.04f), id);
                    d.Box(d.Slot("mat/red"), new Vector3(0f, 1.9f, 0.025f), new Vector3(0.6f, 0.08f, 0.01f), Quaternion.Euler(0f, 0f, 35f));
                    break;
                case "swings":
                {
                    int rust = d.Slot("mat/rust");
                    for (int k = -1; k <= 1; k += 2)
                    {
                        d.Box(rust, new Vector3(k * 1.3f, 1.25f, -0.45f), new Vector3(0.08f, 2.6f, 0.08f), Quaternion.Euler(-10f, 0f, 0f));
                        d.Box(rust, new Vector3(k * 1.3f, 1.25f, 0.45f), new Vector3(0.08f, 2.6f, 0.08f), Quaternion.Euler(10f, 0f, 0f));
                    }
                    d.Box(rust, new Vector3(0f, 2.5f, 0f), new Vector3(2.8f, 0.08f, 0.08f), id);
                    for (int k = -1; k <= 1; k += 2)
                    {
                        d.Box(wood, new Vector3(k * 0.6f, 0.5f, 0f), new Vector3(0.5f, 0.05f, 0.25f), id);
                        d.Box(metal, new Vector3(k * 0.6f - 0.22f, 1.5f, 0f), new Vector3(0.02f, 2.0f, 0.02f), id);
                        d.Box(metal, new Vector3(k * 0.6f + 0.22f, 1.5f, 0f), new Vector3(0.02f, 2.0f, 0.02f), id);
                    }
                    break;
                }
                case "slide":
                {
                    int paint = d.Slot("mat/canvas/red");
                    d.Box(metal, new Vector3(0f, 0.75f, -1.2f), new Vector3(0.7f, 1.5f, 0.6f), id);
                    d.Box(paint, new Vector3(0f, 1.52f, -1.2f), new Vector3(0.8f, 0.06f, 0.7f), id);
                    Vector3 a = new Vector3(-0.3f, 1.5f, -0.9f), b = new Vector3(0.3f, 1.5f, -0.9f), c = new Vector3(0.3f, 0.2f, 1.3f), e = new Vector3(-0.3f, 0.2f, 1.3f);
                    d.QuadBoth(d.Slot("mat/metal", "#B8BEC2"), a, b, c, e);
                    break;
                }
                case "sandbox":
                    for (int k = 0; k < 4; k++)
                    {
                        Quaternion q = Quaternion.Euler(0f, 90f * k, 0f);
                        d.Box(wood, q * new Vector3(0f, 0.15f, 1.0f), new Vector3(2.1f, 0.3f, 0.1f), q);
                    }
                    d.Quad(d.Slot("mat/ground/sand", "#E6D6A8"), new Vector3(-0.95f, 0.12f, -0.95f), new Vector3(-0.95f, 0.12f, 0.95f), new Vector3(0.95f, 0.12f, 0.95f), new Vector3(0.95f, 0.12f, -0.95f));
                    collide = false;
                    break;
                case "carpet_rack":
                {
                    int rust = d.Slot("mat/rust");
                    for (int k = -1; k <= 1; k += 2) d.Box(rust, new Vector3(k * 1.2f, 0.9f, 0f), new Vector3(0.07f, 1.8f, 0.07f), id);
                    d.Box(rust, new Vector3(0f, 1.75f, 0f), new Vector3(2.5f, 0.06f, 0.06f), id);
                    d.Box(rust, new Vector3(0f, 1.2f, 0f), new Vector3(2.5f, 0.05f, 0.05f), id);
                    break;
                }
                case "pipe_support":
                    d.Box(conc, new Vector3(0f, 0.3f, 0f), new Vector3(1.0f, 0.6f, 0.5f), id);
                    break;
                case "kiosk":
                    d.Box(d.Slot("mat/wall/commercial", "#4FA6A0"), new Vector3(0f, 1.3f, 0f), new Vector3(3.0f, 2.6f, 2.2f), id);
                    d.Box(d.Slot("mat/white"), new Vector3(0f, 2.7f, 0.1f), new Vector3(3.4f, 0.2f, 2.8f), id, true);
                    d.Quad(d.Slot("mat/glass"), new Vector3(-0.6f, 1.0f, 1.11f), new Vector3(-0.6f, 1.8f, 1.11f), new Vector3(0.6f, 1.8f, 1.11f), new Vector3(0.6f, 1.0f, 1.11f));
                    break;
                case "atm":
                    d.Box(d.Slot("mat/metal", "#3A5A8A"), new Vector3(0f, 0.9f, 0f), new Vector3(0.8f, 1.8f, 0.7f), id);
                    d.Quad(d.Slot("mat/glass_lit"), new Vector3(-0.25f, 1.2f, 0.36f), new Vector3(-0.25f, 1.5f, 0.36f), new Vector3(0.25f, 1.5f, 0.36f), new Vector3(0.25f, 1.2f, 0.36f));
                    break;
                case "ad_pole":
                    d.Cylinder(metal, Vector3.zero, 0.2f, 3.2f, 8, false);
                    d.Box(d.Slot("mat/sign"), new Vector3(0f, 3.9f, 0f), new Vector3(3.6f, 1.8f, 0.2f), id, true);
                    break;
                case "camera":
                    d.Cylinder(d.Slot("mat/iron"), Vector3.zero, 0.05f, 3.2f, 6, true);
                    d.Box(d.Slot("mat/white"), new Vector3(0f, 3.25f, 0.15f), new Vector3(0.16f, 0.16f, 0.4f), Quaternion.Euler(20f, 0f, 0f));
                    collide = false;
                    break;
                case "log_bench":
                    d.Box(d.Slot("mat/wood/dark"), new Vector3(0f, 0.25f, 0f), new Vector3(2.2f, 0.4f, 0.45f), id);
                    break;
                default:
                    d.Box(d.Slot("mat/concrete"), new Vector3(0f, 0.25f, 0f), new Vector3(0.5f, 0.5f, 0.5f), id);
                    break;
            }
            return d;
        }

        public static MeshDraft Tree(string species, out float trunkRadius)
        {
            var d = new MeshDraft();
            int trunk = d.Slot(species == "birch" ? "mat/trunk/birch" : species == "palm" ? "mat/trunk/palm" : "mat/trunk");
            int leaves = d.Slot("mat/leaves/" + species);
            trunkRadius = 0.025f;
            switch (species)
            {
                case "pine":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.025f, 0.016f }, new[] { 0f, 0.8f }, 5);
                    Blob(d, leaves, new Vector3(0f, 0.62f, 0f), 0.2f, 0.25f);
                    Blob(d, leaves, new Vector3(0.06f, 0.74f, 0.03f), 0.17f, 0.22f);
                    Blob(d, leaves, new Vector3(-0.05f, 0.8f, -0.04f), 0.14f, 0.2f);
                    break;
                case "spruce":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.03f, 0.02f }, new[] { 0f, 0.25f }, 5);
                    d.Lathe(leaves, new Vector3(0f, 0.12f, 0f), new[] { 0.3f, 0f }, new[] { 0f, 0.45f }, 7);
                    d.Lathe(leaves, new Vector3(0f, 0.38f, 0f), new[] { 0.23f, 0f }, new[] { 0f, 0.4f }, 7, 0.4f);
                    d.Lathe(leaves, new Vector3(0f, 0.62f, 0f), new[] { 0.15f, 0f }, new[] { 0f, 0.38f }, 7, 0.8f);
                    trunkRadius = 0.03f;
                    break;
                case "birch":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.02f, 0.012f }, new[] { 0f, 0.75f }, 5);
                    Blob(d, leaves, new Vector3(0f, 0.38f, 0f), 0.17f, 0.62f);
                    trunkRadius = 0.02f;
                    break;
                case "poplar":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.025f, 0.015f }, new[] { 0f, 0.4f }, 5);
                    Blob(d, leaves, new Vector3(0f, 0.15f, 0f), 0.11f, 0.85f);
                    break;
                case "cypress":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.02f, 0.015f }, new[] { 0f, 0.2f }, 5);
                    d.Lathe(leaves, new Vector3(0f, 0.06f, 0f), new[] { 0.08f, 0.1f, 0.07f, 0f }, new[] { 0f, 0.25f, 0.65f, 0.94f }, 7);
                    break;
                case "palm":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.035f, 0.025f }, new[] { 0f, 0.9f }, 6);
                    for (int k = 0; k < 7; k++)
                    {
                        float a = k * Mathf.PI * 2f / 7f;
                        Vector3 dir = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)), side = Vector3.Cross(Vector3.up, dir) * 0.05f;
                        Vector3 root = new Vector3(0f, 0.9f, 0f), mid = root + dir * 0.22f + Vector3.up * 0.06f, tip = root + dir * 0.42f - Vector3.up * 0.12f;
                        d.QuadBoth(leaves, root - side * 0.3f, mid - side, mid + side, root + side * 0.3f);
                        d.Tri(leaves, mid - side, tip, mid + side);
                        d.Tri(leaves, mid + side, tip, mid - side);
                    }
                    trunkRadius = 0.035f;
                    break;
                case "willow":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.045f, 0.03f }, new[] { 0f, 0.45f }, 5);
                    d.Lathe(leaves, new Vector3(0f, 0.18f, 0f), new[] { 0.36f, 0.45f, 0.38f, 0.2f, 0f }, new[] { 0f, 0.3f, 0.55f, 0.75f, 0.82f }, 8);
                    trunkRadius = 0.045f;
                    break;
                case "bush":
                    Blob(d, leaves, new Vector3(0f, 0f, 0f), 0.6f, 1f);
                    trunkRadius = 0f;
                    break;
                case "fruit":
                    d.Lathe(trunk, Vector3.zero, new[] { 0.05f, 0.035f }, new[] { 0f, 0.45f }, 5);
                    Blob(d, leaves, new Vector3(0f, 0.32f, 0f), 0.42f, 0.68f);
                    trunkRadius = 0.05f;
                    break;
                default:
                    d.Lathe(trunk, Vector3.zero, new[] { 0.04f, 0.025f }, new[] { 0f, 0.5f }, 5);
                    Blob(d, leaves, new Vector3(0f, 0.3f, 0f), 0.33f, 0.7f);
                    Blob(d, leaves, new Vector3(0.12f, 0.45f, 0.05f), 0.22f, 0.5f);
                    trunkRadius = 0.04f;
                    break;
            }
            return d;
        }

        // Faceted canopy blob: seven-sided lathe, origin at its bottom.
        private static void Blob(MeshDraft d, int slot, Vector3 baseP, float radius, float height)
        {
            d.Lathe(slot, baseP, new[] { 0f, radius * 0.75f, radius, radius * 0.85f, radius * 0.45f, 0f },
                new[] { 0f, height * 0.12f, height * 0.38f, height * 0.66f, height * 0.88f, height }, 7, baseP.x * 3f);
        }

        // Rock: jittered octahedron subdivided once, fitted to a unit cube with its base slightly below 0.
        public static MeshDraft Rock(int variant)
        {
            var d = new MeshDraft();
            int slot = d.Slot("mat/rock");
            Vector3[] v =
            {
                new(1f, 0f, 0f), new(-1f, 0f, 0f), new(0f, 1f, 0f), new(0f, -1f, 0f), new(0f, 0f, 1f), new(0f, 0f, -1f),
            };
            int[] f = { 0, 2, 4, 4, 2, 1, 1, 2, 5, 5, 2, 0, 0, 4, 3, 4, 1, 3, 1, 5, 3, 5, 0, 3 };
            for (int i = 0; i < f.Length; i += 3)
            {
                Vector3 a = v[f[i]], b = v[f[i + 1]], c = v[f[i + 2]];
                Vector3 ab = Jit((a + b).normalized, variant), bc = Jit((b + c).normalized, variant), ca = Jit((c + a).normalized, variant);
                a = Jit(a, variant);
                b = Jit(b, variant);
                c = Jit(c, variant);
                Emit(d, slot, a, ab, ca);
                Emit(d, slot, ab, b, bc);
                Emit(d, slot, ca, bc, c);
                Emit(d, slot, ab, bc, ca);
            }
            return d;
        }

        // Jitter keyed on the position, so shared corners move together and the rock stays closed.
        private static Vector3 Jit(Vector3 p, int variant)
        {
            int h = Mathf.RoundToInt(p.x * 7f) * 73 + Mathf.RoundToInt(p.y * 7f) * 19 + Mathf.RoundToInt(p.z * 7f) * 5;
            float k = 0.82f + LookGeom.Hash01(h, variant, 11) * 0.3f;
            var q = p * k * 0.5f;
            q.y = q.y * 0.9f + 0.4f;
            return q;
        }

        private static void Emit(MeshDraft d, int slot, Vector3 a, Vector3 b, Vector3 c)
        {
            Vector3 centre = (a + b + c) / 3f - new Vector3(0f, 0.4f, 0f);
            d.TriFacing(slot, a, b, c, centre);
        }
    }
}
