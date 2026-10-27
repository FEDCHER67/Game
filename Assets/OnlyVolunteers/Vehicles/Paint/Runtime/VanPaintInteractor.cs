using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Vehicles.Paint
{
    // Standalone test input. Main-map integration must gate its grab/phone/scroll owners.
    [DefaultExecutionOrder(-900)]
    public sealed class VanPaintInteractor : MonoBehaviour
    {
        [SerializeField] Camera view;
        [SerializeField] VanPaintSurface van;
        [SerializeField] VanPaintHud hud;
        [SerializeField] Transform canHand;
        [SerializeField] Transform brushHand;
        [SerializeField] Vector3 orbitCentre = new(0, 1, 0);
        [SerializeField] float brushRadius = .04f;
        [SerializeField] VanPaintMeshQuery meshQuery;
        [SerializeField] bool firstPerson;
        [SerializeField] float reach = 12;
        public event System.Action<bool> TextModeChanged;
        VanPaintProp can, brush;
        VanPaintSurface activeStroke;
        readonly List<PaintDab> segment = new();
        Vector2? lastUv;
        Rect lastIsland;
        Vector2 textUv;
        VanPaintSurface textSurface;
        float wipeUntil;
        bool strokeLimitedUntilRelease;
        public bool HasTools => can != null && brush != null;
        public float BrushRadius => brushRadius;
        public Color CurrentColor => can != null ? can.PaintColor : Color.white;
        public string Message { get; private set; } = "Aim at the brush and press B, then pick a paint can.";
        public bool TextOpen { get; private set; }
        public string HeldColor => can != null ? can.ColorName : "No can";

        public void Configure(Camera camera, VanPaintSurface surface, VanPaintHud display, Transform left, Transform right)
        { view = camera; van = surface; hud = display; canHand = left; brushHand = right; }
        public void ConfigureFirstPerson(VanPaintMeshQuery query) { meshQuery = query; firstPerson = true; reach = 3.5f; }
        public void StowTools()
        {
            FinishStroke(); if (TextOpen) CloseText();
            if (can != null) can.ReturnToStand(); if (brush != null) brush.ReturnToStand();
            can = null; brush = null;
        }

        void Update()
        {
            var keyboard = Keyboard.current; var mouse = Mouse.current;
            if (keyboard == null || mouse == null || OnlyVolunteers.UI.OvMenuGate.Blocking) return; // W86 pause menu
            if (!mouse.leftButton.isPressed) strokeLimitedUntilRelease = false;
            if (TextOpen) return; // All gameplay shortcuts/paint/orbit suspended while typing.
            Ray ray = firstPerson ? new Ray(view.transform.position, view.transform.forward) : view.ScreenPointToRay(mouse.position.ReadValue());
            bool overUi = !firstPerson && hud != null && hud.BlocksPointer(mouse.position.ReadValue());
            if (!firstPerson && keyboard.bKey.wasPressedThisFrame && !overUi) PickUp(ray);
            if (keyboard.vKey.wasPressedThisFrame && !overUi) OpenText(ray);
            if (TextOpen) return;
            if (keyboard.zKey.wasPressedThisFrame) { FinishStroke(); van.UndoStroke(); Message = van.Status; }
            if (keyboard.deleteKey.wasPressedThisFrame)
            {
                FinishStroke();
                if (Time.unscaledTime < wipeUntil) { van.Wipe(); wipeUntil = 0; Message = van.Status; }
                else { wipeUntil = Time.unscaledTime + 3; Message = "Delete again within 3 seconds to wipe all paint."; }
            }
            if (keyboard.jKey.wasPressedThisFrame) { FinishStroke(); van.SavePaint(); Message = van.Status; }
            if (keyboard.lKey.wasPressedThisFrame) { FinishStroke(); van.LoadPaint(); Message = van.Status; }
            float scroll = mouse.scroll.ReadValue().y;
            if (!overUi && HasTools && Mathf.Abs(scroll) > .01f)
                brushRadius = Mathf.Clamp(brushRadius + Mathf.Sign(scroll) * .008f, .012f, .12f);
            if (!firstPerson && mouse.rightButton.isPressed && !overUi)
            {
                FinishStroke(); Vector2 delta = mouse.delta.ReadValue();
                view.transform.RotateAround(orbitCentre, Vector3.up, delta.x * .15f);
                Vector3 offset = view.transform.position - orbitCentre;
                float nextPitch = Mathf.Asin(offset.normalized.y) * Mathf.Rad2Deg - delta.y * .12f;
                nextPitch = Mathf.Clamp(nextPitch, 5, 60);
                float yaw = Mathf.Atan2(offset.x, offset.z);
                view.transform.position = orbitCentre + new Vector3(Mathf.Sin(yaw) * Mathf.Cos(nextPitch * Mathf.Deg2Rad), Mathf.Sin(nextPitch * Mathf.Deg2Rad), Mathf.Cos(yaw) * Mathf.Cos(nextPitch * Mathf.Deg2Rad)) * offset.magnitude;
                view.transform.LookAt(orbitCentre); return;
            }
            if (mouse.leftButton.isPressed && HasTools && !overUi) PaintAt(ray);
            else FinishStroke();
        }

        public bool PickUp(Ray ray)
        {
            FinishStroke();
            if (!Physics.Raycast(ray, out var hit, reach, ~0, QueryTriggerInteraction.Ignore) || !hit.collider.GetComponentInParent<VanPaintProp>()) return false;
            var prop = hit.collider.GetComponentInParent<VanPaintProp>();
            if (prop.IsBrush) { if (brush != null) brush.ReturnToStand(); brush = prop; prop.Hold(brushHand); }
            else { if (can != null) can.ReturnToStand(); can = prop; prop.Hold(canHand); }
            Message = HasTools ? "Ready. Hold LMB on the body to paint; V to write." :
                brush != null ? "Brush picked up. Now pick a can with B." : "Can picked up. Now pick the brush with B.";
            return true;
        }

        bool Hit(Ray ray, out Vector2 uv, out VanPaintSurface surface)
        {
            surface = null; uv = default;
            if (meshQuery != null) { surface = van; return meshQuery.TryHit(ray, reach, out uv); }
            if (!Physics.Raycast(ray, out var hit, reach)) return false;
            var target = hit.collider.GetComponent<VanPaintTarget>();
            if (target == null || !target.Accepts(hit.triangleIndex)) return false;
            surface = target.Surface; uv = hit.textureCoord; return true;
        }

        public bool PaintAt(Ray ray)
        {
            if (!HasTools || TextOpen || strokeLimitedUntilRelease || !Hit(ray, out var uv, out var surface)) { lastUv = null; return false; }
            if (activeStroke != surface)
            {
                FinishStroke();
                if (!surface.BeginStroke(CurrentColor)) { Message = surface.Status; return false; }
                activeStroke = surface;
            }
            Rect island = surface.Island(uv);
            Vector2 radius = surface.UvPerMetre(uv) * brushRadius;
            segment.Clear();
            if (lastUv.HasValue && island == lastIsland && Vector2.Distance(lastUv.Value, uv) < .12f)
            {
                float distance = Vector2.Distance(Vector2.Scale(uv - lastUv.Value, new Vector2(1 / radius.x, 1 / radius.y)), Vector2.zero);
                int steps = Mathf.Clamp(Mathf.CeilToInt(distance / .4f), 1, 256);
                if (distance < .1f) return true;
                for (int i = 1; i <= steps; i++) segment.Add(new PaintDab(Vector2.Lerp(lastUv.Value, uv, i / (float)steps), radius, island));
            }
            else segment.Add(new PaintDab(uv, radius, island));
            if (!surface.AddDabs(segment)) { FinishStroke(); strokeLimitedUntilRelease = true; Message = "Stroke limit reached; release LMB and continue."; return false; }
            lastUv = uv; lastIsland = island; return true;
        }

        public void FinishStroke() { if (activeStroke != null) activeStroke.EndStroke(); activeStroke = null; lastUv = null; }

        public bool OpenText(Ray ray)
        {
            FinishStroke();
            if (!HasTools || !Hit(ray, out textUv, out textSurface)) { Message = "Hold a brush and can; aim at the van body."; return false; }
            TextOpen = true; hud.ShowText(); TextModeChanged?.Invoke(true); return true;
        }

        public bool SubmitText(string text)
        {
            if (!TextOpen || textSurface == null) return false;
            if (!VanPaintLettering.Build(text, textUv, textSurface.UvPerMetre(textUv), brushRadius * 10,
                    textSurface.Island(textUv), out var dabs, out var error)) { Message = error; return false; }
            if (!textSurface.BeginStroke(CurrentColor, text.Trim().ToUpperInvariant())) { Message = textSurface.Status; return false; }
            if (!textSurface.AddDabs(dabs)) { textSurface.EndStroke(); Message = "Paint budget reached. Undo or wipe before lettering."; return false; }
            textSurface.EndStroke();
            Message = "Painted: " + text.Trim().ToUpperInvariant(); CloseText(); return true;
        }

        public void CloseText() { TextOpen = false; textSurface = null; hud.HideText(); TextModeChanged?.Invoke(false); }
        void OnDisable() { FinishStroke(); }
        void OnApplicationFocus(bool focus) { if (!focus) FinishStroke(); }
    }
}
