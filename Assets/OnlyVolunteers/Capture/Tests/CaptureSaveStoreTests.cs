using System;
using System.IO;
using NUnit.Framework;
using UnityEngine;

namespace OnlyVolunteers.Capture.Tests
{
    /// <summary>WP01 save overwrite guard (SAVE_PROGRESS v01 §7, SV-04, SV-13): a newer / corrupt / too-old save is
    /// recognised before anything is applied, is never written over, renamed or deleted; every successful write keeps three
    /// rotating backups; a failed write keeps the previous file; the way out (a backup copy or a new game) is a NEW file.</summary>
    public sealed class CaptureSaveStoreTests
    {
        private string dir;
        private string path;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "ov_wp01_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            path = Path.Combine(dir, "capture_test.json");
        }

        [TearDown]
        public void TearDown()
        {
            try { if (Directory.Exists(dir)) Directory.Delete(dir, true); } catch (Exception) { }
        }

        private static string Json(float playTime, int version = CaptureSaveData.CurrentVersion)
        {
            var data = new CaptureSaveData { playTime = playTime, savedUtc = new DateTime(2026, 10, 28, 12, 0, 0, DateTimeKind.Utc).AddMinutes(playTime).ToString("o") };
            data.version = version;
            return JsonUtility.ToJson(data, true);
        }

        private static float PlayTime(string file) => JsonUtility.FromJson<CaptureSaveData>(File.ReadAllText(file)).playTime;

        // ---------- probe ----------

        [Test]
        public void ProbeMissingValidNewerTooOld()
        {
            Assert.AreEqual(SaveFileStatus.Missing, CaptureSaveStore.Probe(path).Status);
            File.WriteAllText(path, Json(7f));
            var valid = CaptureSaveStore.Probe(path);
            Assert.AreEqual(SaveFileStatus.Valid, valid.Status);
            Assert.IsTrue(valid.Loadable);
            Assert.AreEqual(7f, valid.Data.playTime);
            File.WriteAllText(path, Json(7f, CaptureSaveData.CurrentVersion + 1));
            var newer = CaptureSaveStore.Probe(path);
            Assert.AreEqual(SaveFileStatus.Newer, newer.Status);
            Assert.AreEqual(CaptureSaveData.CurrentVersion + 1, newer.Version);
            Assert.IsFalse(newer.Loadable);
            Assert.IsNull(newer.Data, "a newer save is never parsed into the old format");
            File.WriteAllText(path, Json(7f, CaptureSaveData.OldestLoadableVersion - 1));
            Assert.AreEqual(SaveFileStatus.TooOld, CaptureSaveStore.Probe(path).Status);
        }

        [TestCase("")]
        [TestCase("   \n")]
        [TestCase("not json at all")]
        [TestCase("{}")]
        [TestCase("{\"scene\":\"x\"}")]
        public void ProbeCorrupt(string text)
        {
            File.WriteAllText(path, text);
            var probe = CaptureSaveStore.Probe(path);
            Assert.AreEqual(SaveFileStatus.Corrupt, probe.Status, text);
            Assert.IsFalse(probe.Loadable);
        }

        [Test]
        public void ProbeTruncatedIsCorrupt()
        {
            string json = Json(3f);
            File.WriteAllText(path, json.Substring(0, json.Length / 2));
            Assert.AreEqual(SaveFileStatus.Corrupt, CaptureSaveStore.Probe(path).Status);
        }

        // ---------- write ----------

        [Test]
        public void WriteKeepsThreeRotatingBackups()
        {
            for (int i = 1; i <= 5; i++) CaptureSaveStore.Write(path, Json(i));
            Assert.AreEqual(5f, PlayTime(path));
            Assert.AreEqual(4f, PlayTime(CaptureSaveStore.BackupPath(path, 1)));
            Assert.AreEqual(3f, PlayTime(CaptureSaveStore.BackupPath(path, 2)));
            Assert.AreEqual(2f, PlayTime(CaptureSaveStore.BackupPath(path, 3)));
            Assert.IsFalse(File.Exists(CaptureSaveStore.BackupPath(path, 4)), "three backups, the oldest drops");
            Assert.IsFalse(File.Exists(path + ".tmp"), "no temporary file left");
            Assert.AreEqual(3, CaptureSaveStore.Backups(path).Count);
        }

        [Test]
        public void FirstWriteHasNoBackup()
        {
            CaptureSaveStore.Write(path, Json(1f));
            Assert.AreEqual(1f, PlayTime(path));
            Assert.AreEqual(0, CaptureSaveStore.Backups(path).Count);
        }

        /// <summary>SV-13: old code never writes over a newer-version save; nothing moves.</summary>
        [Test]
        public void WriteNeverReplacesANewerVersionFile()
        {
            string newer = Json(9f, CaptureSaveData.CurrentVersion + 1);
            File.WriteAllText(path, newer);
            byte[] before = File.ReadAllBytes(path);
            Assert.Throws<IOException>(() => CaptureSaveStore.Write(path, Json(1f)));
            CollectionAssert.AreEqual(before, File.ReadAllBytes(path), "the newer save is byte for byte the same");
            Assert.AreEqual(0, CaptureSaveStore.Backups(path).Count, "and it was not moved into a backup");
            Assert.IsFalse(File.Exists(path + ".tmp"));
        }

        /// <summary>SV-04: a failed write keeps the previous valid version and reports failure (throws).</summary>
        [Test]
        public void FailedWriteKeepsThePreviousFile()
        {
            CaptureSaveStore.Write(path, Json(1f));
            CaptureSaveStore.Write(path, Json(2f));
            byte[] before = File.ReadAllBytes(path);
            using (new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.None))
                Assert.Catch<Exception>(() => CaptureSaveStore.Write(path, Json(3f)), "a locked target fails the write");
            CollectionAssert.AreEqual(before, File.ReadAllBytes(path));
            Assert.AreEqual(2f, PlayTime(path));
            Assert.IsFalse(File.Exists(path + ".tmp"));
            Assert.IsNotNull(CaptureSaveStore.NewestValidBackup(path), "a valid backup still exists");
            Assert.AreEqual(1f, PlayTime(CaptureSaveStore.BackupPath(path, 1)), "a failed write does not shift the backups");
            Assert.AreEqual(1, CaptureSaveStore.Backups(path).Count);
            CaptureSaveStore.Write(path, Json(3f));
            Assert.AreEqual(3f, PlayTime(path), "the next write goes through");
            Assert.AreEqual(2f, PlayTime(CaptureSaveStore.BackupPath(path, 1)));
            Assert.AreEqual(1f, PlayTime(CaptureSaveStore.BackupPath(path, 2)));
        }

        [Test]
        public void AnInterruptedRotationIsRecoveredOnTheNextWrite()
        {
            CaptureSaveStore.Write(path, Json(1f));
            CaptureSaveStore.Write(path, Json(2f));
            File.Copy(path, CaptureSaveStore.StagedBackupPath(path)); // a crash after replace, before the rotation
            CaptureSaveStore.Write(path, Json(3f));
            Assert.AreEqual(3f, PlayTime(path));
            Assert.AreEqual(2f, PlayTime(CaptureSaveStore.BackupPath(path, 1)));
            Assert.AreEqual(2f, PlayTime(CaptureSaveStore.BackupPath(path, 2)));
            Assert.AreEqual(1f, PlayTime(CaptureSaveStore.BackupPath(path, 3)));
            Assert.IsFalse(File.Exists(CaptureSaveStore.StagedBackupPath(path)));
        }

        [Test]
        public void TextThatDoesNotVerifyIsNeverWritten()
        {
            CaptureSaveStore.Write(path, Json(1f));
            byte[] before = File.ReadAllBytes(path);
            Assert.Throws<InvalidDataException>(() => CaptureSaveStore.Write(path, "{\"version\":2,\"scene\""));
            Assert.Throws<InvalidDataException>(() => CaptureSaveStore.Write(path, Json(1f, CaptureSaveData.CurrentVersion + 1)));
            CollectionAssert.AreEqual(before, File.ReadAllBytes(path));
            Assert.AreEqual(0, CaptureSaveStore.Backups(path).Count, "a refused write does not rotate anything");
        }

        // ---------- the way out ----------

        [Test]
        public void NewestValidBackupSkipsBrokenOnes()
        {
            for (int i = 1; i <= 4; i++) CaptureSaveStore.Write(path, Json(i));
            File.WriteAllText(CaptureSaveStore.BackupPath(path, 1), "{\"version\":2,");
            var backup = CaptureSaveStore.NewestValidBackup(path);
            Assert.IsNotNull(backup);
            Assert.AreEqual(CaptureSaveStore.BackupPath(path, 2), backup.Path);
            Assert.AreEqual(2f, backup.Data.playTime);
            Assert.AreNotEqual("время неизвестно", backup.WhenText());
            foreach (var b in CaptureSaveStore.Backups(path)) File.WriteAllText(b.Path, "garbage");
            Assert.IsNull(CaptureSaveStore.NewestValidBackup(path), "all backups broken: none offered");
        }

        [Test]
        public void RestoringABackupLeavesTheFailedFileAndItsBackupsUntouched()
        {
            for (int i = 1; i <= 3; i++) CaptureSaveStore.Write(path, Json(i));
            File.WriteAllText(path, Json(99f, CaptureSaveData.CurrentVersion + 3)); // a newer build wrote the current file
            byte[] main = File.ReadAllBytes(path);
            byte[] bak1 = File.ReadAllBytes(CaptureSaveStore.BackupPath(path, 1));
            byte[] bak2 = File.ReadAllBytes(CaptureSaveStore.BackupPath(path, 2));
            var backup = CaptureSaveStore.NewestValidBackup(path);
            string restored = CaptureSaveStore.RestoreBackupToNewFile(path, backup.Path, new DateTime(2026, 10, 28, 20, 0, 0, DateTimeKind.Utc));
            Assert.AreNotEqual(path, restored);
            Assert.AreEqual(restored, CaptureSaveStore.ResolveActive(path), "the game now reads and writes the copy");
            CollectionAssert.AreEqual(bak1, File.ReadAllBytes(restored), "the copy is the backup byte for byte");
            // the session goes on writing its active file
            CaptureSaveStore.Write(restored, Json(4f));
            CaptureSaveStore.Write(restored, Json(5f));
            CollectionAssert.AreEqual(main, File.ReadAllBytes(path), "the failed file is untouched");
            CollectionAssert.AreEqual(bak1, File.ReadAllBytes(CaptureSaveStore.BackupPath(path, 1)));
            CollectionAssert.AreEqual(bak2, File.ReadAllBytes(CaptureSaveStore.BackupPath(path, 2)));
            Assert.AreEqual(5f, PlayTime(restored));
        }

        [Test]
        public void NewGameInANewFileLeavesTheFailedFileUntouched()
        {
            File.WriteAllText(path, "{\"version\":2, broken");
            byte[] main = File.ReadAllBytes(path);
            string fresh = CaptureSaveStore.StartNewFile(path, new DateTime(2026, 10, 28, 20, 0, 0, DateTimeKind.Utc));
            Assert.AreEqual(fresh, CaptureSaveStore.ResolveActive(path));
            Assert.AreEqual(SaveFileStatus.Missing, CaptureSaveStore.Probe(fresh).Status, "a new game: nothing to load yet");
            CaptureSaveStore.Write(fresh, Json(1f));
            CaptureSaveStore.Write(fresh, Json(2f));
            CollectionAssert.AreEqual(main, File.ReadAllBytes(path));
            Assert.AreEqual(0, CaptureSaveStore.Backups(path).Count);
            string second = CaptureSaveStore.StartNewFile(path, new DateTime(2026, 10, 28, 20, 0, 0, DateTimeKind.Utc));
            Assert.AreNotEqual(fresh, second, "the same second still gives a free name");
        }

        [TestCase("..\\other.json")]
        [TestCase("C:\\Windows\\x.json")]
        [TestCase("notes.txt")]
        [TestCase("")]
        public void PointerOnlyNamesASiblingSaveFile(string pointer)
        {
            File.WriteAllText(CaptureSaveStore.PointerPath(path), pointer);
            Assert.AreEqual(path, CaptureSaveStore.ResolveActive(path));
        }

        [Test]
        public void NoPointerMeansTheBaseFile()
        {
            Assert.AreEqual(path, CaptureSaveStore.ResolveActive(path));
        }

        [Test]
        public void ExplainNamesTheProblem()
        {
            File.WriteAllText(path, Json(1f, CaptureSaveData.CurrentVersion + 1));
            StringAssert.Contains("более новой версией", CaptureSaveStore.Explain(CaptureSaveStore.Probe(path)));
            File.WriteAllText(path, "nope");
            StringAssert.Contains("повреждено", CaptureSaveStore.Explain(CaptureSaveStore.Probe(path)));
        }
    }
}
