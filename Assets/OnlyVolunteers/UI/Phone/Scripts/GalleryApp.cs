using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    public sealed class GalleryApp : PhoneApp
    {
        private const int ThumbsPerFrame = 3;

        private readonly List<(RawImage cell, PhotoAlbum.Photo photo)> pending = new();
        private Texture2D full;

        private Text title;
        private Text subtitle;
        private RectTransform grid;
        private Text empty;
        private RectTransform viewer;
        private RawImage viewerImage;
        private AspectRatioFitter viewerFitter;
        private int builtVersion = -1;
        private int viewing = -1;

        public override string Title => "Gallery";
        public override string IconName => "app_gallery";

        protected override void Build(RectTransform root)
        {
            PhoneUi.Panel(root, "Background", PhoneUi.Hex("#111215")).rectTransform.Stretch();
            var scroll = PhoneUi.Scroll(root, "Photos", out var content);
            scroll.GetComponent<RectTransform>().Stretch(0, PhoneLayout.HeaderHeight, 0, 30);
            grid = PhoneUi.Rect("Grid", content);
            var layout = grid.gameObject.AddComponent<GridLayoutGroup>();
            layout.cellSize = new Vector2(122, 122f * CameraApp.PhotoHeight / CameraApp.PhotoWidth);
            layout.spacing = new Vector2(4, 4);
            layout.padding = new RectOffset(4, 4, 6, 6);
            layout.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
            layout.constraintCount = 3;
            layout.childAlignment = TextAnchor.UpperCenter;

            empty = PhoneUi.Label(root, "No photos yet.\nOpen Camera and press LMB.", 17,
                new Color(1, 1, 1, 0.6f), TextAnchor.MiddleCenter);
            empty.rectTransform.Place(new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(320, 80));

            viewer = PhoneUi.Panel(root, "Viewer", Color.black).rectTransform.Stretch(0, PhoneLayout.HeaderHeight, 0, 0);
            var area = PhoneUi.Rect("Area", viewer).Stretch(0, 0, 0, 84);
            viewerImage = PhoneUi.Rect("Photo", area).gameObject.AddComponent<RawImage>();
            viewerImage.raycastTarget = false;
            viewerFitter = viewerImage.gameObject.AddComponent<AspectRatioFitter>();
            viewerFitter.aspectMode = AspectRatioFitter.AspectMode.FitInParent;
            var previous = PhoneUi.TextButton(viewer, "‹", new Color(1, 1, 1, 0.12f), Color.white, 30, 24,
                () => Step(-1));
            ((RectTransform)previous.transform).Place(new Vector2(0, 0), new Vector2(50, 46), new Vector2(64, 48));
            var next = PhoneUi.TextButton(viewer, "›", new Color(1, 1, 1, 0.12f), Color.white, 30, 24,
                () => Step(1));
            ((RectTransform)next.transform).Place(new Vector2(1, 0), new Vector2(-50, 46), new Vector2(64, 48));
            var delete = PhoneUi.TextButton(viewer, "Delete", PhoneUi.Hex("#E5383B"), Color.white, 16, 24,
                DeleteCurrent);
            ((RectTransform)delete.transform).Place(new Vector2(0.5f, 0), new Vector2(0, 46), new Vector2(130, 48));
            viewer.gameObject.SetActive(false);

            title = PhoneUi.Header(root, Title, PhoneUi.Hex("#1C1E22"), out subtitle, Phone.Back);
        }

        public override void Show()
        {
            base.Show();
            if (builtVersion != Phone.Album.Version)
                RebuildGrid();
            CloseViewer();
        }

        private void RebuildGrid()
        {
            builtVersion = Phone.Album.Version;
            PhoneUi.Clear(grid);
            pending.Clear();
            var photos = Phone.Album.Photos;
            for (int i = 0; i < photos.Count; i++)
            {
                int index = i;
                var cell = PhoneUi.Rect("Photo", grid).gameObject.AddComponent<RawImage>();
                cell.texture = photos[i].Thumb;
                cell.color = photos[i].Thumb != null ? Color.white : PhoneUi.Hex("#2B2D33");
                if (photos[i].Thumb == null)
                    pending.Add((cell, photos[i]));
                var button = cell.gameObject.AddComponent<Button>();
                button.targetGraphic = cell;
                button.onClick.AddListener(() => OpenViewer(index));
            }
            empty.enabled = photos.Count == 0;
            subtitle.text = Count(photos.Count);
        }

        private static string Count(int count) => count + " / " + PhotoAlbum.MaxPhotos + " photos · oldest are replaced";

        // Thumbnails decode a few per frame, so opening a full gallery does not freeze the game.
        public override void Tick()
        {
            for (int i = 0; i < ThumbsPerFrame && pending.Count > 0; i++)
            {
                var (cell, photo) = pending[0];
                pending.RemoveAt(0);
                if (cell == null)
                    continue;
                cell.texture = Phone.Album.Thumbnail(photo);
                cell.color = Color.white;
            }
        }

        private void OpenViewer(int index)
        {
            var photos = Phone.Album.Photos;
            if (photos.Count == 0)
            {
                CloseViewer();
                return;
            }
            viewing = Mathf.Clamp(index, 0, photos.Count - 1);
            var photo = photos[viewing];
            ReleaseFull();
            full = Phone.Album.LoadFull(photo);
            viewerImage.texture = full;
            if (full != null)
                viewerFitter.aspectRatio = full.width / (float)full.height;
            viewer.gameObject.SetActive(true);
            title.text = photo.Taken.ToString("d MMM, HH:mm", CultureInfo.InvariantCulture);
            subtitle.text = (viewing + 1) + " of " + photos.Count;
        }

        private void ReleaseFull()
        {
            if (full != null)
                Object.Destroy(full);
            full = null;
        }

        public override void Hide()
        {
            base.Hide();
            ReleaseFull();
        }

        private void CloseViewer()
        {
            ReleaseFull();
            viewing = -1;
            viewer.gameObject.SetActive(false);
            title.text = Title;
            subtitle.text = Count(Phone.Album.Photos.Count);
        }

        private void Step(int direction)
        {
            int count = Phone.Album.Photos.Count;
            if (count > 0)
                OpenViewer((viewing + direction + count) % count);
        }

        private void DeleteCurrent()
        {
            var photos = Phone.Album.Photos;
            if (viewing < 0 || viewing >= photos.Count)
                return;
            Phone.Album.Delete(photos[viewing]);
            RebuildGrid();
            if (photos.Count == 0)
                CloseViewer();
            else
                OpenViewer(Mathf.Min(viewing, photos.Count - 1));
            Phone.Toast("Deleted");
        }

        public override bool Back()
        {
            if (viewing < 0)
                return false;
            CloseViewer();
            return true;
        }
    }
}
