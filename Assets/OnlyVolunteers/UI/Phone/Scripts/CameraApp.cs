using System.Collections;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // Viewfinder from a second camera on the player's eyes; LMB saves what it sees to the album.
    public sealed class CameraApp : PhoneApp
    {
        public const int PhotoWidth = 612;
        public const int PhotoHeight = 1048;
        private const float PhoneFieldOfView = 66f;

        private Camera rig;
        private RenderTexture target;
        private RawImage viewfinder;
        private Image flash;
        private RawImage thumbnail;
        private RectTransform shutter;
        private float flashAlpha;
        private float pulse;
        private bool capturing;

        public override string Title => "Camera";
        public override string IconName => "app_camera";
        public override bool WantsLook => true;

        protected override void Build(RectTransform root)
        {
            PhoneUi.Panel(root, "Background", Color.black).rectTransform.Stretch();
            float height = PhoneLayout.Width * PhotoHeight / PhotoWidth;
            viewfinder = PhoneUi.Rect("Viewfinder", root).gameObject.AddComponent<RawImage>();
            viewfinder.raycastTarget = false;
            viewfinder.rectTransform.Top(PhoneLayout.StatusHeight, height);
            flash = PhoneUi.Panel(viewfinder.transform, "Flash", new Color(1, 1, 1, 0));
            flash.rectTransform.Stretch();

            // Thirds grid, like every phone camera.
            for (int i = 1; i <= 2; i++)
            {
                var vertical = PhoneUi.Panel(viewfinder.transform, "GridV", new Color(1, 1, 1, 0.18f)).rectTransform;
                vertical.anchorMin = new Vector2(i / 3f, 0);
                vertical.anchorMax = new Vector2(i / 3f, 1);
                vertical.sizeDelta = new Vector2(1, 0);
                var horizontal = PhoneUi.Panel(viewfinder.transform, "GridH", new Color(1, 1, 1, 0.18f)).rectTransform;
                horizontal.anchorMin = new Vector2(0, i / 3f);
                horizontal.anchorMax = new Vector2(1, i / 3f);
                horizontal.sizeDelta = new Vector2(0, 1);
            }

            var mode = PhoneUi.Panel(viewfinder.transform, "ModePill", new Color(0, 0, 0, 0.45f), 13);
            mode.rectTransform.Place(new Vector2(0.5f, 1), new Vector2(0, -26), new Vector2(86, 26));
            PhoneUi.Label(mode.transform, "PHOTO", 13, PhoneUi.Hex("#FFC23D"), TextAnchor.MiddleCenter, true)
                .rectTransform.Stretch();
            PhoneUi.Label(viewfinder.transform, "1×", 14, Color.white, TextAnchor.MiddleCenter, true)
                .rectTransform.Place(new Vector2(0.5f, 0), new Vector2(0, 22), new Vector2(40, 24));

            var controls = PhoneUi.Rect("Controls", root).Stretch(0, PhoneLayout.StatusHeight + height, 0, 0);
            var ring = PhoneUi.Panel(controls, "Shutter", Color.white);
            ring.sprite = PhoneUi.Circle;
            shutter = ring.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0, 6), new Vector2(74, 74));
            var gap = PhoneUi.Panel(shutter, "Gap", Color.black);
            gap.sprite = PhoneUi.Circle;
            gap.rectTransform.Stretch(5, 5, 5, 5);
            var core = PhoneUi.Panel(shutter, "Core", Color.white);
            core.sprite = PhoneUi.Circle;
            core.rectTransform.Stretch(9, 9, 9, 9);

            var frame = PhoneUi.Panel(controls, "Thumb", PhoneUi.Hex("#2B2D33"), 12);
            frame.rectTransform.Place(new Vector2(0, 0.5f), new Vector2(64, 6), new Vector2(54, 54));
            frame.gameObject.AddComponent<Mask>();
            thumbnail = PhoneUi.Rect("Image", frame.transform).gameObject.AddComponent<RawImage>();
            thumbnail.raycastTarget = false;
            thumbnail.rectTransform.Stretch();
            thumbnail.enabled = false;

            PhoneUi.Label(controls, "LMB", 13, new Color(1, 1, 1, 0.6f), TextAnchor.MiddleCenter, true)
                .rectTransform.Place(new Vector2(1, 0.5f), new Vector2(-64, 6), new Vector2(60, 24));
        }

        private void EnsureRig()
        {
            if (rig != null || Phone.ViewCamera == null)
                return;
            target = new RenderTexture(PhotoWidth, PhotoHeight, 24, RenderTextureFormat.ARGB32,
                RenderTextureReadWrite.sRGB) { name = "PhoneViewfinder" };
            var go = new GameObject("PhoneCamera");
            go.transform.SetParent(Phone.ViewCamera.transform, false);
            rig = go.AddComponent<Camera>();
            rig.CopyFrom(Phone.ViewCamera);
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
            rig.fieldOfView = PhoneFieldOfView;
            rig.targetTexture = target;
            rig.depth = Phone.ViewCamera.depth - 1f;
            var source = Phone.ViewCamera.GetUniversalAdditionalCameraData();
            var data = rig.GetUniversalAdditionalCameraData();
            data.renderPostProcessing = source.renderPostProcessing;
            data.antialiasing = source.antialiasing;
            data.renderShadows = source.renderShadows;
            viewfinder.texture = target;
        }

        public override void Show()
        {
            base.Show();
            EnsureRig();
            if (rig != null)
                rig.enabled = true;
            var photos = Phone.Album.Photos;
            SetThumbnail(photos.Count > 0 ? Phone.Album.Thumbnail(photos[0]) : null);
        }

        public override void Hide()
        {
            base.Hide();
            if (rig != null)
                rig.enabled = false;
        }

        public override void Primary()
        {
            if (!capturing && rig != null)
                Phone.StartCoroutine(Capture());
        }

        private IEnumerator Capture()
        {
            capturing = true;
            yield return new WaitForEndOfFrame();
            var previous = RenderTexture.active;
            RenderTexture.active = target;
            var photo = new Texture2D(PhotoWidth, PhotoHeight, TextureFormat.RGB24, false) { name = "Photo" };
            photo.ReadPixels(new Rect(0, 0, PhotoWidth, PhotoHeight), 0, 0);
            photo.Apply();
            RenderTexture.active = previous;
            var saved = Phone.Album.Save(photo);
            Phone.PlayShutter();
            SetThumbnail(saved.Thumb);
            flashAlpha = 1f;
            pulse = 1f;
            Phone.Toast("Saved to Gallery");
            capturing = false;
        }

        private void SetThumbnail(Texture texture)
        {
            thumbnail.texture = texture;
            thumbnail.enabled = texture != null;
            if (texture == null)
                return;
            // Centre-crop the portrait photo into the square frame.
            float aspect = texture.width / (float)texture.height;
            thumbnail.uvRect = new Rect(0, (1 - aspect) * 0.5f, 1, aspect);
        }

        public override void Tick()
        {
            float dt = Time.unscaledDeltaTime;
            flashAlpha = Mathf.MoveTowards(flashAlpha, 0f, dt * 4f);
            flash.color = new Color(1, 1, 1, flashAlpha * 0.9f);
            pulse = Mathf.MoveTowards(pulse, 0f, dt * 6f);
            shutter.localScale = Vector3.one * (1f - 0.12f * Mathf.Sin(pulse * Mathf.PI));
        }

        public override void Dispose()
        {
            if (rig != null)
                Object.Destroy(rig.gameObject);
            if (target != null)
                target.Release();
            if (target != null)
                Object.Destroy(target);
        }
    }
}
