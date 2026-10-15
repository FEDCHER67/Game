using System;
using System.Collections.Generic;
using System.IO;
using FishNet.Component.Transforming;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Object;
using GameKit.Dependencies.Utilities;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using OnlyVolunteers.Player;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    public static class OperationStage1Builder
    {
        public const string Root = "Assets/OnlyVolunteers/Operation/Stage1";
        public const string ScenePath = "Assets/OnlyVolunteers/Scenes/Dev/Operation_Net_Stage1.unity";
        private const string Prefabs = Root + "/Prefabs";
        private const string Data = Root + "/Data";
        private const string NetworkRoot = "Assets/OnlyVolunteers/Network/Prefabs/";
        private static Material metal, dark, accent;
        private static readonly List<NetworkObject> made = new();
        [MenuItem("OnlyVolunteers/Operation/Build Network Stage 1")]
        public static void Build()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle.");
            var prior = SceneManager.GetActiveScene();
            Directory.CreateDirectory(Prefabs); Directory.CreateDirectory(Data); Directory.CreateDirectory("Assets/OnlyVolunteers/Scenes/Dev");
            AssetDatabase.Refresh(); made.Clear();
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(Data + "/OperationStage1_v01.asset");
            if (tuning == null) { tuning = ScriptableObject.CreateInstance<OperationTuning>(); AssetDatabase.CreateAsset(tuning, Data + "/OperationStage1_v01.asset"); }
            EditorUtility.SetDirty(tuning);
            metal = Material("Steel", new Color(0.45f, 0.57f, 0.59f));
            dark = Material("Restraint", new Color(0.14f, 0.18f, 0.19f));
            accent = Material("Guide", new Color(0.2f, 0.85f, 0.75f));
            var patient = BuildPatient();
            var player = BuildPlayerPrefab();
            string syringePath = Root + "/Art/SYRINGE-ASTRA-001.fbx";
            if (!File.Exists(syringePath))
            {
                Directory.CreateDirectory(Root + "/Art");
                File.Copy("ArtSource/Props/SYRINGE-ASTRA-001/SYRINGE-ASTRA-001.fbx", syringePath);
                AssetDatabase.ImportAsset(syringePath, ImportAssetOptions.ForceSynchronousImport);
            }
            var syringe = AssetDatabase.LoadAssetAtPath<GameObject>(syringePath);
            var scalpel = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Props/ScalpelAstra/Model/SCALPEL-ASTRA-001.fbx");
            var toolPrefabs = new OperationTool[4];
            toolPrefabs[0] = Tool("Scalpel_A", scalpel, OperationToolKind.Scalpel, 0);
            toolPrefabs[1] = Tool("Scalpel_B", scalpel, OperationToolKind.Scalpel, 0);
            toolPrefabs[2] = Tool("Syringe_A", syringe, OperationToolKind.Syringe, 0);
            toolPrefabs[3] = Tool("Syringe_B", syringe, OperationToolKind.Syringe, 1);
            var definitions = new[] {
                AssetDatabase.LoadAssetAtPath<ItemDefinition>("Assets/OnlyVolunteers/Inventory/Items/Item_Kidney.asset"),
                AssetDatabase.LoadAssetAtPath<ItemDefinition>("Assets/OnlyVolunteers/Inventory/Items/Item_Liver.asset"),
                BloodDefinition(syringe) };
            var merchandise = new OperationPhysicalItem[3];
            for (int i = 0; i < 3; i++) merchandise[i] = Merchandise(definitions[i], tuning, i<2);

            Scene source = EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/NetworkTest.unity", OpenSceneMode.Additive);
            EditorSceneManager.SaveScene(source, ScenePath, true);
            EditorSceneManager.CloseScene(source, true);
            Scene scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Additive);
            SceneManager.SetActiveScene(scene);
            try
            {
                NetworkSession session = null; Camera menu = null; Light sun = null;
                foreach (var root in scene.GetRootGameObjects())
                {
                    if (root.TryGetComponent(out NetworkSession found)) { session = found; continue; }
                    if (root.TryGetComponent(out Camera foundCamera)) { menu = foundCamera; continue; }
                    if (root.TryGetComponent(out Light foundLight)) { sun = foundLight; continue; }
                    Object.DestroyImmediate(root);
                }
                if (session == null || menu == null) throw new InvalidOperationException("NetworkTest composition missing");
                if (sun == null) sun = new GameObject("Directional Light").AddComponent<Light>();
                sun.type = LightType.Directional; sun.intensity = 1.3f; sun.transform.rotation = Quaternion.Euler(50, -25, 0);
                menu.transform.SetPositionAndRotation(new Vector3(3, 3, -3), Quaternion.LookRotation(new Vector3(-3, -2, 3)));
                RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat; RenderSettings.ambientLight = new Color(0.5f, 0.55f, 0.6f);
                var floor = Box("Stage1 floor", null, new Vector3(0,-0.1f,0), new Vector3(9,0.2f,9), Material("Floor", new Color(0.17f,0.23f,0.25f)));
                Box("Backdrop", null, new Vector3(0,1.5f,3.6f), new Vector3(9,3,0.15f), Material("Wall", new Color(0.3f,0.42f,0.43f)));
                var composition = new SerializedObject(session);
                composition.FindProperty("playerPrefab").objectReferenceValue = player;
                composition.FindProperty("bodyPrefab").objectReferenceValue = null;
                composition.FindProperty("tablePrefab").objectReferenceValue = null;
                composition.FindProperty("scalpelPrefab").objectReferenceValue = null;
                var spawns = composition.FindProperty("playerSpawns"); spawns.arraySize = 4;
                for (int i = 0; i < 4; i++)
                {
                    var at = new GameObject("G25 player spawn " + i).transform;
                    at.position = new Vector3(i % 2 == 0 ? -1.65f : 1.65f, 0.05f, i < 2 ? -0.7f : 0.7f);
                    at.rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(-at.position, Vector3.up));
                    spawns.GetArrayElementAtIndex(i).objectReferenceValue = at;
                }
                composition.ApplyModifiedPropertiesWithoutUndo();
                var manager = session.GetComponent<NetworkManager>();
                string prefabListPath = Data + "/OperationSpawnables_v01.asset";
                var list = AssetDatabase.LoadAssetAtPath<SinglePrefabObjects>(prefabListPath);
                if (list == null) { list = Object.Instantiate(manager.SpawnablePrefabs) as SinglePrefabObjects; AssetDatabase.CreateAsset(list, prefabListPath); }
                foreach (var prefab in made) list.AddObject(prefab, true, false);
                EditorUtility.SetDirty(list); AssetDatabase.SaveAssetIfDirty(list);
                Set(manager, "_spawnablePrefabs", list);

                var tableRoot = new GameObject("G25 Operation table"); tableRoot.AddComponent<NetworkObject>();
                var table = tableRoot.AddComponent<NetworkOperationTable>();
                var tableModel = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Props/TableAstra/Model/TABLE-ASTRA-001.fbx"), tableRoot.transform);
                tableModel.name = "TABLE-ASTRA-001"; tableModel.transform.localRotation = Quaternion.Euler(0, 90, 0);
                foreach (var collider in tableModel.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(collider);
                Box("Patient support", tableRoot.transform, new Vector3(0,0.91f,0), new Vector3(0.88f,0.14f,2.1f), metal);
                var tray = Box("Reachable tray", tableRoot.transform, new Vector3(0.98f,0.98f,0), new Vector3(0.62f,0.1f,1.25f), metal);
                var registry = tableRoot.AddComponent<PatientRegistry>();
                Set(table,"tuning",tuning); Set(table,"patientPrefab",patient); Set(table,"registry",registry);
                SetArray(table,"toolPrefabs",toolPrefabs); SetArray(table,"merchandisePrefabs",merchandise); SetArray(table,"merchandiseDefinitions",definitions);
                var view = tableRoot.AddComponent<OperationTableView>(); Set(view,"table",table);
                var presentation = tableRoot.AddComponent<OperationPresentation>(); Set(presentation,"table",table);
                Set(presentation,"guideMaterial",accent);
                var straps = new GameObject[5];
                for (int i = 0; i < 5; i++) straps[i] = Box("Fastener " + i,tableRoot.transform,tuning.workSurface+tuning.restraintPositions[i],new Vector3(i==4?0.48f:0.16f,0.025f,0.055f),dark);
                SetArray(presentation,"straps",straps);
                tableRoot.AddComponent<OperationNetworkProbe>();
                EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
                AssetDatabase.SaveAssetIfDirty(tuning);
                Debug.Log("[G25] BUILT " + ScenePath + " prefabs=" + made.Count);
            }
            finally { EditorSceneManager.CloseScene(scene,true); if(prior.IsValid() && prior.isLoaded) SceneManager.SetActiveScene(prior); }
        }
        public static string BuildPlayer()
        {
            Directory.CreateDirectory("Working/Reviews/Operations/stage1/build");
            var result = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] {ScenePath}, locationPathName = "Working/Reviews/Operations/stage1/build/OperationsStage1.exe", target = BuildTarget.StandaloneWindows64, options = BuildOptions.Development });
            string report = result.summary.result + " errors=" + result.summary.totalErrors + " warnings=" + result.summary.totalWarnings;
            File.WriteAllText("Working/Reviews/Operations/stage1/build-result.txt", report); return report;
        }
        private static GameObject Body(string name)
        {
            var go = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(NetworkRoot + "NetworkPhysicsBody.prefab"));
            go.name = name;
            foreach (var renderer in go.GetComponentsInChildren<Renderer>()) Object.DestroyImmediate(renderer);
            foreach (var filter in go.GetComponentsInChildren<MeshFilter>()) Object.DestroyImmediate(filter);
            foreach (var collider in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(collider);
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity); go.transform.localScale = Vector3.one;
            return go;
        }
        private static NetworkPhysicsBody BuildPatient()
        {
            var go = Body("Stage1_Patient_v01"); go.GetComponent<Rigidbody>().mass = 65;
            var netTransform = new SerializedObject(go.GetComponent<NetworkTransform>());
            netTransform.FindProperty("_synchronizeScale").boolValue = true; netTransform.ApplyModifiedPropertiesWithoutUndo();
            var collider = go.AddComponent<BoxCollider>(); collider.size = new Vector3(0.62f,0.35f,1.85f); collider.center = new Vector3(0,0.12f,0);
            var buddy = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/SAUSAGE_BUDDY_PATIENT_v01.fbx"),go.transform);
            buddy.name="PATIENT model";
            var animator = buddy.GetComponent<Animator>();
            if (animator == null) animator = buddy.AddComponent<Animator>();
            animator.avatar = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Characters/SausageBuddy/SAUSAGE_BUDDY_A_v04.fbx").GetComponent<Animator>().avatar;
            animator.enabled=false;
            buddy.transform.localRotation=Quaternion.Euler(0,180,0)*Quaternion.Euler(-90,0,0); Fit(buddy, 1.85f);
            var anchors=go.AddComponent<OperationPatientAnchors>();
            var markers=new Transform[3]; string[] names={"INC_KIDNEY_L","INC_KIDNEY_R","INC_LIVER"};
            foreach(var t in buddy.GetComponentsInChildren<Transform>(true))
                for(int i=0;i<3;i++)if(t.name==names[i])markers[i]=t;
            for(int i=0;i<3;i++)if(markers[i]==null)throw new InvalidOperationException("Patient marker missing: "+names[i]);
            SetArray(anchors,"incisions",markers);
            return Save(go).GetComponent<NetworkPhysicsBody>();
        }
        private static NetworkPlayer BuildPlayerPrefab()
        {
            var go=Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(NetworkRoot+"NetworkPlayer.prefab"));
            go.name="Stage1_Player_v01";
            var inventory=go.GetComponent<NetworkInventory>();if(inventory==null)inventory=go.AddComponent<NetworkInventory>();
            Set(inventory,"database",AssetDatabase.LoadAssetAtPath<ItemDatabase>("Assets/OnlyVolunteers/Inventory/Items/ItemDatabase.asset"));
            Set(inventory,"reachOrigin",go.GetComponent<KccFirstPersonInput>().Character.Motor.transform);
            var input=go.GetComponent<InventoryInput>();if(input==null)input=go.AddComponent<InventoryInput>();
            Set(input,"inventorySource",inventory);Set(input,"viewCamera",go.GetComponentInChildren<Camera>(true));
            input.ExternalPickup=true;
            return Save(go).GetComponent<NetworkPlayer>();
        }
        private static OperationTool Tool(string name,GameObject model,OperationToolKind kind,int stock)
        {
            var go=Body("Stage1_"+name+"_v01"); go.GetComponent<Rigidbody>().mass=0.15f;
            var visual=Object.Instantiate(model,go.transform); Fit(visual,kind==OperationToolKind.Syringe?0.27f:0.24f);
            var collider=go.AddComponent<BoxCollider>(); collider.size=new Vector3(0.08f,0.06f,0.26f);
            var tool=go.AddComponent<OperationTool>(); var so=new SerializedObject(tool);
            so.FindProperty("kind").enumValueIndex=(int)kind; so.FindProperty("stockIndex").intValue=stock; so.ApplyModifiedPropertiesWithoutUndo();
            return Save(go).GetComponent<OperationTool>();
        }
        private static ItemDefinition BloodDefinition(GameObject syringe)
        {
            string path=Data+"/Item_BloodStage1_v01.asset"; var item=AssetDatabase.LoadAssetAtPath<ItemDefinition>(path);
            if(item!=null)return item;
            item=ScriptableObject.CreateInstance<ItemDefinition>();var so=new SerializedObject(item);
            so.FindProperty("id").intValue=109;so.FindProperty("displayName").stringValue="Blood";so.FindProperty("shortLabel").stringValue="BLD";
            so.FindProperty("baseValue").intValue=50;so.FindProperty("worldModel").objectReferenceValue=syringe;so.FindProperty("worldModelSize").floatValue=0.24f;
            so.ApplyModifiedPropertiesWithoutUndo();AssetDatabase.CreateAsset(item,path);return item;
        }
        private static OperationPhysicalItem Merchandise(ItemDefinition definition,OperationTuning tuning,bool organ)
        {
            var go=Body("Stage1_Output_"+definition.name+"_v01");
            ItemWorldModel.Build(definition,go.transform,false,false);go.GetComponent<Rigidbody>().mass=definition.DropMass;
            if(organ)go.transform.Find(ItemWorldModel.ChildName).localScale=Vector3.one*tuning.organItemScale;
            var world=go.AddComponent<WorldItem>();Set(world,"definition",definition);
            var item=go.AddComponent<OperationPhysicalItem>();Set(item,"tuning",tuning);
            return Save(go).GetComponent<OperationPhysicalItem>();
        }
        private static GameObject Save(GameObject go)
        {
            string path=Prefabs+"/"+go.name+".prefab";
            var hashText=new System.Text.StringBuilder();
            foreach(char c in (path+go.name).Trim().ToLowerInvariant())if((c>='a'&&c<='z')||(c>='0'&&c<='9'))hashText.Append(c);
            go.GetComponent<NetworkObject>().SetAssetPathHash(hashText.ToString().GetStableHashU64());
            var prefab=PrefabUtility.SaveAsPrefabAsset(go,path);made.Add(prefab.GetComponent<NetworkObject>());Object.DestroyImmediate(go);return prefab;
        }
        private static void Fit(GameObject go,float length)
        {
            Bounds bounds=new Bounds();bool first=true;
            foreach(var renderer in go.GetComponentsInChildren<Renderer>()){if(first){bounds=renderer.bounds;first=false;}else bounds.Encapsulate(renderer.bounds);}
            float size=Mathf.Max(bounds.size.x,bounds.size.y,bounds.size.z);if(size<0.001f)return;
            float factor=length/size;go.transform.localScale*=factor;go.transform.localPosition=-bounds.center*factor;
        }
        private static Material Material(string name,Color color)
        { string path=Data+"/"+name+"_v01.mat";var mat=AssetDatabase.LoadAssetAtPath<Material>(path);if(mat!=null)return mat;mat=new Material(Shader.Find("Universal Render Pipeline/Lit"));mat.color=color;AssetDatabase.CreateAsset(mat,path);return mat; }
        private static GameObject Box(string name,Transform parent,Vector3 position,Vector3 scale,Material mat)
        {var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(parent,false);go.transform.localPosition=position;go.transform.localScale=scale;go.GetComponent<Renderer>().sharedMaterial=mat;return go;}
        private static void Set(Object obj,string key,Object value){var so=new SerializedObject(obj);so.FindProperty(key).objectReferenceValue=value;so.ApplyModifiedPropertiesWithoutUndo();}
        private static void SetArray<T>(Object obj,string key,T[] values)where T:Object
        {var so=new SerializedObject(obj);var prop=so.FindProperty(key);prop.arraySize=values.Length;for(int i=0;i<values.Length;i++)prop.GetArrayElementAtIndex(i).objectReferenceValue=values[i];so.ApplyModifiedPropertiesWithoutUndo();}
    }
}
