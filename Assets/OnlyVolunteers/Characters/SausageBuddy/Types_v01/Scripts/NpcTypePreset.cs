using UnityEngine;

namespace OnlyVolunteers.Characters.Types
{
    /// <summary>G44: one of Vadim's NPC types (ArtSource/Characters/SAUSAGE_BUDDY_01/Types, finished files, imported as is)
    /// as a crowd appearance. Visual is the type's prefab, built exactly like SausageBuddy_A (its FBX with the Buddy
    /// controller and avatar, NpcRig, NpcHeldProps when it carries something), so a crowd NPC made from it
    /// (MapGreyboxBuilder.SpawnCrowdNpc) ragdolls, is captured, tied, swapped on the table and saved like the A/B Buddies.
    /// The visual's object name "SausageBuddy_&lt;TypeId&gt;" is the type's identity in capture facts
    /// (CaptureDirector.VisualName / TypeIdFor give "SAUSAGE_BUDDY_&lt;TypeId&gt;") and in a save (CaptureSave.Template).
    /// Written by NpcTypesImportV01 (Types_v01/Editor) from the type's validation json; data only.</summary>
    public sealed class NpcTypePreset : ScriptableObject
    {
        public string TypeId = "";
        [Tooltip("The type's label from its manifest (npc_type.label).")]
        public string DisplayName = "";
        [Tooltip("The district group from its manifest (npc_type.group).")]
        public string Group = "";
        public int Revision;
        [Tooltip("Types_v01/Prefabs/SausageBuddy_<TypeId>.prefab")]
        public GameObject Visual;
        [Tooltip("npc_type.game_scale (applied as the visual prefab's scale).")]
        public float GameScale = 1f;
        [Tooltip("Idle grounding offset of the type's own clips (heels): applied as the visual prefab's height.")]
        public float GroundLift;
        public bool HandProps;
        public int Triangles;
        public float HeightM;
        public string SourceFbx = "";

        public string VisualName => "SausageBuddy_" + TypeId;
    }
}
