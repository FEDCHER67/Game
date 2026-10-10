using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEngine;
using Debug = UnityEngine.Debug;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Phone
{
    // Photos of the current session only: JPG files in persistentDataPath/Photos/<process id>.
    // Every new start begins with an empty gallery; at most MaxPhotos are kept, the oldest are deleted.
    // The per-process folder keeps two local test instances from wiping each other's photos.
    public sealed class PhotoAlbum
    {
        public const int MaxPhotos = 200;
        private const int ThumbWidth = 140;
        private const int ThumbHeight = 240;

        public sealed class Photo
        {
            public string Path;
            public DateTime Taken;
            public RenderTexture Thumb;
        }

        private readonly List<Photo> photos = new();
        private readonly string root = Path.Combine(Application.persistentDataPath, "Photos");

        public string Folder { get; }
        public int Version { get; private set; }
        public IReadOnlyList<Photo> Photos => photos;

        public PhotoAlbum()
        {
            string self = Process.GetCurrentProcess().Id.ToString();
            Folder = Path.Combine(root, self);
            try
            {
                if (!Directory.Exists(root))
                    return;
                foreach (string file in Directory.GetFiles(root, "IMG_*.jpg"))
                    File.Delete(file); // photos from the first phone version
                foreach (string folder in Directory.GetDirectories(root))
                {
                    string name = Path.GetFileName(folder);
                    if (name == self || !IsRunning(name))
                        Directory.Delete(folder, true);
                }
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[Phone] old photos not cleared: " + exception.Message);
            }
        }

        private static bool IsRunning(string processId)
        {
            if (!int.TryParse(processId, out int id))
                return false;
            try
            {
                using var process = Process.GetProcessById(id);
                return !process.HasExited;
            }
            catch (Exception)
            {
                return false;
            }
        }

        private void Trim()
        {
            while (photos.Count > MaxPhotos)
                Delete(photos[photos.Count - 1]);
        }

        // Saves the shot, makes its thumbnail and releases the full-size texture.
        public Photo Save(Texture2D texture)
        {
            var now = DateTime.Now;
            var photo = new Photo { Path = Path.Combine(Folder, $"IMG_{now:yyyyMMdd_HHmmss_fff}.jpg"), Taken = now };
            try
            {
                Directory.CreateDirectory(Folder);
                File.WriteAllBytes(photo.Path, texture.EncodeToJPG(90));
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[Phone] photo not saved: " + exception.Message);
            }
            photo.Thumb = MakeThumb(texture);
            Object.Destroy(texture);
            photos.Insert(0, photo);
            Trim();
            Version++;
            return photo;
        }

        public Texture Thumbnail(Photo photo)
        {
            if (photo.Thumb != null)
                return photo.Thumb;
            var full = LoadFull(photo);
            if (full == null)
                return null;
            photo.Thumb = MakeThumb(full);
            Object.Destroy(full);
            return photo.Thumb;
        }

        private static RenderTexture MakeThumb(Texture source)
        {
            var thumb = new RenderTexture(ThumbWidth, ThumbHeight, 0, RenderTextureFormat.ARGB32,
                RenderTextureReadWrite.sRGB) { name = "PhotoThumb" };
            Graphics.Blit(source, thumb);
            return thumb;
        }

        // Full-size image for the viewer; the caller destroys it.
        public Texture2D LoadFull(Photo photo)
        {
            try
            {
                var texture = new Texture2D(2, 2, TextureFormat.RGB24, false) { name = "Photo" };
                texture.LoadImage(File.ReadAllBytes(photo.Path), true);
                return texture;
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[Phone] photo not loaded: " + exception.Message);
                return null;
            }
        }

        public void Delete(Photo photo)
        {
            try
            {
                if (File.Exists(photo.Path))
                    File.Delete(photo.Path);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[Phone] photo not deleted: " + exception.Message);
            }
            if (photo.Thumb != null)
            {
                photo.Thumb.Release();
                Object.Destroy(photo.Thumb);
            }
            photos.Remove(photo);
            Version++;
        }

        public void Dispose()
        {
            foreach (var photo in photos)
                if (photo.Thumb != null)
                {
                    photo.Thumb.Release();
                    Object.Destroy(photo.Thumb);
                }
            try
            {
                if (Directory.Exists(Folder))
                    Directory.Delete(Folder, true);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[Phone] session photos not cleared: " + exception.Message);
            }
        }
    }
}
