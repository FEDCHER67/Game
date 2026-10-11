using System;
using System.Collections.Generic;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using ClipInfo = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.ClipInfo;

namespace OnlyVolunteers.Characters.Npc
{
    public enum GetUpKind : byte { None, Back, Belly, SitUp, JumpOut }

    // Stage 9, step 3 (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §4.4-§4.5): a ragdoll NPC waking up with a clip
    // instead of popping up. GreyboxNpc adds it next to NpcRagdoll and drives it (NpcState.GettingUp):
    // 1. Settle (Begin): the stun is over, the ragdoll stays until its pelvis is slower than SettleSpeed (at most
    //    SettleMax). Lying on its side (|front . up| < SideLimit) it is first rolled onto the nearer of back or belly
    //    for SideRollTime.
    // 2. The clip by the pelvis's front: up = GetUp_Back (it sits up toward its feet), down = GetUp_Belly (it pushes up
    //    toward its head); the root faces the way the clip ends (NpcRagdoll.StandFacing). The clip's first-frame Hips
    //    (HipsStart, from clips.json) lands on the ragdoll's Hips, the root on the ground under them.
    // 3. Room: the standing CharacterController must fit on the root, where the clip ends; else 0.3 / 0.6 m along and
    //    across the body; else it crawls GetUpCrawlTime and looks again (GetUpRetries times); then the nearest free spot
    //    on rings of 0.9 / 1.2 / 1.5 m (step 4, GPT review finding 2); only with none it gets up where it lies
    //    (Squeezed), accepting the overlap.
    // 4. NpcRagdoll.Deactivate records the pose and removes the bodies, the root moves, the clip plays from frame 0, and the
    //    ragdoll blends the bones from the lying pose into it (WakeBlend, head WakeBlendHead): nothing jumps on screen.
    // 5. Stable (the clip's Stable share, ~70 %, the feet planted): GreyboxNpc switches the CharacterController on (not
    //    earlier: the upright capsule would not match the lying figure). The clip's end: GreyboxNpc's stand-up tail.
    // In a cargo bay (SitUp) the same snapshot starts SitUp_Cargo at once, on the seated capsule (the controller then
    // loops Cargo_Sit_Idle); GreyboxNpc owns the seated visual layout and passes it in.
    // Animator states and numbers come from the rig's NpcRagdollProfile (clip section, written by
    // GreyboxBuddySetup.InstallClips); without them GreyboxNpc keeps the old quick blend (CanGetUp / CanSitUp false).
    // Step 4: Begin(lie) lets a tripped body lie a while first (GreyboxNpc.Stumble, the police officer's trip); JumpOut
    // hops a passenger out of a standing van's cargo door onto the ground (Hopping: the root on an arc, the Cargo_JumpOut
    // clip when installed, else the caller's run), the procedural stand-in for the cloud animators' clip; Installed/Length
    // are the clip hook (a clips.json state of the profile's name is used as soon as the controller has it).
    // Step 5: it owns the Animator from a get-up's or a hop's first frame to its end (Owns; NpcAnimDriver writes nothing
    // meanwhile) and starts its clips through NpcAnimDriver.PlayGetUp (the contract's parameters of that moment, then the
    // clip at frame 0); what the controller plays is the driver's to say (HasState).
    [DisallowMultipleComponent]
    public sealed class NpcGetUp : MonoBehaviour
    {
        public enum Step : byte { None, Settling, Rising, Standing, Hopping }

        // Rings of eight spots farther out, tried when the near spots and the crawls found no room (§4.4 step 4).
        private static readonly float[] FarRings = { 0.9f, 1.2f, 1.5f };
        // The hop's landing: (out, across) offsets from HopReach, metres.
        private static readonly Vector2[] Landings = { new(0f, 0f), new(0.35f, 0f), new(-0.25f, 0f), new(0f, 0.4f), new(0f, -0.4f) };

        // Room tries around the planned root: (along the body, across it), metres (§4.4 step 4).
        private static readonly Vector2[] Spots =
        {
            new(0f, 0f), new(0.3f, 0f), new(-0.3f, 0f), new(0f, 0.3f), new(0f, -0.3f),
            new(0.6f, 0f), new(-0.6f, 0f), new(0f, 0.6f), new(0f, -0.6f),
        };
        private static readonly Collider[] Hits = new Collider[16];
        // A standing NPC must not stand inside anything but the van's query volumes and its NPC body slide.
        private const int BlockMask = ~((1 << OvLayers.VehicleInterior) | OvLayers.NpcSlideMask);
        private const float GroundAbove = 0.6f; // m: the ground probe starts this far above the Hips
        private const float FootLift = 0.07f;   // m: the room test starts this far above the ground (slopes, kerbs)

        /// <summary>The ground under a point at its height, probing from 'above' metres over it and skipping NPCs and the
        /// van (GreyboxNpc.GroundPoint; set in its OnEnable, so a script reload in Play mode restores it).</summary>
        [NonSerialized] public Func<Vector3, float, Vector3> Ground;

        private NpcRagdoll _ragdoll;
        private CharacterController _controller;
        private NpcAnimDriver _anim;
        // Serialized so a script reload in Play mode keeps a get-up going (the component itself survives it).
        [SerializeField, HideInInspector] private Step _step;
        [SerializeField, HideInInspector] private GetUpKind _kind;
        [SerializeField, HideInInspector] private string _state;
        [SerializeField, HideInInspector] private float _time, _seconds, _stable;
        [SerializeField, HideInInspector] private float _settle, _roll, _crawl;
        [SerializeField, HideInInspector] private bool _rolling, _rollUp;
        [SerializeField, HideInInspector] private int _tries;
        [SerializeField, HideInInspector] private float _lie, _apex;
        [SerializeField, HideInInspector] private Vector3 _hopFrom, _hopTo;
        // Step 5, the hop with the Cargo_JumpOut clip: its ground speeds and take-off (HopTiming), the path's length.
        [SerializeField, HideInInspector] private bool _hopClip;
        [SerializeField, HideInInspector] private float _floorSpeed, _runSpeed, _takeOff, _hopLength;
        private const float HopRamp = 0.1f; // s after the take-off in which the clip's ground speed reaches the run's

        public Step Current => _step;
        /// <summary>A get-up clip or the hop out of a van is playing: the Animator is this script's (NpcAnimDriver stays out).</summary>
        public bool Owns => _step == Step.Rising || _step == Step.Standing || _step == Step.Hopping;
        public GetUpKind Kind => _kind;
        /// <summary>Animator state of the clip playing (or played last).</summary>
        public string State => _state;
        /// <summary>Seconds into the clip, its length and its Stable share.</summary>
        public float ClipTime => _time;
        public float ClipSeconds => _seconds;
        public float StableShare => _stable;
        // How the last one went (RagdollSmokeTest, notes): settle time, crawls, how far the root moved off the Hips for
        // room, whether it got up without room, the Hips' height above the floor in the lying pose it blended from.
        public float SettledAfter { get; private set; }
        public int Crawls { get; private set; }
        public float Shift { get; private set; }
        public bool Squeezed { get; private set; }
        public float LyingHips { get; private set; }

        private NpcRagdollProfile Profile
        {
            get
            {
                if (_ragdoll == null) TryGetComponent(out _ragdoll); // asked before this OnEnable ran (GreyboxNpc's)
                return _ragdoll != null ? _ragdoll.Profile : null;
            }
        }

        // OnEnable rather than Awake: it also runs after a script reload in Play mode, which drops these references.
        private void OnEnable()
        {
            if (_ragdoll == null) TryGetComponent(out _ragdoll);
            if (_controller == null) TryGetComponent(out _controller);
            if (_anim == null) TryGetComponent(out _anim);
        }

        private NpcAnimDriver Anim
        {
            get
            {
                if (_anim == null) TryGetComponent(out _anim); // asked before this OnEnable ran (GreyboxNpc's)
                return _anim;
            }
        }

        /// <summary>The rig has the get-up clips and its controller plays them.</summary>
        public bool CanGetUp
        {
            get
            {
                NpcRagdollProfile p = Profile;
                return p != null && p.HasGetUps && HasState(p.GetUpBack.State) && HasState(p.GetUpBelly.State);
            }
        }

        /// <summary>The rig has the cargo sit-up and sit idle clips and its controller plays them.</summary>
        public bool CanSitUp
        {
            get
            {
                NpcRagdollProfile p = Profile;
                return p != null && p.HasSeat && HasState(p.SitUp.State) && HasState(p.SitIdle.State);
            }
        }

        /// <summary>Whether the rig's controller has a clip (= state, clips.json names both alike) of this name.</summary>
        public bool HasState(string state) => Anim != null && Anim.HasClip(state);

        /// <summary>Step 4, the clip hook: the clip's state when the rig's controller has it (a clips.json entry of that
        /// state name), else null (the caller plays its procedural version).</summary>
        public string Installed(ClipInfo clip) => clip != null && HasState(clip.State) ? clip.State : null;

        /// <summary>Its length: the profile's (written by the installer for the roles it knows), else the clip's own.</summary>
        public float Length(ClipInfo clip)
        {
            if (clip == null) return 0f;
            if (clip.Seconds > 0f) return clip.Seconds;
            return Anim != null && !string.IsNullOrEmpty(clip.Role) ? Anim.Seconds(clip.Role) : 0f;
        }

        // ---------- Getting up ----------

        /// <summary>Starts getting up (the ragdoll must be built): settling first; 'lie' seconds of lying still before
        /// that (a trip, step 4).</summary>
        public void Begin(float lie = 0f)
        {
            _step = Step.Settling;
            _kind = GetUpKind.None;
            _state = null;
            _time = _seconds = _stable = 0f;
            _settle = _roll = _crawl = 0f;
            _tries = 0;
            SettledAfter = 0f;
            Crawls = 0;
            Shift = 0f;
            Squeezed = false;
            LyingHips = 0f;
            _lie = Mathf.Max(0f, lie);
            _rolling = false;
            if (_lie <= 0f) DecideRoll();
        }

        // Lying on its side (|front . up| < SideLimit) it is rolled onto the nearer of back or belly first.
        private void DecideRoll()
        {
            float up = _ragdoll.Front.y;
            _rolling = Mathf.Abs(up) < Profile.SideLimit;
            _rollUp = up >= 0f;
            _roll = 0f;
        }

        /// <summary>Knocked down again (or taken over): the get-up stops where it is.</summary>
        public void Cancel() => _step = Step.None;

        /// <summary>Physics tick: the side roll while settling.</summary>
        public void FixedTick()
        {
            if (_step != Step.Settling || !_rolling || _ragdoll == null || !_ragdoll.Active) return;
            NpcRagdollProfile p = Profile;
            _roll += Time.fixedDeltaTime;
            if (_roll > p.SideRollTime)
            {
                _rolling = false;
                return;
            }
            _ragdoll.RollToward(_rollUp, p.SideRollAccel);
        }

        /// <summary>Frame tick: the step after it. Settling -> Rising (the clip started, no collider yet) -> Standing (the
        /// CharacterController may come on) -> None (the clip has ended; also when the ragdoll vanished while settling).</summary>
        public Step Tick(float dt)
        {
            switch (_step)
            {
                case Step.Settling:
                    Settle(dt);
                    break;
                case Step.Rising:
                    _time += dt;
                    if (_time >= _stable * _seconds) _step = Step.Standing;
                    break;
                case Step.Standing:
                    _time += dt;
                    if (_time >= _seconds) _step = Step.None;
                    break;
                case Step.Hopping:
                {
                    _time += dt;
                    float u = Mathf.Clamp01(_time / Mathf.Max(0.05f, _seconds));
                    // The clip's hop: along the street at the clip's own ground speeds (HopDistance); else evenly on an arc.
                    float along = _hopClip ? Mathf.Clamp01(HopDistance(_time) / Mathf.Max(0.01f, _hopLength)) : u;
                    transform.position = Vector3.Lerp(_hopFrom, _hopTo, along) + Vector3.up * (4f * _apex * u * (1f - u));
                    if (u >= 1f) _step = Step.None;
                    break;
                }
            }
            return _step;
        }

        private void Settle(float dt)
        {
            if (_ragdoll == null || !_ragdoll.Active)
            {
                _step = Step.None; // removed from outside: the caller stands it up the old way
                return;
            }
            NpcRagdollProfile p = Profile;
            if (_lie > 0f)
            {
                // A trip: lies still a moment, then settles as usual (the side roll decided now, where it ended up).
                _lie -= dt;
                if (_lie > 0f) return;
                DecideRoll();
                return;
            }
            _settle += dt;
            if (_crawl > 0f)
            {
                _crawl -= dt;
                if (_crawl > 0f) return;
            }
            else
            {
                Rigidbody pelvis = _ragdoll.MainBody;
                bool slow = pelvis == null || pelvis.linearVelocity.magnitude < p.SettleSpeed;
                if (_settle < p.SettleMax && (!slow || _rolling)) return;
                if (SettledAfter <= 0f) SettledAfter = _settle;
            }
            Plan(p, out GetUpKind kind, out Vector3 root, out Quaternion rotation, out Vector3 along, out Vector3 across);
            float probeY = _ragdoll.Hips.position.y;
            foreach (Vector2 o in Spots)
            {
                Vector3 at = root;
                if (o != Vector2.zero)
                {
                    at = root + along * o.x + across * o.y;
                    at = GroundAt(new Vector3(at.x, probeY, at.z));
                }
                if (!Fits(at)) continue;
                Stand(kind, at, rotation, Flat(at - root).magnitude, false);
                return;
            }
            if (_tries < p.GetUpRetries)
            {
                _tries++;
                Crawl(p, root, along);
                _crawl = p.GetUpCrawlTime;
                return;
            }
            // Still no room (§4.4 step 4: "then the nearest free spot"): rings farther out, and only with none of them free
            // where it lies (GPT review 2026-10-07, finding 2: it used to stand up in the obstruction at once).
            foreach (float ring in FarRings)
                for (int k = 0; k < 8; k++)
                {
                    Vector3 d = Quaternion.Euler(0f, 45f * k, 0f) * along;
                    Vector3 at = GroundAt(new Vector3(root.x + d.x * ring, probeY, root.z + d.z * ring));
                    if (!Fits(at)) continue;
                    Stand(kind, at, rotation, Flat(at - root).magnitude, false);
                    return;
                }
            Stand(kind, root, rotation, 0f, true);
        }

        // §4.4 steps 2-4: the clip by the pelvis's front, the facing, and the root under the Hips on the ground.
        private void Plan(NpcRagdollProfile p, out GetUpKind kind, out Vector3 root, out Quaternion rotation, out Vector3 along,
            out Vector3 across)
        {
            bool back = _ragdoll.Front.y >= 0f;
            kind = back ? GetUpKind.Back : GetUpKind.Belly;
            ClipInfo clip = back ? p.GetUpBack : p.GetUpBelly;
            along = Flat(_ragdoll.Landmark(NpcLandmark.Head) - _ragdoll.Landmark(NpcLandmark.Pelvis));
            Vector3 facing = _ragdoll.StandFacing();
            if (facing.sqrMagnitude < 1e-4f) facing = back ? -along : along;
            if (facing.sqrMagnitude < 1e-4f) facing = Flat(transform.forward);
            if (facing.sqrMagnitude < 1e-4f) facing = Vector3.forward;
            facing.Normalize();
            along = along.sqrMagnitude > 1e-4f ? along.normalized : (back ? -facing : facing);
            across = Vector3.Cross(Vector3.up, along);
            rotation = Quaternion.LookRotation(facing);
            Vector3 hips = _ragdoll.Hips.position;
            root = hips - rotation * clip.HipsStart;
            root = GroundAt(new Vector3(root.x, hips.y, root.z));
        }

        // The ground under p (Ground, GreyboxNpc's probe); without one, the highest hit under it that is not this NPC.
        private Vector3 GroundAt(Vector3 p)
        {
            if (Ground != null) return Ground(p, GroundAbove);
            float ground = float.NegativeInfinity;
            foreach (RaycastHit hit in Physics.RaycastAll(p + Vector3.up * GroundAbove, Vector3.down, GroundAbove + 20f, BlockMask,
                         QueryTriggerInteraction.Ignore))
                if (!hit.collider.transform.IsChildOf(transform)) ground = Mathf.Max(ground, hit.point.y);
            if (!float.IsNegativeInfinity(ground)) p.y = ground;
            return p;
        }

        // The standing CharacterController on 'root', lifted FootLift off the ground, overlaps nothing but this NPC.
        private bool Fits(Vector3 root)
        {
            Capsule(root, out Vector3 bottom, out Vector3 top, out float radius);
            int count = Physics.OverlapCapsuleNonAlloc(bottom, top, radius, Hits, BlockMask, QueryTriggerInteraction.Ignore);
            bool fits = true;
            for (int i = 0; i < count; i++)
            {
                if (fits && !Hits[i].transform.IsChildOf(transform)) fits = false;
                Hits[i] = null;
            }
            return fits;
        }

        private void Capsule(Vector3 root, out Vector3 bottom, out Vector3 top, out float radius)
        {
            float height = _controller != null ? _controller.height : 1.5f;
            Vector3 centre = _controller != null ? _controller.center : new Vector3(0f, 0.77f, 0f);
            radius = Mathf.Max(0.05f, (_controller != null ? _controller.radius : 0.3f) - 0.02f);
            float low = Mathf.Max(centre.y - height * 0.5f, 0f) + radius + FootLift;
            float high = Mathf.Max(low, centre.y + height * 0.5f - radius);
            bottom = root + Vector3.up * low;
            top = root + Vector3.up * high;
        }

        // One crawl hop away from what blocks the planned spot (the middle of the blockers' nearest points), else head
        // first: GreyboxNpc's crawl, one hop (NpcRagdoll.Scoot).
        private void Crawl(NpcRagdollProfile p, Vector3 root, Vector3 along)
        {
            Capsule(root, out Vector3 bottom, out Vector3 top, out float radius);
            int count = Physics.OverlapCapsuleNonAlloc(bottom, top, radius, Hits, BlockMask, QueryTriggerInteraction.Ignore);
            Vector3 away = Vector3.zero;
            Vector3 middle = (bottom + top) * 0.5f;
            for (int i = 0; i < count; i++)
            {
                Collider c = Hits[i];
                Hits[i] = null;
                if (c == null || c.transform.IsChildOf(transform)) continue;
                // Collider.ClosestPoint takes primitives and convex meshes only (terrain, concave meshes: their bounds).
                bool exact = c is BoxCollider || c is SphereCollider || c is CapsuleCollider || (c is MeshCollider mesh && mesh.convex);
                Vector3 near = exact ? c.ClosestPoint(middle) : c.bounds.ClosestPoint(middle);
                away += Flat(middle - near);
            }
            if (away.sqrMagnitude < 1e-4f) away = along;
            _ragdoll.Scoot(away.normalized * p.GetUpCrawlPush, p.GetUpCrawlHop);
            Crawls++;
        }

        private void Stand(GetUpKind kind, Vector3 root, Quaternion rotation, float shift, bool squeezed)
        {
            ClipInfo clip = kind == GetUpKind.Back ? Profile.GetUpBack : Profile.GetUpBelly;
            if (SettledAfter <= 0f) SettledAfter = _settle;
            LyingHips = _ragdoll.Hips.position.y - root.y;
            Shift = shift;
            Squeezed = squeezed;
            _ragdoll.Deactivate();
            transform.SetPositionAndRotation(root, rotation);
            Play(kind, clip);
            _kind = kind;
            _step = Step.Rising;
        }

        // The clip from its first frame now (NpcAnimDriver.PlayGetUp), and the clock that runs Rising / Standing.
        private void Play(GetUpKind kind, ClipInfo clip)
        {
            _state = clip.State;
            _seconds = Mathf.Max(0.1f, clip.Seconds);
            _stable = Mathf.Clamp01(clip.Stable);
            _time = 0f;
            if (Anim != null) Anim.PlayGetUp(kind, clip.State);
        }

        // ---------- Out of a standing van (step 4) ----------

        /// <summary>A passenger leaving a standing (slow) van through a cargo door (§4.5, GreyboxNpc.JumpOut): the root hops
        /// from 'start' (the door sill) along 'outward' onto the ground HopReach out (the first of a few spots where the
        /// standing CharacterController fits), on an arc HopApex high, facing out; Tick moves it (Hopping) and ends with None
        /// on landing. The Cargo_JumpOut clip plays when installed (its length sets the time); clip false: none, the run
        /// plays meanwhile (the driver's parameters: panicking at runAfter m/s). Returns the hop's seconds.</summary>
        public float JumpOut(Vector3 start, Vector3 outward, float runAfter, out bool clip)
        {
            NpcRagdollProfile p = Profile;
            Vector3 dir = Flat(outward);
            dir = dir.sqrMagnitude > 1e-6f ? dir.normalized : Flat(transform.forward).normalized;
            Vector3 across = Vector3.Cross(Vector3.up, dir);
            float reach = p != null ? p.HopReach : 0.7f;
            Vector3 land = GroundAt(start + dir * reach);
            foreach (Vector2 o in Landings)
            {
                Vector3 at = GroundAt(start + dir * (reach + o.x) + across * o.y);
                if (!Fits(at)) continue;
                land = at;
                break;
            }
            string state = p != null ? Installed(p.JumpOut) : null;
            float length = state != null ? Length(p.JumpOut) : 0f;
            clip = state != null && length > 0f;
            _hopClip = clip;
            _seconds = clip ? length : p != null ? p.HopSeconds : 0.45f;
            _apex = clip ? 0f : p != null ? p.HopApex : 0.2f;
            _hopFrom = start;
            _hopTo = land;
            if (clip)
            {
                // Step 5: the clip carries the body from the van floor down to the street itself: the root is on the street
                // under the start from the first frame and goes out at the clip's ground speeds; the path ends where the
                // standing controller fits (all of it, else shorter, at least to the landing).
                HopTiming(p, runAfter, out _floorSpeed, out _runSpeed, out _takeOff);
                _hopLength = HopDistance(length);
                float landing = p.JumpOut.Events != null && p.JumpOut.Events.Length >= 2 ? HopDistance(p.JumpOut.Events[1]) : 0.5f * _hopLength;
                _hopFrom = GroundAt(start);
                _hopTo = GroundAt(_hopFrom + dir * _hopLength);
                foreach (float share in new[] { 1f, 0.8f, 0.6f })
                {
                    Vector3 at = GroundAt(_hopFrom + dir * Mathf.Max(landing, _hopLength * share));
                    if (!Fits(at)) continue;
                    _hopTo = at;
                    break;
                }
            }
            _time = 0f;
            _stable = 1f;
            _kind = GetUpKind.JumpOut;
            _step = Step.Hopping;
            _state = clip ? state : null;
            Shift = Flat(_hopTo - _hopFrom).magnitude;
            transform.SetPositionAndRotation(_hopFrom, Quaternion.LookRotation(dir));
            if (Anim != null) Anim.PlayGetUp(GetUpKind.JumpOut, clip ? state : null, runAfter);
            return _seconds;
        }

        /// <summary>Step 5: how far inside the doorway a passenger running for it hands over to the Cargo_JumpOut clip (the
        /// clip itself crawls to the sill at its floor speed until its take-off: GreyboxVanCargo lets it out there); 0
        /// without the clip (the procedural hop starts outside the doorway).</summary>
        public float HopLead
        {
            get
            {
                NpcRagdollProfile p = Profile;
                if (p == null || Installed(p.JumpOut) == null) return 0f;
                HopTiming(p, 0f, out float floor, out _, out float takeOff);
                return floor * takeOff;
            }
        }

        /// <summary>Seconds into the Cargo_JumpOut clip at which it lands (its second event), or -1 (no clip, no event).</summary>
        public float LandAt
        {
            get
            {
                NpcRagdollProfile p = Profile;
                return _hopClip && p != null && p.JumpOut.Events != null && p.JumpOut.Events.Length >= 2 ? p.JumpOut.Events[1] : -1f;
            }
        }

        // The JumpOut clip's ground speeds: the crawl's on the van floor (the Scramble clip's authored speed) until the
        // take-off (JumpOut's first event), then within HopRamp the run's (JumpOut's own speed, else the flight's).
        private static void HopTiming(NpcRagdollProfile p, float runAfter, out float floor, out float run, out float takeOff)
        {
            floor = p.Scramble.Speed > 0f ? p.Scramble.Speed : 1.2f;
            run = p.JumpOut.Speed > 0f ? p.JumpOut.Speed : runAfter > 0f ? runAfter : 3.2f;
            takeOff = p.JumpOut.Events != null && p.JumpOut.Events.Length >= 2 ? p.JumpOut.Events[0] : 0f;
        }

        // Metres along the street the clip's root has gone 't' seconds into the hop.
        private float HopDistance(float t)
        {
            float floor = _floorSpeed * Mathf.Clamp(t, 0f, _takeOff);
            float tau = Mathf.Clamp(t - _takeOff, 0f, HopRamp);
            float ramp = _floorSpeed * tau + (_runSpeed - _floorSpeed) * tau * tau / (2f * HopRamp);
            return floor + ramp + _runSpeed * Mathf.Max(0f, t - _takeOff - HopRamp);
        }

        // ---------- Sitting up in a cargo bay ----------

        /// <summary>Wakes in a cargo bay (§4.5): SitUp_Cargo at once (the ragdoll must be built). The root goes where the
        /// NPC will sit: on the bay floor, turned so the clip's first frame lies where the ragdoll lies, moved so the seated
        /// figure's footprint (and a seatRadius circle, the seated capsule) stays inside the bay. visualPosition /
        /// visualRotation: the seated visual's local pose that GreyboxNpc sets right after. Lying on its belly, the blend
        /// takes RollBlendScale longer (the body rolls over). False, nothing changed, without the clips.</summary>
        public bool SitUp(VanCargoSpace bay, Vector3 visualPosition, Quaternion visualRotation, float seatRadius,
            out Vector3 rootPosition, out Quaternion rootRotation)
        {
            rootPosition = transform.position;
            rootRotation = transform.rotation;
            NpcRagdollProfile p = Profile;
            if (bay == null || _ragdoll == null || !_ragdoll.Active || !CanSitUp) return false;
            ClipInfo clip = p.SitUp;
            Quaternion van = bay.Rotation;
            // The ragdoll's head direction on the bay floor (van-local) and the clip's (root space, frame 0).
            Vector3 head = Quaternion.Inverse(van) * (_ragdoll.Landmark(NpcLandmark.Head) - _ragdoll.Landmark(NpcLandmark.Pelvis));
            head.y = 0f;
            if (head.sqrMagnitude < 1e-4f) head = Vector3.forward;
            Vector3 clipHead = visualRotation * Vector3.back;
            clipHead.y = 0f;
            Quaternion yaw = Quaternion.Euler(0f, Vector3.SignedAngle(clipHead, head, Vector3.up), 0f);
            // The clip's first-frame Hips (root space) on the ragdoll's Hips; the root on the bay floor.
            Vector3 hips = bay.ToLocal(_ragdoll.Hips.position);
            Vector3 first = yaw * (visualPosition + visualRotation * clip.HipsStart);
            var root = new Vector3(hips.x - first.x, bay.LocalBox.min.y, hips.z - first.z);
            Vector3 fit = Inside(bay.LocalBox, root, yaw, p, seatRadius);
            root += fit;
            rootRotation = van * yaw;
            rootPosition = bay.ToWorld(root);
            bool belly = Vector3.Dot(_ragdoll.Front, van * Vector3.up) < 0f;
            LyingHips = hips.y - root.y;
            Shift = fit.magnitude;
            Squeezed = false;
            Crawls = 0;
            SettledAfter = 0f;
            _ragdoll.Deactivate(belly ? p.RollBlendScale : 1f);
            transform.SetPositionAndRotation(rootPosition, rootRotation);
            Play(GetUpKind.SitUp, clip);
            _kind = GetUpKind.SitUp;
            _step = Step.None; // GreyboxNpc runs the seated NPC; the controller goes on to the sit idle by itself
            return true;
        }

        // How far to move the root (van-local, on the floor) so the seated figure's footprint and the seated capsule stay
        // inside the bay, a few centimetres off its walls (centred when the bay is too short for it).
        private static Vector3 Inside(Bounds box, Vector3 root, Quaternion yaw, NpcRagdollProfile p, float radius)
        {
            const float margin = 0.04f;
            Vector2 min = Vector2.Min(p.SeatMin, new Vector2(-radius, -radius));
            Vector2 max = Vector2.Max(p.SeatMax, new Vector2(radius, radius));
            float minX = float.MaxValue, maxX = float.MinValue, minZ = float.MaxValue, maxZ = float.MinValue;
            for (int corner = 0; corner < 4; corner++)
            {
                Vector3 c = root + yaw * new Vector3((corner & 1) == 0 ? min.x : max.x, 0f, (corner & 2) == 0 ? min.y : max.y);
                minX = Mathf.Min(minX, c.x);
                maxX = Mathf.Max(maxX, c.x);
                minZ = Mathf.Min(minZ, c.z);
                maxZ = Mathf.Max(maxZ, c.z);
            }
            return new Vector3(Fit(minX, maxX, box.min.x + margin, box.max.x - margin), 0f,
                Fit(minZ, maxZ, box.min.z + margin, box.max.z - margin));
        }

        private static float Fit(float low, float high, float boxLow, float boxHigh)
        {
            if (high - low > boxHigh - boxLow) return (boxLow + boxHigh - low - high) * 0.5f;
            if (low < boxLow) return boxLow - low;
            if (high > boxHigh) return boxHigh - high;
            return 0f;
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
    }
}
