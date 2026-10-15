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
        public OnlyVolunteers.Operation.Stage1.OperationWorldState operation;
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

        public static bool Write(ClinicSaveData data, out string error) => WriteAt(FilePath, data, out error);

        // A separate dev-world slot uses the existing envelope/atomic writer, preserving the offline map save.
        // Automated runs (v01 -g25-probe, v02 -ops-test or a test hook) use their own slot and never touch the player's.
        public static string OperationFilePath => Path.Combine(Folder,
            !string.IsNullOrEmpty(OnlyVolunteers.Operation.Stage1.OperationTestHooks.SaveSlot) ? OnlyVolunteers.Operation.Stage1.OperationTestHooks.SaveSlot :
            System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-ops-test") >= 0 ? "operations_stage1_test_v02.json" :
            System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-g25-probe") >= 0 ? "operations_stage1_test_v01.json" : "operations_stage1_v01.json");
        public static bool WriteOperation(OnlyVolunteers.Operation.Stage1.OperationWorldState world, out string error) =>
            WriteAt(OperationFilePath, new ClinicSaveData { operation = world }, out error);
        public static bool TryReadOperation(out OnlyVolunteers.Operation.Stage1.OperationWorldState world, out string note)
        {
            world = null;
            if (!TryReadFile(OperationFilePath, out var data, out note) &&
                !TryReadFile(OperationFilePath + ".bak", out data, out note)) return false;
            world = data.operation;
            return world != null && world.patient != null && world.patient.organs != null && world.patient.organs.Length == 3;
        }

        private static bool WriteAt(string path, ClinicSaveData data, out string error)
        {
            error = null;
            try
            {
                Directory.CreateDirectory(Folder);
                data.version = ClinicSaveData.CurrentVersion;
                data.savedUtc = DateTime.UtcNow.ToString("o");
                string temporary = path + ".tmp";
                File.WriteAllText(temporary, JsonUtility.ToJson(data, true));
                if (File.Exists(path)) File.Replace(temporary, path, path + ".bak");
                else File.Move(temporary, path);
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
