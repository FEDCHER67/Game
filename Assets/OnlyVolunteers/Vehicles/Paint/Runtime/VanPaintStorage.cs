using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEngine;

namespace OnlyVolunteers.Vehicles.Paint
{
    public static class VanPaintStorage
    {
        public static string Folder(string vanId)
        {
            if (string.IsNullOrEmpty(vanId) || vanId.Length > 64 ||
                vanId.Any(c => !(c >= 'a' && c <= 'z') && !(c >= 'A' && c <= 'Z') && !(c >= '0' && c <= '9') && c != '-' && c != '_'))
                throw new ArgumentException("Van ID must be 1-64 ASCII letters, numbers, '-' or '_'.");
            return Path.Combine(Application.persistentDataPath, "VanPaint", vanId);
        }

        public static string Hash(byte[] bytes)
        {
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "");
        }

        // Immutable generations: publish JSON last; an interrupted PNG write is never selected.
        // No deletes or overwrite of earlier player saves. Retention is deliberately a later policy.
        public static string Save(VanPaintSave data, byte[] png)
        {
            string folder = Folder(data.vanId);
            Directory.CreateDirectory(folder);
            string generation = DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffffff") + "_" + Guid.NewGuid().ToString("N");
            data.pngFile = generation + ".png";
            data.pngSha256 = Hash(png);
            WriteNew(Path.Combine(folder, data.pngFile), png);
            string path = Path.Combine(folder, generation + ".json");
            WriteNew(path, System.Text.Encoding.UTF8.GetBytes(JsonUtility.ToJson(data, true)));
            return path;
        }

        static void WriteNew(string path, byte[] bytes)
        {
            using var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
            stream.Write(bytes, 0, bytes.Length);
            stream.Flush(true);
        }

        public static bool Load(string vanId, int resolution, out VanPaintSave data, out byte[] png)
        {
            data = null; png = null;
            string folder = Folder(vanId);
            if (!Directory.Exists(folder)) return false;
            foreach (string file in Directory.GetFiles(folder, "*.json").OrderByDescending(Path.GetFileName))
            {
                try
                {
                    if (new FileInfo(file).Length > 32000000) throw new InvalidDataException("Journal too large.");
                    var candidate = JsonUtility.FromJson<VanPaintSave>(File.ReadAllText(file));
                    if (candidate == null || candidate.version != 1 || candidate.vanId != vanId ||
                        candidate.resolution != resolution || candidate.strokes == null || candidate.strokes.Count > 256 ||
                        string.IsNullOrEmpty(candidate.pngFile) || Path.GetFileName(candidate.pngFile) != candidate.pngFile ||
                        Path.GetExtension(candidate.pngFile) != ".png")
                        throw new InvalidDataException("Unsupported paint save metadata.");
                    int count = 0;
                    foreach (var stroke in candidate.strokes)
                    {
                        if (!VanPaintSurface.Valid(stroke)) throw new InvalidDataException("Invalid stroke data.");
                        count += stroke.dabs.Count;
                    }
                    if (count > 100000) throw new InvalidDataException("Dab budget exceeded.");
                    string pngPath = Path.Combine(folder, candidate.pngFile);
                    if (new FileInfo(pngPath).Length > 16000000) throw new InvalidDataException("PNG too large.");
                    byte[] bytes = File.ReadAllBytes(pngPath);
                    if (Hash(bytes) != candidate.pngSha256) throw new InvalidDataException("PNG checksum mismatch.");
                    data = candidate; png = bytes; return true;
                }
                catch (Exception e) when (e is IOException || e is ArgumentException || e is UnauthorizedAccessException)
                { Debug.LogWarning("[VanPaint] Skipped incomplete/corrupt generation: " + e.Message); }
            }
            throw new InvalidDataException("No supported, complete paint generation found. Existing paint was preserved.");
        }
    }
}
