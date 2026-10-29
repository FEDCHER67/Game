using System;
using System.Collections.Generic;
using System.IO;
using OnlyVolunteers.Characters.Player;
using OnlyVolunteers.Session;
using UnityEngine;

namespace OnlyVolunteers.UI.MainMenu
{
    /// <summary>
    /// The customiser's rotating full-body preview (29.10: the player is a customisable Sausage Buddy). A small stage far
    /// below the menu with its own camera renders into <see cref="Texture"/> (shown by the menu's RawImage); the body turns
    /// slowly and follows a mouse drag. With the modular PLAYER_SAUSAGE_W86 prefab (<see cref="ModularPrefab"/>, its
    /// PlayerSausageAvatarV01 dresses it from the parts manifest) every option is the real part; without it the crowd body
    /// (SausageBuddy_A) stands in with colour swaps (skin, top on the hoodie, bottom on the shorts, hair on the brows).
    /// Presentation only: nothing here is saved or sent (AppearanceProfileV01 owns the look).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class W86AvatarPreviewV01 : MonoBehaviour
    {
        [Tooltip("The modular player sausage prefab once it exists; empty = the crowd body below.")]
        public GameObject ModularPrefab;
        [Tooltip("Stand-in body until the modular parts exist (Characters/SausageBuddy/SausageBuddy_A.prefab).")]
        public GameObject CrowdBodyPrefab;
        public Vector3 StagePosition = new Vector3(0f, -1000f, 0f);
        public float DegreesPerSecond = 22f;
        public Vector2Int Resolution = new Vector2Int(720, 1000);

        public RenderTexture Texture { get; private set; }
        /// <summary>No modular prefab: the crowd body with colour swaps only.</summary>
        public bool PlaceholderParts => ModularPrefab == null || ModularPrefab.GetComponent<PlayerSausageAvatarV01>() == null;
        PlayerSausageAvatarV01 avatar;

        GameObject stage, body;
        Camera cam;
        float yaw = 200f, dragVelocity;
        bool visible;
        readonly List<(Renderer r, int index, string kind, Color baseColor)> tints = new List<(Renderer, int, string, Color)>();
        MaterialPropertyBlock block;
        static readonly int BaseColor = Shader.PropertyToID("_BaseColor"), ColorId = Shader.PropertyToID("_Color");

        void OnDestroy()
        {
            if (stage != null) Destroy(stage);
            if (Texture != null) { Texture.Release(); Destroy(Texture); }
        }

        /// <summary>Does the avatar offer this option? The modular prefab: what its parts manifest lists; the crowd stand-in:
        /// every catalogue option (Fedya 29.10: show the options on the crowd body until the parts exist).</summary>
        public bool HasPart(AppearanceSlot slot, string optionId)
        {
            var a = ModularPrefab != null ? ModularPrefab.GetComponent<PlayerSausageAvatarV01>() : null;
            return a != null ? a.HasPart(slot, optionId) : AppearanceCatalogV01.IsValid(slot, optionId);
        }

        public void Show(bool on)
        {
            visible = on;
            if (on) Build();
            if (stage != null) stage.SetActive(on);
        }

        void Build()
        {
            if (stage != null) return;
            stage = new GameObject("[Menu] Avatar preview stage");
            stage.transform.position = StagePosition;
            Texture = new RenderTexture(Resolution.x, Resolution.y, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4, name = "AvatarPreview" };
            var camGo = new GameObject("Preview camera");
            camGo.transform.SetParent(stage.transform, false);
            camGo.transform.localPosition = new Vector3(0f, 1.05f, 3.35f);
            camGo.transform.localRotation = Quaternion.Euler(4f, 180f, 0f);
            cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0f, 0f, 0f, 0f);
            cam.fieldOfView = 34f; cam.nearClipPlane = 0.1f; cam.farClipPlane = 20f;
            cam.targetTexture = Texture;
            cam.depth = -10;
            var lightGo = new GameObject("Key light");
            lightGo.transform.SetParent(stage.transform, false);
            lightGo.transform.localRotation = Quaternion.Euler(28f, 150f, 0f);
            var key = lightGo.AddComponent<Light>(); key.type = LightType.Directional; key.intensity = 1.25f; key.color = new Color(1f, 0.95f, 0.86f);
            var fillGo = new GameObject("Fill light");
            fillGo.transform.SetParent(stage.transform, false);
            fillGo.transform.localPosition = new Vector3(-1.6f, 1.6f, 1.8f);
            var fill = fillGo.AddComponent<Light>(); fill.type = LightType.Point; fill.range = 6f; fill.intensity = 1.4f; fill.color = new Color(0.78f, 0.86f, 1f);
            GameObject src = ModularPrefab != null ? ModularPrefab : CrowdBodyPrefab;
            if (src == null) { Debug.LogWarning("[OV Avatar] no body prefab for the preview"); return; }
            body = Instantiate(src, stage.transform);
            body.name = "Avatar (" + src.name + ")";
            body.transform.localPosition = Vector3.zero;
            foreach (var mb in body.GetComponentsInChildren<MonoBehaviour>(true))
                if (!(mb is Animator) && mb.GetType().Namespace != null && mb.GetType().Namespace.StartsWith("OnlyVolunteers", StringComparison.Ordinal)) mb.enabled = false;
            foreach (var rb in body.GetComponentsInChildren<Rigidbody>(true)) rb.isKinematic = true;
            foreach (var c in body.GetComponentsInChildren<Collider>(true)) c.enabled = false;
            avatar = body.GetComponent<PlayerSausageAvatarV01>();
            if (avatar != null) avatar.enabled = true;
            else CollectTints();
            // frame the whole body
            var b = new Bounds(body.transform.position + Vector3.up * 0.9f, Vector3.one * 0.1f);
            foreach (var r in body.GetComponentsInChildren<Renderer>()) b.Encapsulate(r.bounds);
            float h = Mathf.Max(1.2f, b.size.y);
            float dist = h * 0.62f / Mathf.Tan(cam.fieldOfView * 0.5f * Mathf.Deg2Rad);
            camGo.transform.position = new Vector3(b.center.x, b.center.y + h * 0.02f, b.center.z + dist);
            camGo.transform.LookAt(b.center);
        }

        void CollectTints()
        {
            tints.Clear();
            foreach (var r in body.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (mats[i] == null) continue;
                    string n = mats[i].name.ToLowerInvariant();
                    string kind = n.Contains("skin") && !n.Contains("inner") ? "skin" :
                                  n.Contains("brow") ? "hair" :
                                  n.Contains("hoodie") || n.Contains("tee_fabric") || n.Contains("shirt") || n.Contains("jacket") ? "top" :
                                  n.Contains("shorts") || n.Contains("cargo") || n.Contains("pants") || n.Contains("jeans") ? "bottom" : null;
                    if (kind == null) continue;
                    Color baseColor = mats[i].HasProperty(BaseColor) ? mats[i].GetColor(BaseColor) : mats[i].HasProperty(ColorId) ? mats[i].GetColor(ColorId) : Color.white;
                    tints.Add((r, i, kind, baseColor));
                }
            }
        }

        public void Apply(PlayerAppearance a)
        {
            if (body == null || a == null) return;
            if (avatar != null) { avatar.Apply(a); return; }
            block ??= new MaterialPropertyBlock();
            Color skin = AppearanceProfileV01.Swatch(a, AppearanceSlot.Skin, Color.white);
            Color hair = AppearanceProfileV01.Swatch(a, AppearanceSlot.HairColour, Color.black);
            Color top = AppearanceProfileV01.Swatch(a, AppearanceSlot.TopColour, Color.grey);
            Color bottom = AppearanceProfileV01.Swatch(a, AppearanceSlot.BottomColour, Color.grey);
            foreach (var (r, index, kind, baseColor) in tints)
            {
                if (r == null) continue;
                Color want = kind == "skin" ? skin : kind == "hair" ? hair : kind == "top" ? top : bottom;
                // keep the material's own shading steps (rib / shadow / nose) by its brightness relative to the main colour
                float lum = Mathf.Clamp(baseColor.grayscale / 0.55f, 0.55f, 1.25f);
                if (kind == "skin" && r.sharedMaterials[index].name.ToLowerInvariant().Contains("nose")) lum *= 0.93f;
                Color c = want * lum; c.a = 1f;
                r.GetPropertyBlock(block, index);
                block.SetColor(BaseColor, c);
                block.SetColor(ColorId, c);
                r.SetPropertyBlock(block, index);
            }
        }

        static Transform Find(Transform root, string name)
        {
            if (root.name == name) return root;
            foreach (Transform c in root) { var f = Find(c, name); if (f != null) return f; }
            return null;
        }

        /// <summary>Mouse drag over the preview turns the body (degrees per pixel); otherwise it turns slowly.</summary>
        public void Drag(float pixels) { dragVelocity = pixels * 0.45f / Mathf.Max(0.0001f, Time.unscaledDeltaTime); yaw += pixels * 0.45f; }

        void Update()
        {
            if (!visible || body == null) return;
            dragVelocity = Mathf.MoveTowards(dragVelocity, 0f, 900f * Time.unscaledDeltaTime);
            yaw += (DegreesPerSecond + dragVelocity * 0.02f) * Time.unscaledDeltaTime;
            body.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);
        }
    }
}
