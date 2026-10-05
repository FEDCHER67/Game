using OnlyVolunteers.Audio;
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
    // LMB grabs a lying NPC anywhere, at the point of its body under the crosshair (Vadim's PhysicsGrabber on the KCC
    // player; the NPC body hands out the point, on its axis). This script only shows the hint: the zone that would be
    // grabbed ("ЛКМ — взять за голову"; "— тяжело" where one hand cannot lift it, hips and belly), and while holding an
    // NPC, that the mouse wheel moves the hold nearer or farther (the hotbar's wheel is switched off meanwhile).
    // F9 (offline test aid): pins the point under the crosshair at hand height, as if another player held it; F9 within
    // 0.25 m of a pin drops that pin, F9 at nothing drops all of them.
    // E does the most specific thing in reach, in this order: in the cargo bay next to the sliding door, its inside handle
    // (canon section 151); pick up an item (the item draws its own "— E" label); open/close the cargo door on that side
    // (the driver works them with 1-4 and F); get into the driver's seat.
    public sealed class GreyboxInteractor : MonoBehaviour
    {
        public GreyboxPawn Pawn;
        public GreyboxVanSeat Seat;
        public GreyboxVanCargo Cargo;
        public InventoryInput InventoryInput;
        [Tooltip("What Q hits with (Map/Data/Fist.asset). Empty = the fist built in code.")]
        public WeaponStun Weapon;

        private const float ConeAngle = 45f; // the walker's Q
        private const float HitRadius = 0.33f; // m: the first-person swing is a fat sphere, not a thin ray
        private const float ItemReach = 2.5f;
        private const float GrabHintReach = 3f;
        private const float PinReach = 6f;
        private const float PinLift = 0.8f;

        private enum Act { None, Handle, PickupItem, ToggleDoor, Enter }

        private static readonly RaycastHit[] SweepHits = new RaycastHit[16];

        private float _nextHit;
        private Act _act;
        private Act _afterItem; // what E does instead when the item pickup fails (inventory full, cursor free)
        private string _label;
        private int _door = -1;
        private bool _canHit;
        private string _grabHint;
        private PhysicsGrabber _grabber;
        private bool _inventoryMuted; // switched InventoryInput off while an NPC body is held (it cycles slots on the wheel)

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
                if (_canHit)
                {
                    target.Hit(weapon, zone, Pawn.Position, point);
                    Sfx.PlayAt(HitSound(zone), point);
                }
            }

            _grabHint = GrabHint();
            MuteInventoryWheel();
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
                    // The nearest item is what the label showed; the pickup itself goes by Vadim's view ray.
                    OfflineWorldItem item = OfflineWorldItem.Nearest(Pawn.Body.position, ItemReach);
                    bool organ = item != null && item.Definition != null && item.Definition.Kind == ItemKind.Organ;
                    Vector3 at = item != null ? item.transform.position : Pawn.Body.position;
                    if (InventoryInput == null || !InventoryInput.PickupNow()) Do(_afterItem);
                    else if (organ) Sfx.PlayAt(SfxIds.OrganSquish, at);
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

        // What Q would hit now, where, and in which zone. First person: the exact crosshair ray first; if it finds no NPC,
        // a fat sphere (HitRadius) along the same ray, so a swing that just misses (beside the head, past a thin limb)
        // still lands. The sphere's hit must be in plain view of the eye (nothing but that NPC between). The zone comes
        // from where the view ray passes the NPC's body (GreyboxNpc.ZoneAlong), not from the exact contact point.
        private bool FindHit(WeaponStun weapon, out GreyboxNpc npc, out HitZone zone, out Vector3 point)
        {
            npc = null;
            zone = HitZone.Torso;
            point = Vector3.zero;
            Camera view = Pawn.ViewCamera;
            if (view != null)
            {
                Transform eye = view.transform;
                var ray = new Ray(eye.position, eye.forward);
                if (Physics.Raycast(ray, out RaycastHit hit, weapon.Reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore) &&
                    hit.collider.GetComponentInParent<GreyboxNpc>() is GreyboxNpc direct)
                {
                    npc = direct;
                    point = hit.point;
                }
                else if (!SweepHit(ray, weapon.Reach, out npc, out point))
                    return false;
                zone = npc.ZoneAlong(ray);
                return true;
            }
            // Third person (walker): no crosshair, so the nearest NPC in front counts as a torso hit.
            npc = Nearest(weapon.Reach, ConeAngle);
            if (npc == null) return false;
            point = npc.Center;
            return true;
        }

        // The nearest NPC the sphere along 'ray' touches within reach, if the eye sees the touched point.
        private static bool SweepHit(Ray ray, float reach, out GreyboxNpc npc, out Vector3 point)
        {
            npc = null;
            point = Vector3.zero;
            int count = Physics.SphereCastNonAlloc(ray, HitRadius, SweepHits, reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore);
            float best = float.MaxValue;
            for (int i = 0; i < count; i++)
            {
                RaycastHit hit = SweepHits[i];
                SweepHits[i] = default;
                // Overlapping at the start (distance 0, no point): point blank, the plain ray decides those.
                if (hit.distance <= 0f || hit.distance >= best || hit.collider == null) continue;
                GreyboxNpc candidate = hit.collider.GetComponentInParent<GreyboxNpc>();
                if (candidate == null || !InView(ray.origin, hit.point, candidate)) continue;
                npc = candidate;
                point = hit.point;
                best = hit.distance;
            }
            return npc != null;
        }

        private static string HitSound(HitZone zone) => zone switch
        {
            HitZone.Head => SfxIds.HitHead,
            HitZone.Limb => SfxIds.HitLimb,
            _ => SfxIds.HitTorso,
        };

        // Nothing but that NPC's own colliders between the eye and 'target'.
        private static bool InView(Vector3 eye, Vector3 target, GreyboxNpc npc)
        {
            Vector3 to = target - eye;
            float distance = to.magnitude;
            if (distance < 0.05f) return true;
            return !Physics.Raycast(eye, to / distance, out RaycastHit block, distance - 0.03f, OvLayers.ShootMask, QueryTriggerInteraction.Ignore) ||
                   block.collider.GetComponentInParent<GreyboxNpc>() == npc;
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

        // "ЛКМ — взять за голову" when the grabber would get hold of the lying body under the crosshair; while holding an
        // NPC body, the wheel hint.
        private string GrabHint()
        {
            if (_grabber == null || !_grabber.isActiveAndEnabled || Pawn.ViewCamera == null) return null;
            if (_grabber.IsHolding)
                return _grabber.GrabbedBody != null && _grabber.GrabbedBody.TryGetComponent(out GreyboxNpcBody _)
                    ? "колесо — ближе/дальше"
                    : null;
            Transform eye = Pawn.ViewCamera.transform;
            // Same mask as PhysicsGrabber.TryAcquire: everything but VehicleInterior (the van's invisible step ramps).
            if (!Physics.Raycast(eye.position, eye.forward, out RaycastHit hit, GrabHintReach, ~(1 << OvLayers.VehicleInterior),
                    QueryTriggerInteraction.Ignore))
                return null;
            if (hit.rigidbody == null || !hit.rigidbody.TryGetComponent(out GreyboxNpcBody body)) return null;
            if (hit.distance > body.Profile.AcquireDistance) return null;
            string zone = body.GrabHintName(hit.point);
            return zone != null ? $"ЛКМ — взять за {zone}" : null;
        }

        // The wheel moves a held NPC point nearer or farther (PhysicsGrabber) and also cycles Vadim's hotbar
        // (InventoryInput, <Mouse>/scroll/y): while an NPC body is held, InventoryInput is switched off (its OnDisable turns
        // its actions off), and back on once let go. Only what this script switched off is switched back on.
        private void MuteInventoryWheel()
        {
            bool npcHold = _grabber != null && _grabber.IsHolding && _grabber.GrabbedBody != null &&
                           _grabber.GrabbedBody.TryGetComponent(out GreyboxNpcBody _);
            if (npcHold && !_inventoryMuted && InventoryInput != null && InventoryInput.enabled)
            {
                InventoryInput.enabled = false;
                _inventoryMuted = true;
            }
            else if (!npcHold && _inventoryMuted) UnmuteInventory();
        }

        private void UnmuteInventory()
        {
            if (InventoryInput != null) InventoryInput.enabled = true;
            _inventoryMuted = false;
        }

        private void OnDisable()
        {
            if (_inventoryMuted) UnmuteInventory();
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
