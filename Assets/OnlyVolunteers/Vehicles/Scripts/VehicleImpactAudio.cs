using System;
using System.Collections.Generic;
using KinematicCharacterController;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Police;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Local presentation: the bootstrap finds placed vans and cars, and periodically finds newly spawned police cars.
    [DisallowMultipleComponent]
    public sealed class VehicleImpactAudio : MonoBehaviour
    {
        private const float MinimumImpact = 1.5f;
        private const float HeavyImpact = 6f;
        private const float Cooldown = 0.15f;
        private const int CacheLimit = 256;

        private enum ImpactMaterial : byte { Metal, Wood, Concrete, Plastic, Glass, Foliage }

        private static VehicleImpactAudio _bootstrap;
        private readonly Dictionary<Collider, ImpactMaterial> _materials = new(CacheLimit);
        private Rigidbody _body;
        private bool _scanner;
        private float _nextScan;
        private float _nextSound;
        private float _lastSoundStep = -1f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => _bootstrap = null;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (_bootstrap != null) return;
            var root = new GameObject("Vehicle impact audio bootstrap");
            DontDestroyOnLoad(root);
            _bootstrap = root.AddComponent<VehicleImpactAudio>();
            _bootstrap.ScanScene();
        }

        private void Awake()
        {
            if (!TryGetComponent(out _body) ||
                (!TryGetComponent<VanController>(out _) && !TryGetComponent<PoliceCarMotor>(out _)))
            {
                _scanner = true;
                return;
            }

            // Compound Rigidbody colliders normally report to the root. Forwarders also cover child callbacks.
            Collider[] children = GetComponentsInChildren<Collider>(true);
            for (int i = 0; i < children.Length; i++)
            {
                Collider child = children[i];
                if (child == null || child.isTrigger || child.gameObject == gameObject || child.attachedRigidbody != _body)
                    continue;
                if (!child.TryGetComponent(out VehicleImpactAudioForwarder forwarder))
                    forwarder = child.gameObject.AddComponent<VehicleImpactAudioForwarder>();
                forwarder.Bind(this);
            }
        }

        private void Update()
        {
            if (_scanner && Time.time >= _nextScan) ScanScene();
        }

        private void ScanScene()
        {
            _nextScan = Time.time + 2f;
            foreach (VanController van in FindObjectsByType<VanController>())
                if (van != null && van.TryGetComponent<Rigidbody>(out _) &&
                    !van.TryGetComponent<VehicleImpactAudio>(out _))
                    van.gameObject.AddComponent<VehicleImpactAudio>();
            foreach (PoliceCarMotor police in FindObjectsByType<PoliceCarMotor>())
                if (police != null && police.TryGetComponent<Rigidbody>(out _) &&
                    !police.TryGetComponent<VehicleImpactAudio>(out _))
                    police.gameObject.AddComponent<VehicleImpactAudio>();
        }

        private void OnCollisionEnter(Collision collision) => Handle(collision);

        internal void ForwardCollisionEnter(Collision collision) => Handle(collision);

        private void Handle(Collision collision)
        {
            if (_scanner || _body == null || collision.contactCount == 0 ||
                Time.fixedTime == _lastSoundStep || Time.time < _nextSound) return;

            Collider other = collision.collider;
            if (other != null && other.attachedRigidbody == _body)
            {
                ContactPoint first = collision.GetContact(0);
                other = first.thisCollider == other ? first.otherCollider : first.thisCollider;
            }
            if (other == null || IsOwnPart(other) || IsPerson(other) || IsGround(other)) return;

            Vector3 velocity = collision.relativeVelocity;
            float speed = 0f;
            Vector3 point = collision.GetContact(0).point;
            for (int i = 0; i < collision.contactCount; i++)
            {
                ContactPoint contact = collision.GetContact(i);
                float normalSpeed = Mathf.Abs(Vector3.Dot(velocity, contact.normal));
                if (normalSpeed <= speed) continue;
                speed = normalSpeed;
                point = contact.point;
            }
            if (speed < MinimumImpact) return;

            ImpactMaterial material = Classify(other, point);
            bool heavy = speed >= HeavyImpact;
            string id = SoundId(material, heavy);
            float volume = heavy
                ? Mathf.Lerp(0.8f, 1f, Mathf.InverseLerp(HeavyImpact, 14f, speed))
                : Mathf.Lerp(0.35f, 0.8f, Mathf.InverseLerp(MinimumImpact, HeavyImpact, speed));
            if (!Sfx.PlayAt(id, point, volume)) return;
            _lastSoundStep = Time.fixedTime;
            _nextSound = Time.time + Cooldown;
        }

        private bool IsOwnPart(Collider other) => other.attachedRigidbody == _body || other.transform.IsChildOf(transform);

        private static bool IsPerson(Collider other)
        {
            int layer = other.gameObject.layer;
            if (layer == OvLayers.Player || layer == OvLayers.RemotePlayer ||
                layer == OvLayers.NpcBody || layer == OvLayers.NpcSeated || layer == OvLayers.NpcSlide)
                return true;
            return other.GetComponentInParent<GreyboxNpc>() != null ||
                   other.GetComponentInParent<GreyboxNpcBody>() != null ||
                   other.GetComponentInParent<NpcRagdollPart>() != null ||
                   other.GetComponentInParent<GreyboxKccPawn>() != null ||
                   other.GetComponentInParent<KinematicCharacterMotor>() != null;
        }

        private static bool IsGround(Collider other)
        {
            if (other is TerrainCollider) return true;
            for (Transform t = other.transform; t != null; t = t.parent)
            {
                string name = t.name;
                if (Starts(name, "Road_") || Starts(name, "RoadMesh") ||
                    Starts(name, "Ground_") || Starts(name, "Terrain")) return true;
            }
            return false;
        }

        private ImpactMaterial Classify(Collider other, Vector3 point)
        {
            if (_materials.TryGetValue(other, out ImpactMaterial cached)) return cached;
            ImpactMaterial result;
            PhysicsMaterial physicsMaterial = other.sharedMaterial;
            if (physicsMaterial != null && NameMaterial(physicsMaterial.name, out result))
                return Remember(other, result);

            for (Transform t = other.transform; t != null; t = t.parent)
                if (NameMaterial(t.name, out result)) return Remember(other, result);

            // SfxSurfaces has a useful material-name fallback for unlabelled map colliders.
            SfxSurface surface = SfxSurfaces.At(other, point);
            if (surface == SfxSurface.Metal) return Remember(other, ImpactMaterial.Metal);
            if (surface == SfxSurface.Grass) return Remember(other, ImpactMaterial.Foliage);

            Rigidbody body = other.attachedRigidbody;
            result = body == null ? ImpactMaterial.Concrete :
                body.mass > 300f ? ImpactMaterial.Metal :
                body.mass < 30f ? ImpactMaterial.Plastic : ImpactMaterial.Concrete;
            return Remember(other, result);
        }

        private ImpactMaterial Remember(Collider other, ImpactMaterial material)
        {
            if (_materials.Count >= CacheLimit) _materials.Clear();
            _materials[other] = material;
            return material;
        }

        private static bool NameMaterial(string name, out ImpactMaterial material)
        {
            // Specific compound names precede broad words. These include MapArtSetup prefab names and the greybox names.
            if (Has(name, "powerpole_wood") || Has(name, "fn_wood") || Has(name, "fence_wood") ||
                Has(name, "bench") || Has(name, "crate") || Has(name, "plank") || Has(name, "wood"))
                { material = ImpactMaterial.Wood; return true; }
            if (Has(name, "powerpole_concrete") || Has(name, "sovietconcrete") ||
                Has(name, "trashbin_concrete") || Has(name, "fn_concrete") || Has(name, "fence_concrete") ||
                Has(name, "kerb") || Has(name, "curb") || Has(name, "building") || Has(name, "wall") ||
                Has(name, "stone") || Has(name, "rock") || Has(name, "planter") || Has(name, "concrete"))
                { material = ImpactMaterial.Concrete; return true; }
            if (Has(name, "glass") || Has(name, "window") || Has(name, "glazed") || Has(name, "busstop_shelter"))
                { material = ImpactMaterial.Glass; return true; }
            if (Has(name, "bush") || Has(name, "hedge") || Has(name, "tree") || Has(name, "leaves") ||
                Has(name, "foliage") || Has(name, "shrub"))
                { material = ImpactMaterial.Foliage; return true; }
            if (Has(name, "garbage_container"))
                { material = ImpactMaterial.Metal; return true; }
            if (Has(name, "trashbin") || Has(name, "bin_") ||
                Has(name, "cone") || Has(name, "plastic") || Has(name, "chair"))
                { material = ImpactMaterial.Plastic; return true; }
            if (Has(name, "lamp") || Has(name, "lp_oldtown") || Has(name, "pole") ||
                Has(name, "sign") || Has(name, "rail") || Has(name, "elitefence") || Has(name, "fn_elite") ||
                Has(name, "parking_barrier") || Has(name, "car_") || Has(name, "vk_car") ||
                Has(name, "vehicle") || Has(name, "metal") || Has(name, "steel") || Has(name, "iron"))
                { material = ImpactMaterial.Metal; return true; }
            material = default;
            return false;
        }

        private static bool Has(string value, string word) =>
            !string.IsNullOrEmpty(value) && value.IndexOf(word, StringComparison.OrdinalIgnoreCase) >= 0;

        private static bool Starts(string value, string prefix) =>
            value != null && value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase);

        private static string SoundId(ImpactMaterial material, bool heavy) => material switch
        {
            ImpactMaterial.Metal => heavy ? SfxIds.VanHitMetalHeavy : SfxIds.VanHitMetalLight,
            ImpactMaterial.Wood => SfxIds.VanHitWood,
            ImpactMaterial.Plastic => SfxIds.VanHitPlastic,
            ImpactMaterial.Glass => SfxIds.VanHitGlass,
            ImpactMaterial.Foliage => SfxIds.VanHitFoliage,
            _ => SfxIds.VanHitConcrete,
        };
    }

    // Added only to compound-collider children; the root also receives collisions on normal Unity Rigidbody setups.
    [DisallowMultipleComponent]
    internal sealed class VehicleImpactAudioForwarder : MonoBehaviour
    {
        private VehicleImpactAudio _owner;
        internal void Bind(VehicleImpactAudio owner) => _owner = owner;
        private void OnCollisionEnter(Collision collision)
        {
            if (_owner != null && _owner.isActiveAndEnabled) _owner.ForwardCollisionEnter(collision);
        }
    }
}
