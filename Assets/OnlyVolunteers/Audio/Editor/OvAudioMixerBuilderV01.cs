using System;
using System.Linq;
using System.Reflection;
using System.Text;
using OnlyVolunteers.Audio;
using UnityEditor;
using UnityEngine;
using UnityEngine.Audio;

namespace OnlyVolunteers.Audio.EditorTools
{
    /// <summary>
    /// Creates Audio/Mixer/OV_Main_v01.mixer (29.10): Master → Effects / Ambience / VoiceUI, each group's volume exposed as
    /// OV_Vol_&lt;Group&gt; (the names OvAudioMixerV01 sets), the routing asset Audio/Resources/OvAudioRouting_v01.asset
    /// that points the runtime at it, and the one-shot library's default output (SfxLibrary.Output = Effects; per-id
    /// VoiceUI routing is done in code). Unity has no public API for building a mixer, so the editor's own
    /// AudioMixerController is driven by reflection (the same calls the Audio Mixer window makes). Never overwrites an
    /// existing mixer file: a second run only checks it and re-links the routing asset.
    /// </summary>
    public static class OvAudioMixerBuilderV01
    {
        public const string MixerPath = "Assets/OnlyVolunteers/Audio/Mixer/OV_Main_v01.mixer";
        public const string RoutingPath = "Assets/OnlyVolunteers/Audio/Resources/OvAudioRouting_v01.asset";
        const string SfxLibraryPath = "Assets/OnlyVolunteers/Audio/Resources/SfxLibrary.asset";

        [MenuItem("OnlyVolunteers/Audio/Build mixer OV_Main_v01")]
        public static void BuildMenu() => Debug.Log(Build());

        public static string Build()
        {
            var log = new StringBuilder();
            Assembly editor = typeof(Editor).Assembly;
            Type controllerType = editor.GetType("UnityEditor.Audio.AudioMixerController");
            Type groupType = editor.GetType("UnityEditor.Audio.AudioMixerGroupController");
            Type pathType = editor.GetType("UnityEditor.Audio.AudioGroupParameterPath");
            Type exposedType = editor.GetType("UnityEditor.Audio.ExposedAudioParameter");
            if (controllerType == null || groupType == null || pathType == null || exposedType == null)
                return "FAILED: the editor's mixer types were not found (Unity API changed)";
            const BindingFlags any = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;

            var mixer = AssetDatabase.LoadAssetAtPath<AudioMixer>(MixerPath);
            if (mixer == null)
            {
                System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(MixerPath));
                MethodInfo create = controllerType.GetMethod("CreateMixerControllerAtPath", any);
                if (create == null) return "FAILED: CreateMixerControllerAtPath missing";
                mixer = (AudioMixer)create.Invoke(null, new object[] { MixerPath });
                log.AppendLine("created " + MixerPath);
                object master = controllerType.GetProperty("masterGroup", any).GetValue(mixer);
                MethodInfo newGroup = controllerType.GetMethod("CreateNewGroup", any);
                MethodInfo addChild = controllerType.GetMethod("AddChildToParent", any);
                MethodInfo volumeGuid = groupType.GetMethod("GetGUIDForVolume", any);
                MethodInfo expose = controllerType.GetMethod("AddExposedParameter", any);
                ConstructorInfo pathCtor = pathType.GetConstructors(any).First(c => c.GetParameters().Length == 2);
                var groups = new System.Collections.Generic.List<(object group, string name)> { (master, "Master") };
                foreach (OvAudioBus bus in OvAudioMixerV01.Buses)
                {
                    if (bus == OvAudioBus.Master) continue;
                    object g = newGroup.Invoke(mixer, new object[] { OvAudioMixerV01.GroupName(bus), false });
                    addChild.Invoke(mixer, new[] { g, master });
                    groups.Add((g, OvAudioMixerV01.GroupName(bus)));
                }
                foreach (var (group, name) in groups)
                {
                    object guid = volumeGuid.Invoke(group, null);
                    expose.Invoke(mixer, new[] { pathCtor.Invoke(new[] { group, guid }) });
                }
                // name the exposed parameters OV_Vol_<Group> (they are created as "MyExposedParam N")
                PropertyInfo exposedProp = controllerType.GetProperty("exposedParameters", any);
                var arr = (Array)exposedProp.GetValue(mixer);
                FieldInfo guidField = exposedType.GetField("guid", any), nameField = exposedType.GetField("name", any);
                for (int i = 0; i < arr.Length; i++)
                {
                    object e = arr.GetValue(i);
                    object g = guidField.GetValue(e);
                    foreach (var (group, name) in groups)
                        if (volumeGuid.Invoke(group, null).Equals(g)) { nameField.SetValue(e, "OV_Vol_" + name); break; }
                    arr.SetValue(e, i);
                }
                exposedProp.SetValue(mixer, arr);
                EditorUtility.SetDirty(mixer);
                AssetDatabase.SaveAssets();
                log.AppendLine("groups: " + string.Join(", ", groups.Select(x => x.name)) + "; exposed " + arr.Length + " volume parameters");
            }
            else log.AppendLine("kept " + MixerPath);

            // check what the runtime will look up
            foreach (OvAudioBus bus in OvAudioMixerV01.Buses)
            {
                var found = mixer.FindMatchingGroups(bus == OvAudioBus.Master ? "Master" : "Master/" + OvAudioMixerV01.GroupName(bus));
                log.AppendLine($"  {OvAudioMixerV01.GroupName(bus)}: group {(found.Length > 0 ? "ok" : "MISSING")}, parameter {OvAudioMixerV01.Parameter(bus)}");
            }
            var exposedNow = (Array)controllerType.GetProperty("exposedParameters", any).GetValue(mixer);
            var names = new System.Collections.Generic.List<string>();
            foreach (object e in exposedNow) names.Add((string)exposedType.GetField("name", any).GetValue(e));
            log.AppendLine("  exposed: " + string.Join(", ", names));

            var routing = AssetDatabase.LoadAssetAtPath<OvAudioRoutingV01>(RoutingPath);
            if (routing == null)
            {
                routing = ScriptableObject.CreateInstance<OvAudioRoutingV01>();
                AssetDatabase.CreateAsset(routing, RoutingPath);
                log.AppendLine("created " + RoutingPath);
            }
            routing.Mixer = mixer;
            EditorUtility.SetDirty(routing);

            var library = AssetDatabase.LoadAssetAtPath<SfxLibrary>(SfxLibraryPath);
            var effects = mixer.FindMatchingGroups("Master/Effects").FirstOrDefault();
            if (library != null && effects != null && library.Output != effects)
            {
                library.Output = effects;
                EditorUtility.SetDirty(library);
                log.AppendLine("SfxLibrary.Output = Effects (NPC voices and UI ids go to VoiceUI in code)");
            }
            AssetDatabase.SaveAssets();
            return log.ToString();
        }
    }
}
