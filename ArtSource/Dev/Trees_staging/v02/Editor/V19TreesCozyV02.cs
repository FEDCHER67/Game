using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19TreesCozyV02
    {
        public enum TreeRevision { Original, CozyV02 }
        public static TreeRevision V19Revision = TreeRevision.CozyV02;
        public static bool ForestConifers = true;
        public static bool BetweenDistrictBroadleafTrial = true;
        public static bool RoughBareTrees = true;
        public const string Root = "Assets/OnlyVolunteers/Art/Trees/v02";
        public const string ScenePath = "Assets/OnlyVolunteers/Scenes/Dev/Trees_Test.unity";
        public const string Review = "Working/Reviews/Trees";
        public static readonly Vector3 Proportions = new(1.25f,.78f,1.25f);
        public const string ShaderName = "OnlyVolunteers/Trees/Cozy Sway v02";
        public static bool IsConifer(string n) => n.ToLowerInvariant().Contains("tree_pine_");
        public static bool IsBare(string n) => n.StartsWith("TREE_BARE_",StringComparison.OrdinalIgnoreCase) || n.StartsWith("LEAFLESS_TERRAIN_",StringComparison.OrdinalIgnoreCase);
        public static bool IsBroadleaf(string n) => !IsConifer(n) && !n.ToLowerInvariant().Contains("palm") && (n.StartsWith("tree_",StringComparison.OrdinalIgnoreCase) || n.StartsWith("V19_tree_",StringComparison.OrdinalIgnoreCase));
        public static bool IsTree(string n) => IsConifer(n)||IsBare(n)||IsBroadleaf(n);
        public static string RevisionPath(GameObject source) => Root+"/Prefabs/"+source.name+"_Cozy_v02.prefab";
        public static GameObject Original(GameObject tree)
        {
            if (!tree || !AssetDatabase.GetAssetPath(tree).StartsWith(Root+"/",StringComparison.Ordinal)) return tree;
            string name=tree.name.Replace("_Cozy_v02","");
            var source=TreesCozyAuthoringV02.Sources().FirstOrDefault(p=>p.name==name);
            if (!source) throw new InvalidDataException("Cannot resolve original tree: "+tree.name);
            return source;
        }
        public static GameObject Resolve(GameObject tree,string revision)
        {
            if (!tree || revision!="v19" || !IsTree(tree.name)) return tree;
            var original=Original(tree);
            if (V19Revision==TreeRevision.Original || (IsConifer(original.name)&&!ForestConifers)
                || (IsBroadleaf(original.name)&&!BetweenDistrictBroadleafTrial) || (IsBare(original.name)&&!RoughBareTrees)) return original;
            string path=RevisionPath(original); var revised=AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!revised) throw new FileNotFoundException("G23 v02 tree set is incomplete",path);
            return revised;
        }
        static bool Inside(Vector3 p,Vector4 b) => p.x>=b.x && p.z>=b.y && p.x<=b.z && p.z<=b.w;
        // Shared district bounds make roadside/common land explicit. Forest conifers are selected
        // inside the forest district. Trees inside every other district remain approved originals.
        public static bool ApplyToTerrain(TerrainData data,Vector3 origin,string revision)
        {
            if (revision!="v19") return false;
            var districts=V19PaletteTest.Districts();
            var forest=districts.First(d=>d.id=="forest").bounds;
            var prototypes=data.treePrototypes.ToList(); var before=prototypes.ToArray();
            var originals=before.Select(p=>Original(p.prefab)).ToArray();
            var candidates=before.Select(p=>Resolve(p.prefab,revision)).ToArray();
            var instances=data.treeInstances; bool changed=false;
            for (int i=0;i<instances.Length;i++)
            {
                var instance=instances[i]; int old=instance.prototypeIndex;
                var original=originals[old]; if (!original||!IsTree(original.name)) continue;
                Vector3 world=origin+Vector3.Scale(instance.position,data.size);
                bool select=IsBare(original.name) || (IsConifer(original.name)&&Inside(world,forest))
                    || (IsBroadleaf(original.name)&&!districts.Any(d=>Inside(world,d.bounds)));
                var desired=select?candidates[old]:original;
                int index=prototypes.FindIndex(p=>p.prefab==desired);
                if(index<0) { index=prototypes.Count; prototypes.Add(new TreePrototype {prefab=desired,bendFactor=0}); }
                if(index==old) continue;
                instance.prototypeIndex=index; instances[i]=instance; changed=true;
            }
            if(changed) { data.treePrototypes=prototypes.ToArray(); data.SetTreeInstances(instances,false); EditorUtility.SetDirty(data); }
            return changed;
        }
        public static TerrainData ResolveTerrainCopy(TerrainData original,Vector3 origin,string revision)
        {
            if(revision!="v19") return original;
            var copy=UnityEngine.Object.Instantiate(original);
            if(!ApplyToTerrain(copy,origin,revision)) { UnityEngine.Object.DestroyImmediate(copy); return original; }
            string source=AssetDatabase.GetAssetPath(original);
            if(string.IsNullOrEmpty(source)) { UnityEngine.Object.DestroyImmediate(copy); throw new InvalidOperationException("Save source terrain first"); }
            string folder=Path.GetDirectoryName(source).Replace('\\','/'); int build=1; string path;
            do { path=folder+"/"+original.name+"_Trees_v02_build"+build++.ToString("D3")+".asset"; } while(File.Exists(path));
            copy.name=Path.GetFileNameWithoutExtension(path); AssetDatabase.CreateAsset(copy,path); return copy;
        }
    }
}
