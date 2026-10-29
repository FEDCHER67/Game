using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>What a save file on disk is, before anything of it is applied to the world.</summary>
    public enum SaveFileStatus : byte
    {
        /// <summary>No file: a new game.</summary>
        Missing,
        /// <summary>Parses and its version is one this build reads.</summary>
        Valid,
        /// <summary>Written by a newer build (version above CaptureSaveData.CurrentVersion): never loaded, never overwritten.</summary>
        Newer,
        /// <summary>Below CaptureSaveData.OldestLoadableVersion.</summary>
        TooOld,
        /// <summary>Empty, truncated, not JSON or without a version.</summary>
        Corrupt,
    }

    /// <summary>The result of reading one save file without touching the world (WP01).</summary>
    public sealed class SaveFileProbe
    {
        public string Path = "";
        public SaveFileStatus Status;
        /// <summary>The version written in the file (0 when it could not be read).</summary>
        public int Version;
        /// <summary>CaptureSaveData.savedUtc as written ("" when unknown).</summary>
        public string SavedUtc = "";
        public string Error = "";
        /// <summary>The parsed save when Status is Valid, else null.</summary>
        public CaptureSaveData Data;
        public bool Loadable => Status == SaveFileStatus.Valid && Data != null;

        /// <summary>The save time for the player (local clock), or the file time when the save carries none.</summary>
        public string WhenText()
        {
            DateTime when;
            if (!DateTime.TryParse(SavedUtc, null, System.Globalization.DateTimeStyles.RoundtripKind, out when))
            {
                try { when = File.GetLastWriteTimeUtc(Path); }
                catch (Exception) { return "время неизвестно"; }
            }
            return when.ToLocalTime().ToString("dd.MM.yyyy HH:mm");
        }
    }

    /// <summary>Save files on disk (WP01, SAVE_PROGRESS v01 §2 / §7, SV-04, SV-13). One place that decides whether a
    /// file may be loaded and how it is written:
    /// - <see cref="Probe"/> reads a file without applying it: Valid / Newer / TooOld / Corrupt / Missing.
    /// - <see cref="Write"/> checks the new text first, replaces atomically (tmp → File.Replace), then keeps
    ///   <see cref="BackupCount"/> rotating backups (path.bak newest, path.bak2, path.bak3 oldest) and never writes over a
    ///   file of a newer version. A failed write leaves the previous file and the backups as they were and throws (no false
    ///   "saved").
    /// - A file that failed to load is never written, renamed or deleted here: the player's way out is a NEW file next to
    ///   it (a copy of a backup, or an empty new game), chosen through a one-line pointer file "base.active". Five worlds
    ///   / slots are WP07; this pointer is only the minimal escape so the bad file stays untouched.</summary>
    public static class CaptureSaveStore
    {
        /// <summary>Rotating backups kept before every successful write (SAVE §2: three past versions).</summary>
        public const int BackupCount = 3;
        public const string PointerSuffix = ".active";

        [Serializable]
        private sealed class VersionOnly
        {
            public int version = int.MinValue;
            public string savedUtc = "";
        }

        /// <summary>Backup n (1 = newest): path.bak, path.bak2, path.bak3. ".bak" is also what the old single-backup code wrote.</summary>
        public static string BackupPath(string path, int index) => index <= 1 ? path + ".bak" : path + ".bak" + index;

        public static string PointerPath(string basePath) => basePath + PointerSuffix;

        /// <summary>The file this game reads and writes: the base path, or the sibling named in base.active (written when
        /// the player chose a way out of a save that would not load). A pointer to a missing file is still the active
        /// file (a new game not saved yet).</summary>
        public static string ResolveActive(string basePath)
        {
            string pointer = PointerPath(basePath);
            try
            {
                if (!File.Exists(pointer)) return basePath;
                string name = File.ReadAllText(pointer).Trim();
                if (!IsPlainFileName(name)) return basePath;
                return System.IO.Path.Combine(System.IO.Path.GetDirectoryName(basePath) ?? "", name);
            }
            catch (Exception) { return basePath; }
        }

        private static bool IsPlainFileName(string name) =>
            !string.IsNullOrEmpty(name) && name.EndsWith(".json", StringComparison.OrdinalIgnoreCase)
            && name.IndexOfAny(System.IO.Path.GetInvalidFileNameChars()) < 0 && name.IndexOf("..", StringComparison.Ordinal) < 0;

        // ---------- reading ----------

        public static SaveFileProbe Probe(string path)
        {
            var probe = new SaveFileProbe { Path = path ?? "" };
            if (string.IsNullOrEmpty(path) || !File.Exists(path)) { probe.Status = SaveFileStatus.Missing; return probe; }
            string text;
            try { text = File.ReadAllText(path); }
            catch (Exception e) { probe.Status = SaveFileStatus.Corrupt; probe.Error = e.Message; return probe; }
            return ProbeText(text, probe);
        }

        /// <summary>The same checks on text (the write checks its own output with it before replacing anything).</summary>
        public static SaveFileProbe ProbeText(string text, SaveFileProbe probe = null)
        {
            probe ??= new SaveFileProbe();
            string trimmed = text != null ? text.Trim() : "";
            if (trimmed.Length == 0) return Bad(probe, "пустой файл");
            // JsonUtility is lenient with a cut-off tail: a whole file is one JSON object, first '{' to last '}'.
            if (trimmed[0] != '{' || trimmed[trimmed.Length - 1] != '}') return Bad(probe, "файл обрезан или это не JSON");
            VersionOnly head;
            try { head = JsonUtility.FromJson<VersionOnly>(trimmed); }
            catch (Exception e) { return Bad(probe, e.Message); }
            if (head == null || head.version == int.MinValue) return Bad(probe, "нет номера версии");
            probe.Version = head.version;
            probe.SavedUtc = head.savedUtc ?? "";
            if (head.version > CaptureSaveData.CurrentVersion) { probe.Status = SaveFileStatus.Newer; return probe; }
            if (head.version < CaptureSaveData.OldestLoadableVersion) { probe.Status = SaveFileStatus.TooOld; return probe; }
            CaptureSaveData data;
            try { data = JsonUtility.FromJson<CaptureSaveData>(trimmed); }
            catch (Exception e) { return Bad(probe, e.Message); }
            if (data == null) return Bad(probe, "пустые данные");
            probe.Data = data;
            probe.Status = SaveFileStatus.Valid;
            return probe;
        }

        private static SaveFileProbe Bad(SaveFileProbe probe, string error)
        {
            probe.Status = SaveFileStatus.Corrupt;
            probe.Error = error ?? "";
            probe.Data = null;
            return probe;
        }

        /// <summary>The backups of one file that exist, newest first (whatever their state).</summary>
        public static List<SaveFileProbe> Backups(string path)
        {
            var list = new List<SaveFileProbe>();
            for (int i = 1; i <= BackupCount; i++)
            {
                string b = BackupPath(path, i);
                if (File.Exists(b)) list.Add(Probe(b));
            }
            return list;
        }

        /// <summary>The newest backup this build can load, or null.</summary>
        public static SaveFileProbe NewestValidBackup(string path)
        {
            foreach (var b in Backups(path)) if (b.Loadable) return b;
            return null;
        }

        // ---------- writing ----------

        /// <summary>Writes <paramref name="json"/> to <paramref name="path"/>: the text is checked first (it must probe
        /// Valid), then it replaces the current file atomically (tmp → File.Replace, the old file kept as a staged copy) and
        /// only after that success the backups move down one place: staged → path.bak, .bak → .bak2, .bak2 → .bak3 (the
        /// oldest drops). Refuses (throws) to replace a file of a newer version or one it cannot read. Any failure throws,
        /// leaves the current file and the backups as they were and removes the temporary file.</summary>
        public static void Write(string path, string json)
        {
            if (string.IsNullOrEmpty(path)) throw new ArgumentException("no save path");
            var check = ProbeText(json);
            if (!check.Loadable) throw new InvalidDataException("the new save text does not verify: " + check.Status + " " + check.Error);
            string dir = System.IO.Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            string tmp = path + ".tmp";
            string staged = StagedBackupPath(path);
            try
            {
                File.WriteAllText(tmp, json);
                if (File.Exists(path))
                {
                    int onDisk = VersionOnDisk(path);
                    if (onDisk > CaptureSaveData.CurrentVersion)
                        throw new IOException($"the save on disk is version {onDisk} (newer than {CaptureSaveData.CurrentVersion}): not overwritten");
                    if (File.Exists(staged)) RotateIn(path, staged); // left by a write interrupted between replace and rotation
                    File.Replace(tmp, path, staged);
                    RotateIn(path, staged);
                }
                else File.Move(tmp, path);
            }
            finally
            {
                try { if (File.Exists(tmp)) File.Delete(tmp); } catch (Exception) { }
            }
        }

        /// <summary>Where File.Replace puts the previous file before it becomes backup 1.</summary>
        public static string StagedBackupPath(string path) => path + ".bak0";

        private static void RotateIn(string path, string staged)
        {
            for (int i = BackupCount; i >= 2; i--)
            {
                string from = BackupPath(path, i - 1), to = BackupPath(path, i);
                if (!File.Exists(from)) continue;
                if (File.Exists(to)) File.Delete(to);
                File.Move(from, to);
            }
            File.Move(staged, BackupPath(path, 1));
        }

        /// <summary>The version field of a file on disk (int.MinValue when it has none or is not JSON). A file that cannot
        /// be read at all throws: nothing is written over a file that could not be checked.</summary>
        private static int VersionOnDisk(string path)
        {
            string text = File.ReadAllText(path);
            try
            {
                var head = JsonUtility.FromJson<VersionOnly>(text);
                return head != null ? head.version : int.MinValue;
            }
            catch (Exception) { return int.MinValue; }
        }

        /// <summary>A normal "new game" (Shift+K): the active file and its backups go. Never used on a file that failed to
        /// load (that one is left alone; see <see cref="StartNewFile"/>).</summary>
        public static void DeleteWithBackups(string path)
        {
            if (File.Exists(path)) File.Delete(path);
            if (File.Exists(StagedBackupPath(path))) File.Delete(StagedBackupPath(path));
            for (int i = 1; i <= BackupCount; i++)
            {
                string b = BackupPath(path, i);
                if (File.Exists(b)) File.Delete(b);
            }
        }

        // ---------- the way out of a save that would not load ----------

        /// <summary>A free sibling name: base stem + "_" + tag + "_" + UTC stamp (+ counter) + ".json".</summary>
        public static string NewSiblingPath(string basePath, string tag, DateTime utc)
        {
            string dir = System.IO.Path.GetDirectoryName(basePath) ?? "";
            string stem = System.IO.Path.GetFileNameWithoutExtension(basePath);
            string stamp = utc.ToString("yyyyMMdd-HHmmss");
            for (int n = 0; n < 1000; n++)
            {
                string name = stem + "_" + tag + "_" + stamp + (n > 0 ? "-" + n : "") + ".json";
                string candidate = System.IO.Path.Combine(dir, name);
                if (!File.Exists(candidate) && !File.Exists(BackupPath(candidate, 1))) return candidate;
            }
            throw new IOException("no free save file name next to " + basePath);
        }

        /// <summary>"New game in a new file": points the game at a fresh sibling (created by its first save). Writes only
        /// the pointer; the failed file and its backups are not touched.</summary>
        public static string StartNewFile(string basePath, DateTime utc)
        {
            string path = NewSiblingPath(basePath, "new", utc);
            WritePointer(basePath, path);
            return path;
        }

        /// <summary>"Load the newest valid backup": copies that backup byte for byte into a fresh sibling and points the game
        /// at it. The failed file and its backups are not touched (the copy is what the game writes from now on).</summary>
        public static string RestoreBackupToNewFile(string basePath, string backupPath, DateTime utc)
        {
            if (!Probe(backupPath).Loadable) throw new InvalidDataException("the backup does not load: " + backupPath);
            string path = NewSiblingPath(basePath, "restored", utc);
            File.Copy(backupPath, path, false);
            WritePointer(basePath, path);
            return path;
        }

        private static void WritePointer(string basePath, string activePath)
        {
            string dir = System.IO.Path.GetDirectoryName(basePath);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            string pointer = PointerPath(basePath), tmp = pointer + ".tmp";
            File.WriteAllText(tmp, System.IO.Path.GetFileName(activePath));
            if (File.Exists(pointer)) File.Delete(pointer);
            File.Move(tmp, pointer);
        }

        /// <summary>The player-facing reason a probe cannot be loaded (Russian HUD text).</summary>
        public static string Explain(SaveFileProbe probe)
        {
            if (probe == null) return "Сохранение не читается.";
            switch (probe.Status)
            {
                case SaveFileStatus.Newer:
                    return $"Сохранение сделано более новой версией игры (формат v{probe.Version}, эта версия понимает до v{CaptureSaveData.CurrentVersion}).";
                case SaveFileStatus.TooOld:
                    return $"Сохранение слишком старого формата (v{probe.Version}).";
                case SaveFileStatus.Corrupt:
                    return "Сохранение повреждено и не читается" + (string.IsNullOrEmpty(probe.Error) ? "." : $" ({Short(probe.Error)}).");
                default:
                    return "Сохранение не загрузилось" + (string.IsNullOrEmpty(probe.Error) ? "." : $" ({Short(probe.Error)}).");
            }
        }

        private static string Short(string s)
        {
            s = (s ?? "").Replace('\n', ' ').Replace('\r', ' ').Trim();
            return s.Length > 90 ? s.Substring(0, 90) + "…" : s;
        }
    }
}
