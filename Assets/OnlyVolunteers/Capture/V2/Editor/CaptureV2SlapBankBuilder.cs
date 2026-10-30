using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace OnlyVolunteers.Capture.V2.EditorTools
{
    /// <summary>Fills Resources/CaptureV2SlapBank.asset with Vadim's slap (31.10): Audio/Slap/Slap_Vadim_Light/Medium/Heavy_*
    /// by name, the original Slap_Vadim_01 as the fallback; runs by itself whenever something in that folder is imported or deleted, and
    /// before every player build, from the menu or batch mode (-executeMethod OnlyVolunteers.Capture.V2.EditorTools.CaptureV2SlapBankBuilder.Build).</summary>
    public sealed class CaptureV2SlapBankBuilder : AssetPostprocessor, IPreprocessBuildWithReport
    {
        public int callbackOrder => 0;
        public void OnPreprocessBuild(BuildReport report) => Build();

        public const string Folder = "Assets/OnlyVolunteers/Capture/V2/Audio/Slap";
        public const string BankPath = "Assets/OnlyVolunteers/Capture/V2/Resources/CaptureV2SlapBank.asset";
        public const string HitPath = Folder + "/Slap_Vadim_01.wav";

        [MenuItem("OnlyVolunteers/Capture V2/Rebuild slap sound bank")]
        public static void Build()
        {
            if (!AssetDatabase.IsValidFolder("Assets/OnlyVolunteers/Capture/V2/Resources"))
                AssetDatabase.CreateFolder("Assets/OnlyVolunteers/Capture/V2", "Resources");
            var bank = AssetDatabase.LoadAssetAtPath<CaptureV2SlapBank>(BankPath);
            bool created = bank == null;
            if (created) bank = ScriptableObject.CreateInstance<CaptureV2SlapBank>();
            bank.Hit = AssetDatabase.LoadAssetAtPath<AudioClip>(HitPath);
            AudioClip[] Tier(string tier) => Enumerable.Range(1, 9)
                .Select(i => AssetDatabase.LoadAssetAtPath<AudioClip>($"{Folder}/Slap_Vadim_{tier}_{i:00}.wav")).Where(c => c != null).ToArray();
            bank.Light = Tier("Light");
            bank.Medium = Tier("Medium");
            bank.Heavy = Tier("Heavy");
            if (created) AssetDatabase.CreateAsset(bank, BankPath);
            else EditorUtility.SetDirty(bank);
            AssetDatabase.SaveAssets();
            Debug.Log($"[CaptureV2] slap bank: light {bank.Light.Length}, medium {bank.Medium.Length}, heavy {bank.Heavy.Length}, fallback {(bank.Hit != null ? bank.Hit.name : "MISSING")}");
        }

        private static bool _queued;

        private static void OnPostprocessAllAssets(string[] imported, string[] deleted, string[] moved, string[] movedFrom)
        {
            bool touches = imported.Concat(deleted).Concat(moved).Concat(movedFrom).Any(p => p.StartsWith(Folder + "/"));
            if (!touches || _queued) return;
            _queued = true;
            EditorApplication.delayCall += () =>
            {
                _queued = false;
                Build();
            };
        }
    }
}
