using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.EditorTools
{
    /// <summary>Adds the VadimHaze full-screen pass (distance haze on the whole map) to every URP renderer the project uses.</summary>
    static class VadimHazeSetup
    {
        const string Dir = "Assets/VadimLocal/Haze";

        public static void Install()
        {
            var assets = new List<UniversalRenderPipelineAsset>();
            if (GraphicsSettings.defaultRenderPipeline is UniversalRenderPipelineAsset a0) assets.Add(a0);
            for (int q = 0; q < QualitySettings.names.Length; q++) if (QualitySettings.GetRenderPipelineAssetAt(q) is UniversalRenderPipelineAsset aq) assets.Add(aq);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(Dir + "/VadimHaze.mat");
            if (!mat) { mat = new Material(Shader.Find("Hidden/VadimHaze")); AssetDatabase.CreateAsset(mat, Dir + "/VadimHaze.mat"); }
            int added = 0;
            foreach (var asset in assets.Distinct())
            {
                var list = new SerializedObject(asset).FindProperty("m_RendererDataList");
                for (int i = 0; i < list.arraySize; i++)
                {
                    var data = list.GetArrayElementAtIndex(i).objectReferenceValue as ScriptableRendererData;
                    if (!data || data.rendererFeatures.Any(f => f && f.name == "VadimHaze")) continue;
                    var feat = ScriptableObject.CreateInstance<FullScreenPassRendererFeature>();
                    feat.name = "VadimHaze";
                    feat.passMaterial = mat;
                    feat.injectionPoint = FullScreenPassRendererFeature.InjectionPoint.BeforeRenderingPostProcessing;
                    feat.fetchColorBuffer = true;
                    feat.requirements = ScriptableRenderPassInput.Depth | ScriptableRenderPassInput.Color;
                    AssetDatabase.AddObjectToAsset(feat, data);
                    data.rendererFeatures.Add(feat);
                    var dso = new SerializedObject(data);
                    var map = dso.FindProperty("m_RendererFeatureMap");
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feat, out string _, out long lid);
                    map.arraySize++; map.GetArrayElementAtIndex(map.arraySize - 1).longValue = lid;
                    dso.ApplyModifiedPropertiesWithoutUndo();
                    data.SetDirty(); EditorUtility.SetDirty(data);
                    added++;
                    Debug.Log("[VadimHaze] pass -> " + AssetDatabase.GetAssetPath(data));
                }
            }
            AssetDatabase.SaveAssets();
            Debug.Log("[VadimHaze] features added: " + added);
        }
    }
}
