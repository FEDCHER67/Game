using System.Collections.Generic;
using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.Clinic
{
    // The Field Clinic loop's patient registry (offline, like the map's NPCs and van). It watches the map's NPCs every
    // frame and keeps one PatientRecord per NPC that was ever knocked down: Available / Captured / Loaded follow what the
    // NPC is doing (GreyboxNpc.State, InCargo); AtBase / InOperation / Resolved are set by the clinic (ClinicDropOff,
    // ClinicOperationRunner). Every change goes through Move, which refuses moves PatientLifecycle does not allow.
    // Rewards: TryResolve pays at most once per id, also across sessions (the ids of finished patients are saved).
    public sealed class PatientRegistry : MonoBehaviour
    {
        private readonly Dictionary<string, PatientRecord> _records = new();
        private readonly HashSet<string> _completed = new();

        public IEnumerable<PatientRecord> Records => _records.Values;
        public IReadOnlyCollection<string> Completed => _completed;
        public int RefusedMoves { get; private set; }

        public event System.Action<PatientRecord, PatientStage> StageChanged;

        public PatientRecord Get(string id) => id != null && _records.TryGetValue(id, out PatientRecord r) ? r : null;

        /// <summary>The network operation uses the same stable registry without creating a crowd-controller copy.</summary>
        public PatientRecord EnsureOperationPatient(string id, OnlyVolunteers.Operation.Stage1.OperationState state)
        {
            if (!_records.TryGetValue(id, out var record))
            {
                record = new PatientRecord(id, state.onTable ? PatientStage.AtBase : PatientStage.Captured);
                _records.Add(id, record);
            }
            record.Operation ??= state;
            return record;
        }

        public bool IsCompleted(string id) => id != null && _completed.Contains(id);

        /// <summary>Save/load: ids of patients that were already paid for.</summary>
        public void LoadCompleted(IEnumerable<string> ids)
        {
            if (ids == null) return;
            foreach (string id in ids)
                if (!string.IsNullOrEmpty(id)) _completed.Add(id);
        }

        /// <summary>The record of this NPC, made (with a new id and a PatientTag) if it has none yet.</summary>
        public PatientRecord Ensure(GreyboxNpc npc)
        {
            if (!npc.TryGetComponent(out PatientTag tag))
            {
                tag = npc.gameObject.AddComponent<PatientTag>();
                tag.PatientId = PatientLifecycle.NewId();
            }
            if (!_records.TryGetValue(tag.PatientId, out PatientRecord record))
            {
                record = new PatientRecord(tag.PatientId, PatientStage.Available);
                _records.Add(record.Id, record);
            }
            return record;
        }

        public static string IdOf(GreyboxNpc npc) => npc != null && npc.TryGetComponent(out PatientTag tag) ? tag.PatientId : null;

        /// <summary>One lifecycle step; false (and a warning) if PatientLifecycle forbids it.</summary>
        public bool Move(PatientRecord record, PatientStage to)
        {
            if (record == null) return false;
            if (record.Stage == to) return true;
            if (!PatientLifecycle.CanMove(record.Stage, to))
            {
                RefusedMoves++;
                Debug.LogWarning($"[Clinic] refused patient move {record.Id}: {record.Stage} -> {to}");
                return false;
            }
            PatientStage from = record.Stage;
            record.Stage = to;
            Debug.Log($"[Clinic] patient {record.Id}: {from} -> {to}");
            StageChanged?.Invoke(record, from);
            return true;
        }

        /// <summary>InOperation -> Resolved and the reward amount recorded, exactly once per id. False when this id was
        /// resolved or paid before (in this session or a saved one): the caller must not pay again.</summary>
        public bool TryResolve(PatientRecord record, int reward)
        {
            if (record == null) return false;
            bool repeat = record.Rewarded || _completed.Contains(record.Id);
            if (!Move(record, PatientStage.Resolved)) return false; // (already Resolved counts as moved)
            if (repeat)
            {
                Debug.LogWarning($"[Clinic] patient {record.Id} was already paid for: no second reward");
                return false;
            }
            record.Rewarded = true;
            record.Reward = reward;
            _completed.Add(record.Id);
            return true;
        }

        private void Update()
        {
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || !npc.isActiveAndEnabled) continue;
                PatientStage seen = Observed(npc);
                string id = IdOf(npc);
                if (id == null && seen == PatientStage.Available) continue; // a free NPC that was never caught
                PatientRecord record = Ensure(npc);
                if (record.Stage == seen || record.Stage >= PatientStage.AtBase) continue;
                // Knocked down inside the van at once (rare): Available -> Captured -> Loaded, one allowed step each.
                if (record.Stage == PatientStage.Available && seen == PatientStage.Loaded) Move(record, PatientStage.Captured);
                Move(record, seen);
            }
        }

        // What the NPC itself shows: in a cargo bay (lying or sitting) = Loaded; lying elsewhere = Captured; else free.
        private static PatientStage Observed(GreyboxNpc npc)
        {
            if (npc.InCargo) return PatientStage.Loaded;
            return npc.State == NpcState.Down ? PatientStage.Captured : PatientStage.Available;
        }
    }
}
