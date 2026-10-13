using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace OnlyVolunteers.Clinic
{
    /// <summary>Field Clinic loop save, format version 1 (JsonUtility). Money, the ids of patients already paid for and the
    /// van's upgrade levels; no scene references and no C# type names in the file.</summary>
    [Serializable]
    public sealed class ClinicSaveData
    {
        public const int CurrentVersion = 1;

        public int version = CurrentVersion;
        public int money;
        public List<string> completedPatients = new();
        public int engineLevel;
        public int brakesLevel;
        public int handlingLevel;
        public string savedUtc = "";
    }

    // One JSON file in Application.persistentDataPath/OnlyVolunteers (outside the project). A save writes a temporary file
    // first and then replaces the old one, keeping it as .bak, so a crash mid-write never leaves only a broken file; a load
    // falls back to the .bak when the main file is missing or unreadable. Unknown newer versions are refused, not guessed.
    public static class ClinicSave
    {
        public const string FileName = "fc_loop_save_v1.json";

        public static string Folder => Path.Combine(Application.persistentDataPath, "OnlyVolunteers");
        public static string FilePath => Path.Combine(Folder, FileName);
        private static string BackupPath => FilePath + ".bak";
        private static string TempPath => FilePath + ".tmp";

        public static bool Write(ClinicSaveData data, out string error)
        {
            error = null;
            try
            {
                Directory.CreateDirectory(Folder);
                data.version = ClinicSaveData.CurrentVersion;
                data.savedUtc = DateTime.UtcNow.ToString("o");
                File.WriteAllText(TempPath, JsonUtility.ToJson(data, true));
                if (File.Exists(FilePath)) File.Replace(TempPath, FilePath, BackupPath);
                else File.Move(TempPath, FilePath);
                return true;
            }
            catch (Exception e)
            {
                error = e.Message;
                Debug.LogError($"[Clinic] save failed: {e.Message} ({FilePath})");
                return false;
            }
        }

        /// <summary>False when there is no usable save (a new game).</summary>
        public static bool TryRead(out ClinicSaveData data, out string note)
        {
            if (TryReadFile(FilePath, out data, out note)) return true;
            if (TryReadFile(BackupPath, out data, out string backupNote))
            {
                note = $"main save unusable ({note}); loaded the backup";
                return true;
            }
            data = null;
            return false;
        }

        private static bool TryReadFile(string path, out ClinicSaveData data, out string note)
        {
            data = null;
            note = "missing";
            try
            {
                if (!File.Exists(path)) return false;
                data = JsonUtility.FromJson<ClinicSaveData>(File.ReadAllText(path));
                if (data == null)
                {
                    note = "empty";
                    return false;
                }
                if (data.version < 1 || data.version > ClinicSaveData.CurrentVersion)
                {
                    note = $"unsupported version {data.version}";
                    data = null;
                    return false;
                }
                data.completedPatients ??= new List<string>();
                note = "ok";
                return true;
            }
            catch (Exception e)
            {
                note = e.Message;
                data = null;
                return false;
            }
        }
    }
}
