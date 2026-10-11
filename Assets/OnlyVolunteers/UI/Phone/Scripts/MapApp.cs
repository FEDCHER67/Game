using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // Live top-down view around the player, north up, zoom with the mouse wheel.
    // Renders only while the app is visible.
    public sealed class MapApp : PhoneApp
    {
        private const int MapWidth = 560;
        private const int MapHeight = 1086; // 560 x 1086 matches the 392 x 760 view
        private const float MinZoom = 12f;
        private const float MaxZoom = 140f;

        private Camera rig;
        private RenderTexture target;
        private RawImage view;
        private RectTransform marker;
        private float zoom = 38f;

        public override string Title => "Map";
        public override string IconName => "app_map";

        protected override void Build(RectTransform root)
        {
            PhoneUi.Panel(root, "Background", PhoneUi.Hex("#23302A")).rectTransform.Stretch();
            view = PhoneUi.Rect("View", root).gameObject.AddComponent<RawImage>();
            view.raycastTarget = false;
            view.rectTransform.Stretch(0, PhoneLayout.HeaderHeight, 0, 0);

            var outline = PhoneUi.Picture(view.transform, "MarkerOutline", PhoneUi.Arrow, Color.white);
            marker = outline.rectTransform.Place(new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(40, 40));
            PhoneUi.Picture(marker, "Marker", PhoneUi.Arrow, PhoneUi.Hex("#FF7A30")).rectTransform
                .Place(new Vector2(0.5f, 0.5f), new Vector2(0, 1), new Vector2(28, 28));

            PhoneUi.Header(root, Title, PhoneUi.Hex("#2E9C8E"), out _, Phone.Back);
        }

        private void Zoom(float factor) => zoom = Mathf.Clamp(zoom * factor, MinZoom, MaxZoom);

        private void EnsureRig()
        {
            if (rig != null || Phone.ViewCamera == null)
                return;
            target = new RenderTexture(MapWidth, MapHeight, 24, RenderTextureFormat.ARGB32,
                RenderTextureReadWrite.sRGB) { name = "PhoneMap" };
            rig = new GameObject("PhoneMapCamera").AddComponent<Camera>();
            rig.orthographic = true;
            rig.orthographicSize = zoom;
            rig.clearFlags = CameraClearFlags.SolidColor;
            rig.backgroundColor = PhoneUi.Hex("#23302A");
            rig.nearClipPlane = 0.3f;
            rig.farClipPlane = 600f;
            rig.cullingMask = Phone.ViewCamera.cullingMask;
            rig.targetTexture = target;
            rig.depth = Phone.ViewCamera.depth - 2f;
            var data = rig.GetUniversalAdditionalCameraData();
            data.renderShadows = false;
            data.renderPostProcessing = false;
            view.texture = target;
        }

        public override void Show()
        {
            base.Show();
            EnsureRig();
            if (rig != null)
            {
                Follow();
                rig.enabled = true;
            }
        }

        public override void Hide()
        {
            base.Hide();
            if (rig != null)
                rig.enabled = false;
        }

        public override void Tick()
        {
            float wheel = Input.mouseScrollDelta.y;
            if (wheel != 0f)
                Zoom(Mathf.Pow(0.85f, wheel));
            Follow();
        }

        private void Follow()
        {
            if (rig == null)
                return;
            Transform eye = Phone.ViewCamera.transform;
            Vector3 position = eye.position;
            rig.transform.SetPositionAndRotation(position + Vector3.up * 200f, Quaternion.Euler(90f, 0f, 0f));
            rig.orthographicSize = Mathf.Lerp(rig.orthographicSize, zoom, 1f - Mathf.Exp(-12f * Time.unscaledDeltaTime));
            marker.localRotation = Quaternion.Euler(0, 0, -eye.eulerAngles.y);
        }

        public override void Dispose()
        {
            if (rig != null)
                Object.Destroy(rig.gameObject);
            if (target != null)
            {
                target.Release();
                Object.Destroy(target);
            }
        }
    }
}
