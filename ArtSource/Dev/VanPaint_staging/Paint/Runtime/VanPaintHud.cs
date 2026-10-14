using UnityEngine;
using UnityEngine.UIElements;

namespace OnlyVolunteers.Vehicles.Paint
{
    [RequireComponent(typeof(UIDocument))]
    public sealed class VanPaintHud : MonoBehaviour
    {
        [SerializeField] VanPaintInteractor input;
        [SerializeField] VanPaintSurface surface;
        VisualElement root, panel, textPanel, swatch;
        Label status, toolsLabel, size;
        TextField text;
        string lastMessage, lastStatus, lastHeld;
        float lastRadius = -1;
        int lastCount = -1;
        bool lastHasTools;
        public void Configure(VanPaintInteractor owner, VanPaintSurface van) { input = owner; surface = van; }
        void OnEnable()
        {
            root = GetComponent<UIDocument>().rootVisualElement;
            root.pickingMode = PickingMode.Ignore;
            panel = root.Q("hud"); textPanel = root.Q("text-panel");
            status = root.Q<Label>("status"); toolsLabel = root.Q<Label>("tools"); size = root.Q<Label>("size");
            text = root.Q<TextField>("lettering"); swatch = root.Q("swatch");
            root.Q<Button>("stamp").clicked += Stamp;
            root.Q<Button>("cancel").clicked += Cancel;
            text.RegisterCallback<KeyDownEvent>(OnTextKey, TrickleDown.TrickleDown);
            lastMessage = null;
            HideText();
        }
        void OnDisable()
        {
            if (root == null) return;
            root.Q<Button>("stamp").clicked -= Stamp; root.Q<Button>("cancel").clicked -= Cancel;
            text.UnregisterCallback<KeyDownEvent>(OnTextKey, TrickleDown.TrickleDown);
        }
        void Stamp() { input.SubmitText(text.value); }
        void Cancel() { input.CloseText(); }
        void OnTextKey(KeyDownEvent e)
        {
            if (e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) { Stamp(); e.StopPropagation(); }
            if (e.keyCode == KeyCode.Escape) { Cancel(); e.StopPropagation(); }
        }
        void Update()
        {
            if (input == null || status == null) return;
            if (lastMessage == input.Message && lastStatus == surface.Status && lastHeld == input.HeldColor &&
                lastRadius == input.BrushRadius && lastCount == surface.StrokeCount && lastHasTools == input.HasTools) return;
            lastMessage = input.Message; lastStatus = surface.Status; lastHeld = input.HeldColor;
            lastRadius = input.BrushRadius; lastCount = surface.StrokeCount; lastHasTools = input.HasTools;
            status.text = input.Message;
            toolsLabel.text = input.HasTools ? "BRUSH + " + input.HeldColor.ToUpperInvariant() : "PICK UP BRUSH + CAN  /  B";
            size.text = $"Brush {input.BrushRadius * 200:0.0} cm  ·  {surface.StrokeCount} strokes  ·  {surface.Status}";
            swatch.style.backgroundColor = input.CurrentColor;
        }
        public bool BlocksPointer(Vector2 screen)
        {
            if (root?.panel == null) return false;
            var position = RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(screen.x, Screen.height - screen.y));
            return panel.worldBound.Contains(position) || (input.TextOpen && textPanel.worldBound.Contains(position));
        }
        public void ShowText() { textPanel.style.display = DisplayStyle.Flex; text.schedule.Execute(() => { text.Focus(); text.SelectAll(); }); }
        public void HideText() { if (textPanel != null) textPanel.style.display = DisplayStyle.None; }
        public void SetShown(bool shown) { if (root != null) root.style.display = shown ? DisplayStyle.Flex : DisplayStyle.None; }
        public void SetMapHelp()
        {
            root.Q<Label>("save-help").text = "J  save  ·  L  load  ·  B away from tools  stow";
        }
    }
}
