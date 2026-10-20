using System;
using System.Collections.Generic;
using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.Characters.Types
{
    /// <summary>G44: which NPC types walk in which district (weights), and the idle placements of the special types.
    /// CrowdDirector.TypeTable uses TakeFor for every crowd spawn: a type drawn by weight for the district (a Unique type
    /// only while none is alive), then a pooled NPC already wearing it, else a clone of the director's template for it.
    /// A district without types (elite, quiet valley, Tramduro), the police patrol, or a type without a template take a
    /// FallbackVisuals NPC (the A/B Buddies) the same way. Null when nothing fits: the director then pops its pool as
    /// before. Placements are data for the scene builder only (no runtime code reads them).</summary>
    public sealed class NpcSpawnTables : ScriptableObject
    {
        [Serializable]
        public sealed class Entry
        {
            public NpcTypePreset Type;
            [Min(0f)] public float Weight = 1f;
            [Tooltip("At most one alive on the whole map at a time.")]
            public bool Unique;
        }

        [Serializable]
        public sealed class District
        {
            [Tooltip("Crowd file district id (W85: forest, hamlet, construction, rough, downtown, port, elite, quiet_valley, beach, tramduro).")]
            public string Id = "";
            [Tooltip("Older crowd file ids for the same district (v19: village, transition, residential, old_town, industrial).")]
            public string[] Aliases = Array.Empty<string>();
            public List<Entry> Entries = new();
        }

        [Serializable]
        public sealed class Placement
        {
            public NpcTypePreset Type;
            public string District = "";
            [Tooltip("Idle, or a CrowdActivity name (BeachLie) the NPC stays in.")]
            public string Activity = "Idle";
            [Tooltip("Prop placed with him (the sand mound of BEACH_BURIED).")]
            public GameObject Prop;
            [Tooltip("Game hours he is there (0-24 = all day).")]
            public Vector2 Hours = new(0f, 24f);
            public int Count = 1;
            [TextArea] public string Note = "";
        }

        public List<District> Districts = new();
        [Tooltip("Visual (Animator object) names used where a district has no types and for the police patrol.")]
        public string[] FallbackVisuals = { "SausageBuddy_A", "SausageBuddy_B" };
        public List<Placement> Placements = new();

        public District Find(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            foreach (District d in Districts)
            {
                if (d.Id == id) return d;
                if (d.Aliases != null && Array.IndexOf(d.Aliases, id) >= 0) return d;
            }
            return null;
        }

        /// <summary>The NPC object for one crowd spawn in district 'districtId' (null: police / no district), taken out of
        /// 'pool' or cloned (inactive) from 'templates' under 'parent'. See the class summary.</summary>
        public GameObject TakeFor(string districtId, List<GameObject> pool, GameObject[] templates, Transform parent)
        {
            District d = Find(districtId);
            NpcTypePreset type = d != null ? Pick(d) : null;
            if (type != null && Take(pool, templates, parent, v => v == type.VisualName) is GameObject typed) return typed;
            return Take(pool, templates, parent, v => Array.IndexOf(FallbackVisuals, v) >= 0);
        }

        /// <summary>The visual (Animator object) name of an NPC: "SausageBuddy_A", "SausageBuddy_BAD_GOPNIK".</summary>
        public static string VisualOf(GameObject npc)
        {
            Animator a = npc != null ? npc.GetComponentInChildren<Animator>(true) : null;
            return a != null ? a.gameObject.name : "";
        }

        private static NpcTypePreset Pick(District d)
        {
            float total = 0f;
            foreach (Entry e in d.Entries)
                if (Usable(e)) total += e.Weight;
            if (total <= 0f) return null;
            float r = UnityEngine.Random.value * total;
            NpcTypePreset last = null;
            foreach (Entry e in d.Entries)
            {
                if (!Usable(e)) continue;
                last = e.Type;
                r -= e.Weight;
                if (r <= 0f) return e.Type;
            }
            return last;
        }

        private static bool Usable(Entry e) => e.Type != null && e.Weight > 0f && !(e.Unique && Alive(e.Type.VisualName));

        private static bool Alive(string visual)
        {
            foreach (GreyboxNpc npc in GreyboxNpc.All)
                if (npc != null && VisualOf(npc.gameObject) == visual) return true;
            return false;
        }

        private static GameObject Take(List<GameObject> pool, GameObject[] templates, Transform parent, Predicate<string> fits)
        {
            if (pool != null)
                for (int i = pool.Count - 1; i >= 0; i--)
                    if (pool[i] != null && fits(VisualOf(pool[i])))
                    {
                        GameObject go = pool[i];
                        pool.RemoveAt(i);
                        return go;
                    }
            if (templates == null) return null;
            var matches = new List<GameObject>();
            foreach (GameObject t in templates)
                if (t != null && fits(VisualOf(t))) matches.Add(t);
            return matches.Count > 0 ? Instantiate(matches[UnityEngine.Random.Range(0, matches.Count)], parent) : null;
        }
    }
}
