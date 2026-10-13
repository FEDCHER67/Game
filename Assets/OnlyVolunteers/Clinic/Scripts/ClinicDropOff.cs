using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.Clinic
{
    // The base's receiving pad (Field Clinic loop, step "unload"): unloading stays physical (the players drag the body out
    // of the van with LMB, GreyboxVanCargo unloads it); a captured patient left lying in the pad's circle is handed over:
    // pelvis inside the circle, down (State Down), not in a cargo bay, nobody holding it and not flying (every body slower
    // than RestSpeed) for HoldSeconds. A Groggy body may kick and crawl meanwhile (loop run 1: a strict "at rest" rule
    // never let a Groggy patient be handed over before he woke up and ran). Then the record moves Captured -> AtBase, the starting grade comes from its
    // Condition, the NPC object is removed (no living copy next to the table's stand-in) and ClinicStation lays the
    // stand-in on the table. While the table is taken nothing is handed over ("стол занят").
    public sealed class ClinicDropOff : MonoBehaviour
    {
        public float HoldSeconds = 0.75f;
        public float RestSpeed = 1.5f;
        public float MaxHeight = 1.5f;

        private static readonly System.Func<Vector3, Vector3> StillGround = _ => Vector3.zero;

        private readonly Dictionary<GreyboxNpc, float> _restFor = new();
        private readonly List<GreyboxNpc> _gone = new();
        private PatientRegistry _registry;
        private ClinicStation _station;
        private float _busyToastAt;

        /// <summary>Something on the pad is being handed over (for the lamp and the HUD).</summary>
        public bool Settling { get; private set; }
        public string LastRefusal { get; private set; } = "";

        public event System.Action<PatientRecord> Admitted;

        public void Init(PatientRegistry registry, ClinicStation station)
        {
            _registry = registry;
            _station = station;
        }

        private void Update()
        {
            if (_registry == null || _station == null) return;
            Settling = false;
            float dt = Time.deltaTime;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || !npc.isActiveAndEnabled) continue;
                PatientRecord record = _registry.Get(PatientRegistry.IdOf(npc));
                if (!OnPad(npc, record))
                {
                    _restFor.Remove(npc);
                    continue;
                }
                Settling = true;
                INpcBody body = npc.PhysicalBody;
                bool still = body.HolderCount == 0 && body.MaxRelativeSpeed(StillGround) < RestSpeed;
                float rest = still ? (_restFor.TryGetValue(npc, out float r) ? r : 0f) + dt : 0f;
                _restFor[npc] = rest;
                if (rest < HoldSeconds) continue;
                if (_station.Busy)
                {
                    LastRefusal = "Стол занят: сначала прооперируй пациента на столе";
                    if (Time.time >= _busyToastAt)
                    {
                        _busyToastAt = Time.time + 3f;
                        Sfx.PlayAt(SfxIds.UiError, _station.PadCenter);
                    }
                    continue;
                }
                Admit(npc, record);
                break; // GreyboxNpc.All changed (the NPC is gone)
            }
            // Forget timers of NPCs that were destroyed meanwhile.
            _gone.Clear();
            foreach (GreyboxNpc npc in _restFor.Keys)
                if (npc == null) _gone.Add(npc);
            foreach (GreyboxNpc npc in _gone) _restFor.Remove(npc);
        }

        // A captured patient's downed body with its pelvis inside the pad's circle.
        private bool OnPad(GreyboxNpc npc, PatientRecord record)
        {
            if (record == null || record.Stage != PatientStage.Captured) return false;
            if (npc.State != NpcState.Down || npc.InCargo) return false;
            INpcBody body = npc.PhysicalBody;
            if (body == null || !body.Active) return false;
            Vector3 pelvis = body.Landmark(NpcLandmark.Pelvis);
            Vector3 center = _station.PadCenter;
            Vector3 flat = new(pelvis.x - center.x, 0f, pelvis.z - center.z);
            return flat.magnitude <= _station.PadRadius && Mathf.Abs(pelvis.y - center.y) <= MaxHeight;
        }

        private void Admit(GreyboxNpc npc, PatientRecord record)
        {
            record.Condition = npc.Condition;
            record.Quality = PatientLifecycle.QualityFor(npc.Condition);
            if (!_registry.Move(record, PatientStage.AtBase)) return;
            Color shirt = ShirtColor(npc);
            _restFor.Remove(npc);
            // One owner from here on: the NPC object (controller, ragdoll, animator) goes away with its body.
            npc.gameObject.SetActive(false);
            Destroy(npc.gameObject);
            _station.Admit(record, shirt);
            LastRefusal = "";
            Admitted?.Invoke(record);
        }

        // The stand-in wears roughly the NPC's top colour (its first renderer's material), else a plain blue.
        private static Color ShirtColor(GreyboxNpc npc)
        {
            foreach (Renderer r in npc.GetComponentsInChildren<Renderer>())
            {
                Material m = r.sharedMaterial;
                if (m == null || r is ParticleSystemRenderer) continue;
                if (m.name.IndexOf("Tee", System.StringComparison.OrdinalIgnoreCase) < 0 &&
                    m.name.IndexOf("Shirt", System.StringComparison.OrdinalIgnoreCase) < 0 &&
                    m.name.IndexOf("Hoodie", System.StringComparison.OrdinalIgnoreCase) < 0) continue;
                if (m.HasProperty("_BaseColor")) return m.GetColor("_BaseColor");
                return m.color;
            }
            return new Color(0.25f, 0.55f, 0.75f);
        }
    }
}
