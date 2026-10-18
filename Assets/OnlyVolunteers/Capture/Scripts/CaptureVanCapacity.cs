using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>Stock van capacity (spec §4, D5, CD-08): 3 lying NPCs. With more bodies inside the cargo box the cargo
    /// doors refuse to close (they bounce back open) and the van refuses to drive off: the engine coughs and stalls,
    /// «Тесно, не влезает». Runs after the driver's and the on-foot door input in the same frame, so it only overrides
    /// their requests; the van, its doors and the cargo logic are unchanged. Cargo-body upgrades (+1 per level, up to 5)
    /// are stage B: Capacity is the hook.</summary>
    [DefaultExecutionOrder(200)]
    [RequireComponent(typeof(VanController))]
    public sealed class CaptureVanCapacity : MonoBehaviour
    {
        public int Capacity = 3;
        public float CoughInterval = 1.3f;

        private VanController van;
        private Rigidbody vanBody;
        private GreyboxVanCargo cargo;
        private GreyboxVanSeat seat;
        private VanCargoSpace space;
        private float nextCough;
        private float nextHint;
        public int BodiesInside { get; private set; }
        public bool Overloaded => BodiesInside > Capacity;
        public int RefusedDoors { get; private set; }
        public int Stalls { get; private set; }

        private void Awake()
        {
            van = GetComponent<VanController>();
            vanBody = GetComponent<Rigidbody>();
            cargo = GetComponent<GreyboxVanCargo>();
            seat = GetComponent<GreyboxVanSeat>();
        }

        private void Update()
        {
            if (space == null && !TryGetComponent(out space)) return;
            BodiesInside = Count();
            if (!Overloaded) return;
            // The doors: a cargo door asked to close bounces back open.
            if (cargo != null)
            {
                Refuse(cargo.Slide);
                Refuse(cargo.RearLeft);
                Refuse(cargo.RearRight);
            }
            // Driving off: no throttle, a cough and a shake.
            if (seat != null && seat.Driving && Mathf.Abs(van.Throttle) > 0.01f && Mathf.Abs(van.SpeedKmh) < 8f)
            {
                van.Throttle = 0f;
                van.Handbrake = true;
                if (Time.time >= nextCough)
                {
                    nextCough = Time.time + CoughInterval;
                    Stalls++;
                    CaptureSounds.Cough(transform.position);
                    if (vanBody != null) vanBody.AddRelativeTorque(new Vector3(0.6f, 0f, 0.4f) * vanBody.mass * 0.9f, ForceMode.Impulse);
                    Say();
                    Debug.Log($"[CAPTURE] van stalls: {BodiesInside} bodies inside, capacity {Capacity}");
                }
            }
        }

        private void Refuse(VanDoor door)
        {
            if (door == null || door.TargetOpen || door.Openness <= 0.02f) return;
            door.Request(true);
            RefusedDoors++;
            Say();
            Debug.Log($"[CAPTURE] door {door.name} refuses to close: {BodiesInside} bodies inside, capacity {Capacity}");
        }

        private void Say()
        {
            if (Time.time < nextHint) return;
            nextHint = Time.time + 1.2f;
            CaptureDirector.Instance?.Toast($"Тесно, не влезает! ({BodiesInside} из {Capacity}) — вытащи одного", CaptureHud.Warn);
        }

        /// <summary>NPC bodies inside the cargo box: loaded ones, and any lying or sitting body whose pelvis is in it.</summary>
        public int Count()
        {
            int n = 0;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null || !npc.isActiveAndEnabled) continue;
                if (npc.InCargo && ReferenceEquals(npc.Carrier, space)) { n++; continue; }
                INpcBody body = npc.PhysicalBody;
                if (body != null && body.Active && space.Contains(body.Landmark(NpcLandmark.Pelvis))) n++;
                else if (npc.Body != null && npc.Body.Active && npc.Body.Seated && space.Contains(npc.Center)) n++;
            }
            return n;
        }
    }
}
