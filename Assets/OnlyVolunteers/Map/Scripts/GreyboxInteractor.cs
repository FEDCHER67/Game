using OnlyVolunteers.Inventory;
using OnlyVolunteers.Player.Physics;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // On-foot keys for the grey-box pawn (on pawn.Body, next to InventoryInput, which leaves E to this script).
    // NPC capture stage 1: no carry or load key any more; downed NPCs are physical bodies.
    // Q hits with the current weapon (WeaponStun, the fist for now). The first-person KCC player hits what the camera ray
    // finds within the weapon's reach (OvLayers.ShootMask skips our own capsule), and the height of that point on the NPC
    // picks the zone (head / torso / limbs), which sets how long it stays down. The third-person walker has no crosshair:
    // it hits the nearest NPC in a cone in front, as a torso hit. The player only ever sees the weapon's strength as dots.
    // LMB drags a lying NPC by the point nearest to the crosshair (Vadim's PhysicsGrabber on the KCC player; the NPC body
    // hands out the points). This script only shows that hint.
    // F9 (offline test aid): pins the grab point under the crosshair at hand height, as if another player held it; F9 on
    // a pinned point drops that pin, F9 at nothing drops all of them.
    // E does the most specific thing in reach, in this order: in the cargo bay next to the sliding door, its inside handle
    // (canon section 151); pick up an item (the item draws its own "— E" label); open/close the cargo door on that side
    // (rear doors by hand only, the driver has just the sliding door); get into the driver's seat.
    public sealed class GreyboxInteractor : MonoBehaviour
    {
        public GreyboxPawn Pawn;
        public GreyboxVanSeat Seat;
        public GreyboxVanCargo Cargo;
        public InventoryInput InventoryInput;
        [Tooltip("What Q hits with (Map/Data/Fist.asset). Empty = the fist built in code.")]
        public WeaponStun Weapon;

        private const float ConeAngle = 45f; // the walker's Q
        private const float ItemReach = 2.5f;
        private const float GrabHintReach = 3f;
        private const float PinReach = 6f;
        private const float PinLift = 0.8f;

        private enum Act { None, Handle, PickupItem, ToggleDoor, Enter }

        private float _nextHit;
        private Act _act;
        private Act _afterItem; // what E does instead when the item pickup fails (inventory full, cursor free)
        private string _label;
        private int _door = -1;
        private bool _canHit;
        private string _grabHint;
        private PhysicsGrabber _grabber;

        public WeaponStun CurrentWeapon => Weapon != null ? Weapon : WeaponStun.Fist;

        private void Start()
        {
            // Scenes built before this script (GreyboxVanSeat adds it) have the inventory's own E still on: take it over.
            if (InventoryInput == null && Pawn != null) Pawn.Body.TryGetComponent(out InventoryInput);
            if (InventoryInput != null) InventoryInput.ExternalPickup = true;
            // The KCC player's grabber sits on its root, next to KccFirstPersonInput (MapGreyboxBuilder adds it).
            if (Pawn != null) _grabber = Pawn.GetComponentInChildren<PhysicsGrabber>(true);
            if (Pawn is GreyboxKccPawn && _grabber == null)
                Debug.LogWarning("[Greybox] The KCC player has no PhysicsGrabber: rebuild the map scene to drag NPC bodies with LMB.");
        }

        private void Update()
        {
            if (Pawn == null) return;

            WeaponStun weapon = CurrentWeapon;
            _canHit = FindHit(weapon, out GreyboxNpc target, out HitZone zone, out Vector3 point);
            if (Input.GetKeyDown(KeyCode.Q) && Time.time >= _nextHit)
            {
                _nextHit = Time.time + weapon.Cooldown;
                if (_canHit) target.Hit(weapon, zone, Pawn.Position, point);
            }

            _grabHint = GrabHint();
            if (Input.GetKeyDown(KeyCode.F9)) TogglePin();

            (_act, _label) = Resolve();
            if (Input.GetKeyDown(KeyCode.E) && GreyboxInput.EFree) Do(_act);
        }

        private (Act, string) Resolve()
        {
            // Inside the bay the handle wins: the door is right there and nothing else in reach matters more.
            if (Cargo != null && Cargo.AtInsideHandle(Pawn.Position))
                return (Act.Handle, Cargo.DoorOpen(0) ? "E — закрыть сдвижную дверь (ручка)" : "E — открыть сдвижную дверь (ручка)");
            _door = Cargo != null ? Cargo.NearestDoor(Pawn.Position) : -1;
            Act below = _door >= 0 ? Act.ToggleDoor : Seat != null && Seat.CanEnter ? Act.Enter : Act.None;
            // The item carries its own "— E" label; if it cannot be picked up, E falls through to the act below.
            if (OfflineWorldItem.Nearest(Pawn.Body.position, ItemReach) != null)
            {
                _afterItem = below;
                return (Act.PickupItem, null);
            }
            return below switch
            {
                Act.ToggleDoor => (Act.ToggleDoor, $"E — {(Cargo.DoorOpen(_door) ? "закрыть" : "открыть")} {Cargo.DoorName(_door)}"),
                Act.Enter => (Act.Enter, "E — сесть в бусик"),
                _ => (Act.None, null),
            };
        }

        private void Do(Act act)
        {
            switch (act)
            {
                case Act.PickupItem:
                    if (InventoryInput == null || !InventoryInput.PickupNow()) Do(_afterItem);
                    break;
                case Act.Handle:
                    Cargo.ToggleDoor(0);
                    break;
                case Act.ToggleDoor:
                    Cargo.ToggleDoor(_door);
                    break;
                case Act.Enter:
                    Seat.Enter();
                    break;
            }
        }

        // ---------- Q ----------

        // What Q would hit now, where, and in which zone.
        private bool FindHit(WeaponStun weapon, out GreyboxNpc npc, out HitZone zone, out Vector3 point)
        {
            npc = null;
            zone = HitZone.Torso;
            point = Vector3.zero;
            Camera view = Pawn.ViewCamera;
            if (view != null)
            {
                Transform eye = view.transform;
                if (!Physics.Raycast(eye.position, eye.forward, out RaycastHit hit, weapon.Reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore))
                    return false;
                npc = hit.collider.GetComponentInParent<GreyboxNpc>();
                if (npc == null) return false;
                point = hit.point;
                zone = npc.ZoneAt(point);
                return true;
            }
            // Third person (walker): no crosshair, so the nearest NPC in front counts as a torso hit.
            npc = Nearest(weapon.Reach, ConeAngle);
            if (npc == null) return false;
            point = npc.Center;
            return true;
        }

        // Nearest NPC within reach and within 'angle' of the walker's flat facing.
        private GreyboxNpc Nearest(float reach, float angle)
        {
            Vector3 from = Pawn.Position;
            Vector3 facing = Flat(Pawn.Body.forward);
            GreyboxNpc best = null;
            float bestDistance = reach;
            foreach (GreyboxNpc npc in GreyboxNpc.All)
            {
                if (npc == null) continue;
                Vector3 to = Flat(npc.Center - from);
                float distance = to.magnitude;
                if (distance > bestDistance) continue;
                if (distance > 0.3f && facing.sqrMagnitude > 0.0001f && Vector3.Angle(facing, to) > angle) continue;
                best = npc;
                bestDistance = distance;
            }
            return best;
        }

        // ---------- LMB hint, F9 pins ----------

        // "ЛКМ — схватить (шиворот)" when the grabber would get a point of the lying body under the crosshair.
        private string GrabHint()
        {
            if (_grabber == null || !_grabber.isActiveAndEnabled || _grabber.IsHolding || Pawn.ViewCamera == null) return null;
            Transform eye = Pawn.ViewCamera.transform;
            if (!Physics.Raycast(eye.position, eye.forward, out RaycastHit hit, GrabHintReach, ~0, QueryTriggerInteraction.Ignore))
                return null;
            if (hit.rigidbody == null || !hit.rigidbody.TryGetComponent(out GreyboxNpcBody body)) return null;
            if (hit.distance > body.Profile.AcquireDistance) return null;
            string point = body.FreePointName(hit.point);
            return point != null ? $"ЛКМ — схватить ({point})" : null;
        }

        private void TogglePin()
        {
            Ray ray;
            if (Pawn.ViewCamera != null) ray = new Ray(Pawn.ViewCamera.transform.position, Pawn.ViewCamera.transform.forward);
            else if (Camera.main != null) ray = Camera.main.ViewportPointToRay(new Vector3(0.5f, 0.5f, 0f));
            else return;
            if (Physics.Raycast(ray, out RaycastHit hit, PinReach, OvLayers.NpcMask, QueryTriggerInteraction.Ignore) &&
                hit.rigidbody != null && hit.rigidbody.TryGetComponent(out GreyboxNpcBody body))
            {
                body.TogglePin(hit.point, PinLift);
                return;
            }
            foreach (GreyboxNpc npc in GreyboxNpc.All)
                if (npc != null && npc.Body != null) npc.Body.UnpinAll();
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);

        private void OnGUI()
        {
            string hint = _label;
            if (_grabHint != null) hint = hint == null ? _grabHint : $"{hint}     {_grabHint}";
            if (_canHit)
            {
                // Strength dots only, never seconds (canon section 151).
                string q = $"Q — ударить {CurrentWeapon.StrengthDots}";
                hint = hint == null ? q : $"{hint}     {q}";
            }
            if (hint == null) return;
            var style = new GUIStyle(GUI.skin.label) { fontSize = 18, alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0f, Screen.height - 70f, Screen.width - 340f, 30f), hint, style); // left of the trip panel
        }
    }
}
