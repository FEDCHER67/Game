using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 capture: the van's seats and doors for the E throw. Seats sit on the cargo floor with the back to the
    /// wall (van v05 bay from its VanCargoSpace box): three along the left wall facing the sliding door, one at the rear
    /// right, one at the front left. How many are in use = the van's capacity (CaptureVanCapacity: stock 3, the cargo
    /// fit-out raises it to 5). A seated recruit is GreyboxNpc.CargoSeated with SeatBelted (GreyboxVanCargo then never
    /// starts an escape for him); the seat frees itself when he is no longer sitting in this van.</summary>
    [RequireComponent(typeof(GreyboxVanCargo))]
    public sealed class CaptureV2Van : MonoBehaviour
    {
        public const int MaxSeats = 5;
        public const int SlideDoor = 0, RearDoors = 1;

        [System.NonSerialized] public CaptureV2Rig Rig;
        private GreyboxVanCargo _cargo;
        private VanCargoSpace _space;
        private Rigidbody _body;
        private CaptureVanCapacity _capacity;
        private readonly GreyboxNpc[] _seated = new GreyboxNpc[MaxSeats];

        public GreyboxVanCargo Cargo => _cargo != null ? _cargo : _cargo = GetComponent<GreyboxVanCargo>();
        public VanCargoSpace Space => _space != null ? _space : _space = GetComponent<VanCargoSpace>();
        public Rigidbody Body => _body != null ? _body : _body = GetComponent<Rigidbody>();
        public int Seats => Mathf.Clamp(_capacity != null || TryGetComponent(out _capacity) ? _capacity.Capacity : 3, 1, MaxSeats);

        public int Occupied
        {
            get
            {
                int n = 0;
                for (int i = 0; i < Seats; i++) if (_seated[i] != null) n++;
                return n;
            }
        }

        public GreyboxNpc SeatedAt(int seat) => seat >= 0 && seat < MaxSeats ? _seated[seat] : null;

        private void Update()
        {
            for (int i = 0; i < MaxSeats; i++)
            {
                GreyboxNpc npc = _seated[i];
                if (npc == null) continue;
                bool reserved = npc.TryGetComponent(out CaptureV2Npc brain) && brain.ReservedSeat == i && brain.Busy;
                bool sitting = npc.isActiveAndEnabled && npc.State == NpcState.CargoSeated && npc.InCargo && ReferenceEquals(npc.Carrier, Space);
                if (reserved || sitting) continue;
                npc.SeatBelted = false;
                _seated[i] = null;
            }
        }

        /// <summary>The free seat a body thrown through 'door' lands in best (nearest that doorway), -1 = all full.</summary>
        public int FreeSeat(int door)
        {
            int best = -1;
            float bestDistance = float.MaxValue;
            Vector3 doorway = DoorwayLocal(door);
            for (int i = 0; i < Seats; i++)
            {
                if (_seated[i] != null) continue;
                SeatLocal(i, out Vector3 p, out _);
                float d = Vector3.Distance(new Vector3(p.x, 0f, p.z), new Vector3(doorway.x, 0f, doorway.z));
                if (d < bestDistance)
                {
                    bestDistance = d;
                    best = i;
                }
            }
            return best;
        }

        public bool Reserve(int seat, GreyboxNpc npc)
        {
            if (seat < 0 || seat >= Seats || (_seated[seat] != null && _seated[seat] != npc)) return false;
            _seated[seat] = npc;
            return true;
        }

        public void Free(GreyboxNpc npc)
        {
            for (int i = 0; i < MaxSeats; i++)
                if (_seated[i] == npc)
                {
                    _seated[i] = null;
                    if (npc != null) npc.SeatBelted = false;
                }
        }

        /// <summary>Seat root on the cargo floor (van-root space) and its facing (van-local yaw, degrees): the back to the
        /// wall behind it.</summary>
        public void SeatLocal(int seat, out Vector3 local, out float yaw)
        {
            Bounds b = Space != null ? Space.LocalBox : new Bounds(new Vector3(0f, 1.548f, -1.024f), new Vector3(1.84f, 1.983f, 3.539f));
            float back = 0.38f;
            NpcRagdollProfile p = null;
            foreach (GreyboxNpc n in GreyboxNpc.All)
                if (n != null && n.Ragdoll != null && n.Ragdoll.Profile != null) { p = n.Ragdoll.Profile; break; }
            if (p != null) back = Mathf.Clamp(-p.SeatMin.y, 0.25f, 0.5f) + 0.04f; // the seated footprint behind the root (z)
            float left = b.min.x + back, right = b.max.x - back, floor = b.min.y;
            float slideZ = Mathf.Clamp(-0.25f, b.min.z + 0.5f, b.max.z - 0.4f);
            (local, yaw) = seat switch
            {
                0 => (new Vector3(left, floor, slideZ), 90f),
                1 => (new Vector3(left, floor, slideZ - 0.85f), 90f),
                2 => (new Vector3(left, floor, slideZ - 1.7f), 90f),
                3 => (new Vector3(right, floor, slideZ - 1.7f), -90f),
                _ => (new Vector3(left, floor, Mathf.Min(slideZ + 0.75f, b.max.z - 0.35f)), 90f),
            };
        }

        public Vector3 SeatWorld(int seat)
        {
            SeatLocal(seat, out Vector3 l, out _);
            return Space != null ? Space.ToWorld(l) : transform.TransformPoint(l);
        }

        public Quaternion SeatRotation(int seat)
        {
            SeatLocal(seat, out _, out float yaw);
            return (Space != null ? Space.Rotation : transform.rotation) * Quaternion.Euler(0f, yaw, 0f);
        }

        /// <summary>The doorway's middle at floor height (van-local) and its outward normal.</summary>
        public Vector3 DoorwayLocal(int door)
        {
            Bounds b = Space != null ? Space.LocalBox : new Bounds(Vector3.zero, Vector3.one);
            return door == SlideDoor ? new Vector3(b.max.x, b.min.y, Mathf.Clamp(-0.25f, b.min.z + 0.5f, b.max.z - 0.4f))
                                     : new Vector3(0f, b.min.y, b.min.z);
        }

        public Vector3 DoorwayWorld(int door, float above) =>
            Space != null ? Space.ToWorld(DoorwayLocal(door) + Vector3.up * above) : transform.TransformPoint(DoorwayLocal(door));

        public Vector3 Outward(int door) => (Space != null ? Space.Rotation : transform.rotation) * (door == SlideDoor ? Vector3.right : Vector3.back);

        public float CeilingAbove(float floorY) => Space != null ? Space.LocalBox.max.y - Space.LocalBox.min.y : 1.9f;

        /// <summary>The cargo door the player at 'feet' may throw through (within ~2 m of its outside point and open), -1.</summary>
        public int DoorNear(Vector3 feet)
        {
            if (Cargo == null) return -1;
            int door = Cargo.NearestDoor(feet);
            if (door < 0 || !Cargo.DoorOpen(door)) return -1;
            float open = door == SlideDoor ? (Cargo.Slide != null ? Cargo.Slide.Openness : 0f)
                : Mathf.Max(Cargo.RearLeft != null ? Cargo.RearLeft.Openness : 0f, Cargo.RearRight != null ? Cargo.RearRight.Openness : 0f);
            return open > 0.6f ? door : -1;
        }

        /// <summary>The van dips on its springs where he lands and rocks sideways.</summary>
        public void Dip(Vector3 at, Vector3 side, float down, float rock)
        {
            Rigidbody rb = Body;
            if (rb == null) return;
            rb.AddForceAtPosition(Vector3.down * down, at, ForceMode.Impulse);
            Vector3 roof = at + Vector3.up * 1.4f;
            rb.AddForceAtPosition(side.normalized * rock, roof, ForceMode.Impulse);
            rb.WakeUp();
        }
    }
}
