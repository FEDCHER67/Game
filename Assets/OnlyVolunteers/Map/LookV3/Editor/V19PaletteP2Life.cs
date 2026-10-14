using System;
using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Audio.EditorTools;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object=UnityEngine.Object;

namespace OnlyVolunteers.Map.Look.V3
{
    public static class V19PaletteP2Life
    {
        static Transform root;
        static MapHeightSampler ground;
        static Material crowMaterial,woodMaterial,wireMaterial;
        static readonly List<DistrictLife19V02.Flyer> flyers=new();
        static readonly List<Light> lamps=new();
        static float Y(float x,float z)=>ground.Height(x,z);
        static GameObject Kit(string name,float x,float z,float yaw=0,float up=0)
        {
            return PlacePrefab(V19PaletteP2.Kit+"/Prefabs/"+name+"_v02.prefab",name,x,z,yaw,up);
        }
        static GameObject PlacePrefab(string path,string name,float x,float z,float yaw,float up)
        {
            var asset=AssetDatabase.LoadAssetAtPath<GameObject>(path);if(!asset)throw new InvalidOperationException("Missing "+path);
            var go=(GameObject)PrefabUtility.InstantiatePrefab(asset);go.name="V19_"+name;go.transform.SetParent(root,false);
            go.transform.position=new Vector3(x,Y(x,z)+up,z);go.transform.rotation=Quaternion.Euler(0,yaw,0);return go;
        }
        static Material Mat(string name,string hex)
        {
            var m=new Material(Shader.Find("Universal Render Pipeline/Lit")){name=name};m.SetColor("_BaseColor",V19PaletteP2.C(hex));m.SetFloat("_Smoothness",.1f);
            AssetDatabase.CreateAsset(m,V19PaletteP2.Output+"/Materials/"+name+".mat");return m;
        }
        static void Recolour(GameObject go,Material mat)
        {
            foreach(var r in go.GetComponentsInChildren<MeshRenderer>())r.sharedMaterials=Enumerable.Repeat(mat,r.sharedMaterials.Length).ToArray();
        }
        static void Bar(string name,Vector3 a,Vector3 b,float width,Material mat)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(root,false);
            go.transform.position=(a+b)*.5f;go.transform.rotation=Quaternion.FromToRotation(Vector3.up,b-a);go.transform.localScale=new Vector3(width,(b-a).magnitude,width);
            go.GetComponent<MeshRenderer>().sharedMaterial=mat;
        }
        public static void Place(DistrictWeather19V02 weather)
        {
            ground=Object.FindAnyObjectByType<MapHeightSampler>();root=new GameObject("V19_Life_CheckpointP_v02").transform;
            flyers.Clear();lamps.Clear();crowMaterial=Mat("V19_CrowBlack","#14191E");woodMaterial=Mat("V19_WornWood","#655949");wireMaterial=Mat("V19_Wires","#272E33");
            // One household: flowers at the house, chores beside the shed, tea and apples by the garden tree.
            Kit("LAUNDRY_CLOTHES",284,526.1f,8);
            Kit("FLOWER_BED",282,531.3f,5);Kit("FLOWER_BED",286.1f,531.6f,5);
            Kit("DOGHOUSE",288.7f,529,185);Kit("HEN_COOP_RUN",281.2f,522.5f,180);
            Kit("AXE_STUMP_LOGS",280.7f,528.7f,90);Kit("BUCKET_WATERING",286.1f,530.4f,35);
            Kit("BICYCLE",289.6f,527,83);Kit("APPLE_BASKET",286.4f,524.2f,10);
            Kit("PICNIC_TABLE",287,523.2f,25);Kit("CROOKED_FENCE",290.4f,526.9f,90);
            var tree=PlacePrefab("Assets/OnlyVolunteers/Art/Map/Prefabs/TREES/tree_apple_a.prefab","GardenAppleTree",289.2f,522.4f,0,0);
            tree.transform.localScale=Vector3.one*.9f;
            Kit("TREE_SWING",289.6f,522.35f,0,.42f);
            Bar("Swing_branch_support",new Vector3(289.2f,Y(289.2f,522.4f)+2.53f,522.4f),new Vector3(290.1f,Y(289.2f,522.4f)+2.53f,522.4f),.10f,woodMaterial);
            PlacePrefab("Assets/OnlyVolunteers/Art/Map/Prefabs/BENCHES/bench_soviet.prefab","GateBench",291,530.1f,90,0);
            Smoke(285.9f,535.0f,4.1f);
            for(int i=0;i<5;i++)
            {
                var butterfly=Kit("BUTTERFLY",282+i*.24f,531.3f,0,.9f);
                flyers.Add(new DistrictLife19V02.Flyer{body=butterfly.transform,centre=butterfly.transform.position,radius=.45f,speed=.85f+i*.1f,phase=i*1.3f,flap=20});
            }
            Rough(weather);
            var life=root.gameObject.AddComponent<DistrictLife19V02>();life.flyers=flyers.ToArray();life.wornLamps=lamps.ToArray();
            var source=AssetDatabase.LoadAssetAtPath<AmbienceData>("Assets/OnlyVolunteers/Audio/Resources/Ambience_v18.asset");
            var bounds=source.Districts.Select(d=>weather.districts.First(w=>w.id==d.Id).bounds).ToArray();
            var spots=new[]{
                new AmbienceData.Spot{Name="Apple garden birds",DistrictId="village",SoundId="amb_birds",Position=new Vector3(289.2f,Y(289.2f,522.4f)+2,522.4f),Volume=.13f,Range=22},
                new AmbienceData.Spot{Name="Hen run - awaiting clip",DistrictId="village",SoundId="life_hens",Position=new Vector3(281.2f,Y(281.2f,522.5f)+.5f,522.5f),Volume=.25f,Range=18},
                new AmbienceData.Spot{Name="Crow wire - awaiting clip",DistrictId="residential",SoundId="life_crow",Position=new Vector3(656,Y(656,650)+6,650),Volume=.3f,Range=38},
                new AmbienceData.Spot{Name="Distant stray dog - awaiting clip",DistrictId="residential",SoundId="life_dog_distant",Position=new Vector3(684,Y(684,669),669),Volume=.15f,Range=45}
            };
            AmbienceBaker.BakeV19Palette("v18",bounds,spots);
        }
        static void Smoke(float x,float z,float up)
        {
            var go=new GameObject("V19_LightChimneySmoke");go.transform.SetParent(root,false);go.transform.position=new Vector3(x,Y(x,z)+up,z);
            var p=go.AddComponent<ParticleSystem>();var main=p.main;main.loop=true;main.maxParticles=32;main.startLifetime=4;main.startSpeed=.35f;
            main.startSize=.32f;main.startColor=new Color(.62f,.65f,.65f,.14f);main.simulationSpace=ParticleSystemSimulationSpace.World;
            var emission=p.emission;emission.rateOverTime=3;var shape=p.shape;shape.shapeType=ParticleSystemShapeType.Cone;shape.angle=5;shape.radius=.12f;
            go.transform.rotation=Quaternion.Euler(-90,0,0);
            var over=p.sizeOverLifetime;over.enabled=true;over.size=new ParticleSystem.MinMaxCurve(1,new AnimationCurve(new Keyframe(0,.4f),new Keyframe(1,2.2f)));
            var fade=p.colorOverLifetime;fade.enabled=true;var gradient=new Gradient();gradient.SetKeys(new[]{new GradientColorKey(Color.white,0),new GradientColorKey(Color.white,1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(.6f,.15f),new GradientAlphaKey(0,1)});fade.color=gradient;
            var mat=new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit")){name="V19_SoftSmoke"};mat.SetFloat("_Surface",1);mat.SetFloat("_Blend",0);mat.SetFloat("_ZWrite",0);
            mat.SetFloat("_SrcBlend",(float)BlendMode.SrcAlpha);mat.SetFloat("_DstBlend",(float)BlendMode.OneMinusSrcAlpha);mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");mat.renderQueue=3000;
            // Generated analytic alpha texture; no dependency or download.
            var tex=new Texture2D(32,32,TextureFormat.RGBA32,true){name="V19_SmokeAlpha"};var pixels=new Color[1024];
            for(int j=0;j<32;j++)for(int i=0;i<32;i++){float r=new Vector2((i-15.5f)/15.5f,(j-15.5f)/15.5f).magnitude;pixels[j*32+i]=new Color(1,1,1,Mathf.Pow(Mathf.Clamp01(1-r),2));}
            tex.SetPixels(pixels);tex.Apply();AssetDatabase.CreateAsset(tex,V19PaletteP2.Output+"/V19_SmokeAlpha.asset");mat.SetTexture("_BaseMap",tex);
            AssetDatabase.CreateAsset(mat,V19PaletteP2.Output+"/Materials/V19_SoftSmoke.mat");go.GetComponent<ParticleSystemRenderer>().sharedMaterial=mat;
            p.Simulate(3,true,true);p.Play();
        }
        static void Rough(DistrictWeather19V02 weather)
        {
            var terrain=Terrain.activeTerrain;var data=terrain.terrainData;var prototypes=data.treePrototypes.ToList();
            var bareAsset=TerrainTree();
            prototypes.Add(new TreePrototype{prefab=bareAsset,bendFactor=0});data.treePrototypes=prototypes.ToArray();
            var trees=data.treeInstances;var bounds=weather.districts.Select(d=>d.bounds).ToArray();var weights=new float[bounds.Length];int ri=Array.FindIndex(weather.districts,d=>d.id=="residential");
            int changed=0;
            for(int i=0;i<trees.Length;i++)
            {
                Vector3 p=Vector3.Scale(trees[i].position,data.size)+terrain.transform.position;
                DistrictBlend19.Weights(bounds,new Vector2(p.x,p.z),60,weights);
                float selection=((i*7919)%1000)/1000f;
                if(selection>=weights[ri]*.94f)continue;
                trees[i].prototypeIndex=prototypes.Count-1;trees[i].widthScale=.8f+selection*.5f;trees[i].heightScale=.9f+selection*.5f;
                trees[i].color=new Color(.68f,.70f,.71f);changed++;
            }
            data.SetTreeInstances(trees,false);EditorUtility.SetDirty(data);
            for(int i=0;i<3;i++)
            {
                float x=638+i*26;float z=650;
                var pole=PlacePrefab("Assets/OnlyVolunteers/Art/Map/Prefabs/LAMPS/lamp_soviet_broken.prefab","WornLamp",x,z,90,0);
                var light=new GameObject("Flicker").AddComponent<Light>();light.transform.SetParent(pole.transform,true);light.transform.position=new Vector3(x,Y(x,z)+4.5f,z);
                light.type=LightType.Point;light.color=V19PaletteP2.C("#BAC8D2");light.range=7;light.intensity=.4f;light.shadows=LightShadows.None;lamps.Add(light);
                Bar("Overhead_support",new Vector3(x,Y(x,z),z),new Vector3(x,Y(x,z)+6.5f,z),.12f,wireMaterial);
                if(i>0)Wire(new Vector3(x-26,Y(x-26,z)+6.45f,z),new Vector3(x,Y(x,z)+6.45f,z));
            }
            // Weathered garage fronts, with real surface offsets and small, restrained decal coverage.
            for(int i=0;i<5;i++)Decal(new Vector3(655.5f+i*4.83f,Y(655.5f+i*4.83f,662.99f)+1.25f,659.67f),new Vector2(2.35f,1.25f),i%4);
            var look=MapLookBuilder.Load("v18");
            foreach(var b in look.buildings.Where(b=>b.district=="residential" && b.h>8).Take(8))
            {
                float minZ=b.fp.Where((v,i)=>i%2==1).Min();
                Detail("ROOF_ANTENNA",b.x,b.y,b.h+.12f,0);
                Detail("ROOF_SATELLITE_DISH",b.x+1.3f,b.y,b.h+.10f,25);
                Detail("WIN_AC_UNIT",b.x,minZ-.09f,b.h*.55f,0);
            }
            for(int i=0;i<6;i++)
            {
                var crow=Kit("CROW",653.6f+i*4.85f,660,180,2.67f);Recolour(crow,crowMaterial);
            }
            for(int i=0;i<7;i++)
            {
                var crow=Kit("CROW",662,654,0,10+i*.55f);Recolour(crow,crowMaterial);
                var left=Wing(crow.transform,-1);var right=Wing(crow.transform,1);
                flyers.Add(new DistrictLife19V02.Flyer{body=crow.transform,leftWing=left,rightWing=right,centre=crow.transform.position,radius=7+i*.85f,speed=.27f+i*.012f,phase=i*.84f,flap=7});
                // Also set the first still pose to a distributed flock rather than overlapping origins.
                crow.transform.position+=new Vector3(Mathf.Cos(i*.84f)*(7+i*.85f),0,Mathf.Sin(i*.84f)*(7+i*.85f)*.64f);
            }
            Debug.Log("[G18 P2] Bare tree ecotone: "+changed+"; 13 crows; five garage decals; three worn lamps.");
        }
        static GameObject TerrainTree()
        {
            const string path=V19PaletteP2.Kit+"/Prefabs/LEAFLESS_TERRAIN_v03.prefab";
            var existing=AssetDatabase.LoadAssetAtPath<GameObject>(path);if(existing)return existing;
            var modelPath=V19PaletteP2.Kit+"/LEAFLESS_TREE_v03.fbx";
            var importer=(ModelImporter)AssetImporter.GetAtPath(modelPath);importer.globalScale=1;importer.useFileScale=true;importer.bakeAxisConversion=true;importer.isReadable=true;
            importer.importAnimation=false;importer.importCameras=false;importer.importLights=false;importer.importBlendShapes=false;
            importer.importNormals=ModelImporterNormals.Import;importer.importTangents=ModelImporterTangents.None;importer.SaveAndReimport();
            var src=AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            var go=new GameObject("LEAFLESS_TERRAIN_v03");
            var combine=new List<CombineInstance>();
            foreach(var f in src.GetComponentsInChildren<MeshFilter>())for(int s=0;s<f.sharedMesh.subMeshCount;s++)
                combine.Add(new CombineInstance{mesh=f.sharedMesh,subMeshIndex=s,transform=f.transform.localToWorldMatrix});
            var mesh=new Mesh{name="LEAFLESS_TERRAIN_Metres_v03"};mesh.CombineMeshes(combine.ToArray(),true,true);mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh,V19PaletteP2.Kit+"/LEAFLESS_TERRAIN_Metres_v03.asset");
            go.AddComponent<MeshFilter>().sharedMesh=mesh;go.AddComponent<MeshRenderer>().sharedMaterial=woodMaterial;
            var proxySource=AssetDatabase.LoadAssetAtPath<GameObject>(V19PaletteP2.Kit+"/Prefabs/LEAFLESS_TREE_v02.prefab");
            foreach(var box in proxySource.GetComponentsInChildren<BoxCollider>())
            {
                var child=new GameObject(box.name);child.transform.SetParent(go.transform,false);child.transform.localPosition=box.transform.localPosition;
                child.transform.localRotation=box.transform.localRotation;var copy=child.AddComponent<BoxCollider>();copy.size=box.size;
                if(box.name.EndsWith("_trunk")){var c=child.transform.localPosition;c.y=1.7f;child.transform.localPosition=c;var size=copy.size;size.y=3.4f;copy.size=size;}
            }
            var result=PrefabUtility.SaveAsPrefabAsset(go,path);Object.DestroyImmediate(go);return result;
        }

        public static string RepairTreeContacts()
        {
            woodMaterial=AssetDatabase.LoadAssetAtPath<Material>(V19PaletteP2.Output+"/Materials/V19_WornWood.mat");
            var data=Terrain.activeTerrain.terrainData;var p=data.treePrototypes;p[p.Length-1]=new TreePrototype{prefab=TerrainTree(),bendFactor=0};data.treePrototypes=p;
            EditorUtility.SetDirty(data);AssetDatabase.SaveAssetIfDirty(data);
            return "v03 leafless tree: all primary branches meet the 3.4 m trunk; 11 source-fitted proxies";
        }

        public static string RefineFirstReview()
        {
            ground=Object.FindAnyObjectByType<MapHeightSampler>();root=GameObject.Find("V19_Life_CheckpointP_v02").transform;
            woodMaterial=AssetDatabase.LoadAssetAtPath<Material>(V19PaletteP2.Output+"/Materials/V19_WornWood.mat");
            var data=Terrain.activeTerrain.terrainData;var p=data.treePrototypes;p[p.Length-1]=new TreePrototype{prefab=TerrainTree(),bendFactor=0};data.treePrototypes=p;EditorUtility.SetDirty(data);
            // Use the open west garden, clear of the original orchard canopies and the narrow gate path.
            var laundry=GameObject.Find("V19_LAUNDRY_CLOTHES");laundry.transform.position=new Vector3(276.5f,Y(276.5f,532.0f),532.0f);laundry.transform.rotation=Quaternion.Euler(0,90,0);
            var coop=GameObject.Find("V19_HEN_COOP_RUN");coop.transform.position=new Vector3(276.4f,Y(276.4f,539.5f),539.5f);coop.transform.rotation=Quaternion.Euler(0,90,0);
            var table=GameObject.Find("V19_PICNIC_TABLE");table.transform.position=new Vector3(278.0f,Y(278.0f,534.5f),534.5f);table.transform.rotation=Quaternion.Euler(0,90,0);
            // Wires behind the garages cross the visible sky; clear of the alley's walking/driving space.
            foreach(var t in root.GetComponentsInChildren<Transform>())
                if(t.name=="Overhead_support" || t.name=="V19_WornLamp")t.position+=new Vector3(0,0,18);
            foreach(var line in root.GetComponentsInChildren<LineRenderer>())for(int i=0;i<line.positionCount;i++)line.SetPosition(i,line.GetPosition(i)+new Vector3(0,2.5f,18));
            foreach(var t in root.GetComponentsInChildren<Transform>().Where(t=>t.name=="Overhead_support"))
            {t.position+=Vector3.up*1.25f;t.localScale=new Vector3(.12f,9,.12f);}
            float[] xs={654.7f,660.1f,661.0f,678.4f,684.5f,690.0f};int j=0;
            foreach(Transform t in root)if(t.name=="V19_CROW" && j<6)
            {float x=xs[j];t.position=new Vector3(x,Y(x,662.99f)+2.67f,660.2f+(j%2)*.4f);t.rotation=Quaternion.Euler(0,115+j*43,0);j++;}
            // Decals avoid the original windows and door hardware.
            j=0;foreach(Transform t in root)if(t.name=="V19_GarageGraffiti_v02")
            {t.position+=new Vector3(j<2?.9f:-1.5f,-.22f,-.006f);t.localScale=new Vector3(j<2?1.1f:.8f,.80f,1);j++;}
            var smoke=GameObject.Find("V19_LightChimneySmoke");smoke.transform.position=new Vector3(285.9f,Y(285.9f,535)+4.1f,535);
            var ambience=AssetDatabase.LoadAssetAtPath<AmbienceData>("Assets/OnlyVolunteers/Audio/Resources/Ambience_v19.asset");
            ambience.Spots[1].Position=coop.transform.position+Vector3.up*.5f;ambience.Spots[2].Position=new Vector3(656,Y(656,668)+8,668);EditorUtility.SetDirty(ambience);
            AssetDatabase.SaveAssets();UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            UnityEditor.SceneManagement.EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            return "Terrain tree mesh flattened in metres; garden and Rough details refined";
        }
        static void Detail(string name,float x,float z,float up,float yaw)
        {
            // Model roots retain their FBX import transforms inside a metre-space placement parent.
            var asset=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Art/StyleKit_v3/BuildingDetails/"+name+"_v01.fbx");
            if(!asset)throw new InvalidOperationException("Building detail missing "+name);
            var holder=new GameObject("V19_"+name);holder.transform.SetParent(root,false);holder.transform.position=new Vector3(x,Y(x,z)+up,z);holder.transform.rotation=Quaternion.Euler(0,yaw,0);
            var go=(GameObject)PrefabUtility.InstantiatePrefab(asset);go.transform.SetParent(holder.transform,false);
            foreach(var r in go.GetComponentsInChildren<MeshRenderer>())r.sharedMaterials=Enumerable.Repeat(wireMaterial,r.sharedMaterials.Length).ToArray();
        }
        static Transform Wing(Transform parent,int side)
        {
            var go=new GameObject(side<0?"LeftWing":"RightWing");go.transform.SetParent(parent,false);go.transform.localPosition=new Vector3(side*.08f,.26f,0);
            var mesh=new Mesh{name="V19_CrowWing_"+side};mesh.vertices=new[]{Vector3.zero,new Vector3(side*.36f,0,.05f),new Vector3(side*.21f,0,-.14f)};
            mesh.triangles=new[]{0,1,2,2,1,0};mesh.RecalculateNormals();AssetDatabase.CreateAsset(mesh,AssetDatabase.GenerateUniqueAssetPath(V19PaletteP2.Output+"/CrowWing_"+side+".asset"));
            go.AddComponent<MeshFilter>().sharedMesh=mesh;go.AddComponent<MeshRenderer>().sharedMaterial=crowMaterial;return go.transform;
        }
        static void Wire(Vector3 a,Vector3 b)
        {
            var go=new GameObject("V19_SaggingWire");go.transform.SetParent(root,false);var line=go.AddComponent<LineRenderer>();line.sharedMaterial=wireMaterial;
            line.positionCount=17;line.widthMultiplier=.035f;line.numCornerVertices=1;line.useWorldSpace=true;
            for(int i=0;i<17;i++){float t=i/16f;line.SetPosition(i,Vector3.Lerp(a,b,t)-Vector3.up*(Mathf.Sin(t*Mathf.PI)*.9f));}
        }
        static void Decal(Vector3 p,Vector2 size,int quadrant)
        {
            string path=V19PaletteP2.Output+"/Materials/Decal_v02_"+quadrant+".mat";
            var mat=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!mat)
            {
                mat=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="V19_Decal_"+quadrant};mat.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/OnlyVolunteers/Art/StyleKit_v3/decals_v02/GRAFFITI_TORN_POSTERS_v02.png"));
                mat.SetTextureScale("_BaseMap",new Vector2(.5f,.5f));mat.SetTextureOffset("_BaseMap",new Vector2((quadrant%2)*.5f,(quadrant<2)?.5f:0));
                mat.SetFloat("_AlphaClip",1);mat.SetFloat("_Cutoff",.3f);mat.EnableKeyword("_ALPHATEST_ON");mat.SetFloat("_Cull",0);mat.renderQueue=2450;
                mat.SetFloat("_Smoothness",.04f);AssetDatabase.CreateAsset(mat,path);
            }
            var go=GameObject.CreatePrimitive(PrimitiveType.Quad);go.name="V19_GarageGraffiti_v02";go.transform.SetParent(root,false);go.transform.position=p;go.transform.localScale=new Vector3(size.x,size.y,1);
            go.GetComponent<MeshRenderer>().sharedMaterial=mat;Object.DestroyImmediate(go.GetComponent<Collider>());
        }
    }
}
