using System.Collections.Generic;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using UnityEngine;
using C = OnlyVolunteers.Characters.Npc.NpcAnimContract;
using ClipInfo = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.ClipInfo;

namespace OnlyVolunteers.Characters.Npc
{
    // Stage 9 step 5 (docs/drafts/NPC_RAGDOLL_ANIM_STAGE9_DESIGN.md §5.4, "one driver"): the only writer of an NPC's
    // Animator. GreyboxNpc adds it at runtime next to NpcRagdoll (no prefab or map-builder edits). It maps game state to the
    // contract's parameters (NpcAnimContract) and the controller (built by the editor's NpcAnimatorBuilder from clips.json)
    // picks the states: locomotion by Speed (walk, then the run of the NPC's Gait), idles, crowd activities (enter, loop,
    // exit), the cargo bay (sit-up, sit idle, knocks), the escape scramble, the capsule lying (Down) with the carried
    // struggle on top, hit reacts and the police one-shots.
    // Inputs: GreyboxNpc's state is read here every frame (State, Phase, Fleeing, held); whoever moves the NPC tells it its
    // speed every frame it moves it (SetMove: GreyboxNpc fleeing or escaping, CrowdWalker, PoliceOfficer; no call = standing);
    // CrowdWalker sets the activity, PoliceOfficer aiming; one-shots go through Trigger (a pulse: reset at the end of the
    // frame if no transition took it).
    // Ownership: while the NPC is a ragdoll the Animator is off (NpcRagdoll) and while NpcGetUp plays a get-up or the hop out
    // of a van (NpcGetUp.Owns, the police trip's get-up included) the driver writes nothing (Held); NpcGetUp starts those
    // clips through PlayGetUp: the contract's parameters of that moment plus Play at frame 0 (the ragdoll's pose blend needs
    // the clip's first frame at once). Writes and OwnerWrites count every Animator write of the two paths (RagdollSmokeTest
    // checks that neither the ragdoll nor a get-up sees a driver write).
    // A controller without the contract (no Driven parameter) is left alone.
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(50)] // after GreyboxNpc, CrowdWalker and PoliceOfficer (0) gave this frame's inputs, before the Animator runs
    public sealed class NpcAnimDriver : MonoBehaviour
    {
        /// <summary>The contract's parameter values (one NPC situation).</summary>
        public struct Params
        {
            public float Speed, SpeedMul, Gait;
            public bool Panic, Carried, InCargo, Ragdoll, Aim, Driven;
            public int StunPhase, Activity, GetUp;

            public override string ToString() =>
                $"Speed {Speed:0.00} x{SpeedMul:0.00} gait {Gait:0} panic {(Panic ? 1 : 0)} stun {StunPhase} carried {(Carried ? 1 : 0)} " +
                $"cargo {(InCargo ? 1 : 0)} activity {Activity} ragdoll {(Ragdoll ? 1 : 0)} getUp {GetUp} aim {(Aim ? 1 : 0)} driven {(Driven ? 1 : 0)}";
        }

        /// <summary>What the driver knows about one NPC this frame (Compose's input).</summary>
        public struct Inputs
        {
            public NpcState State;
            public StunPhase Phase;
            public bool Fleeing, Held, Aim;
            public float Speed, Rate, IdleRate;
            public NpcGait Gait;
            public int Activity;
        }

        /// <summary>Authored ground speeds (m/s) of the locomotion clips the controller plays.</summary>
        public struct Speeds
        {
            public float Walk, Run, RunCop, RunCopFat, Scramble;

            public static Speeds Default => new() { Walk = 1.5f, Run = 3.2f, RunCop = 3.2f, RunCopFat = 3.2f, Scramble = 3.2f };

            public float RunOf(NpcGait gait) => gait == NpcGait.Police ? RunCop : gait == NpcGait.PoliceFat ? RunCopFat : Run;
        }

        // Playback limits of the locomotion clips (the stage-1 numbers: civilians up to x2, police runs up to x3).
        private const float MinRate = 0.15f, MaxRate = 2f, MaxPoliceRate = 3f;
        // A smoker without the SmokeCorner clips idles slower (the stage-1 placeholder).
        private const float SmokerIdleRate = 0.6f;

        private static readonly int SpeedId = Animator.StringToHash(C.Speed), SpeedMulId = Animator.StringToHash(C.SpeedMul),
            PanicId = Animator.StringToHash(C.Panic), StunId = Animator.StringToHash(C.StunPhase), CarriedId = Animator.StringToHash(C.Carried),
            CargoId = Animator.StringToHash(C.InCargo), ActivityId = Animator.StringToHash(C.Activity), RagdollId = Animator.StringToHash(C.Ragdoll),
            GetUpId = Animator.StringToHash(C.GetUp), GaitId = Animator.StringToHash(C.Gait), AimId = Animator.StringToHash(C.Aim),
            DrivenId = Animator.StringToHash(C.Driven);
        private static readonly int[] TriggerIds = Hashes(C.Triggers);
        private static readonly int[] GetUpTriggerIds = Hashes(C.GetUpTriggers);

        // Per controller: its parameters and the clips it plays (a role is installed when its state's clip is there:
        // clips.json names the state and the clip alike).
        private sealed class Installed
        {
            public readonly HashSet<int> Parameters = new();
            public readonly Dictionary<string, float> Clips = new();
        }
        private static readonly Dictionary<RuntimeAnimatorController, Installed> Cache = new();

        private GreyboxNpc _npc;
        private NpcGetUp _getUp;
        private NpcRagdoll _ragdoll;
        private Animator _animator;
        private Installed _installed;
        private RuntimeAnimatorController _cachedFor;
        private Speeds _speeds = Speeds.Default;
        // Inputs from the callers: the mover's speed (this frame only), the crowd activity, aiming.
        private float _speed, _rate = 1f;
        private NpcGait _gait;
        private int _moveFrame = -10;
        private int _activity = -1;
        private float _idleRate = 1f;
        private bool _aim;
        private readonly List<int> _pulsed = new();
        private readonly Dictionary<string, bool> _has = new(); // Has(role), per controller

        /// <summary>Animator writes by the driver itself (parameters, trigger pulses).</summary>
        public int Writes { get; private set; }
        /// <summary>Animator writes made for NpcGetUp (PlayGetUp: the parameters of that moment and the Play).</summary>
        public int OwnerWrites { get; private set; }
        /// <summary>Frames the driver wrote nothing because the ragdoll or a get-up had the Animator (Held).</summary>
        public int HeldFrames { get; private set; }
        /// <summary>The parameters it wrote last (either path).</summary>
        public Params Last { get; private set; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Cache.Clear();

        /// <summary>Forget what controllers play (after the editor rebuilt one).</summary>
        public static void ClearCache() => Cache.Clear();

        private static int[] Hashes(string[] names)
        {
            var ids = new int[names.Length];
            for (int i = 0; i < names.Length; i++) ids[i] = names[i] != null ? Animator.StringToHash(names[i]) : 0;
            return ids;
        }

        // ---------- What the controller has ----------

        /// <summary>The rig's Animator (the Buddy visual's).</summary>
        public Animator Animator => Resolve() ? _animator : null;

        /// <summary>The Animator plays the contract (a controller built by NpcAnimatorBuilder).</summary>
        public bool HasContract => Resolve() && _installed != null && _installed.Parameters.Contains(DrivenId);

        /// <summary>NpcGetUp has the Animator (a get-up or the hop out of a van) or the ragdoll switched it off: the driver
        /// writes nothing now.</summary>
        public bool Held => !Resolve() || !_animator.isActiveAndEnabled || (_getUp != null && _getUp.Owns);

        /// <summary>The clip of this role (NpcAnimContract roles) is in clips.json and the controller plays it (a state of
        /// that name: the clip's own, or a "states" entry reusing another clip).</summary>
        public bool Has(string role)
        {
            if (string.IsNullOrEmpty(role) || !Resolve()) return false;
            if (_has.TryGetValue(role, out bool known)) return known;
            ClipInfo clip = Clip(role);
            bool has = clip != null && (HasClip(clip.State) || HasBaseState(clip.State));
            if (_animator.isActiveAndEnabled) _has[role] = has; // asked of an Animator that is off, ask again later
            return has;
        }

        private bool HasBaseState(string state) =>
            !string.IsNullOrEmpty(state) && Resolve() && _animator.isActiveAndEnabled &&
            (_animator.HasState(0, Animator.StringToHash(state)) || _animator.HasState(0, Animator.StringToHash("Base Layer." + state)));

        /// <summary>The controller has a clip (= state, clips.json names both alike) of this name.</summary>
        public bool HasClip(string state) =>
            !string.IsNullOrEmpty(state) && Resolve() && _installed != null && _installed.Clips.ContainsKey(state);

        /// <summary>The clips.json clip of this role, or null.</summary>
        public ClipInfo Clip(string role)
        {
            NpcRagdollProfile p = Profile;
            return p != null ? p.Role(role) : null;
        }

        /// <summary>Seconds of a role's clip: the profile's, else the clip's own length; 0 when not installed.</summary>
        public float Seconds(string role)
        {
            ClipInfo clip = Clip(role);
            if (clip == null || !Has(role)) return 0f;
            return clip.Seconds > 0f ? clip.Seconds : _installed.Clips.TryGetValue(clip.State, out float length) ? length : 0f;
        }

        /// <summary>The crowd activity has its own clips (at least a loop).</summary>
        public bool HasActivity(CrowdActivity activity) => Has(C.ActivityRole(activity.ToString(), C.LoopPhase));

        /// <summary>Seconds of the activity's exit clip (standing up from the bench...), 0 without one.</summary>
        public float ActivityExitSeconds(CrowdActivity activity) => Seconds(C.ActivityRole(activity.ToString(), C.ExitPhase));

        /// <summary>The prop the activity's clips need behind the NPC (a bench seat, a wall), or null (none, or no clips).</summary>
        public NpcRagdollProfile.ActivityPlacement Placement(CrowdActivity activity) =>
            HasActivity(activity) && Profile != null ? Profile.PlacementOf(activity.ToString()) : null;

        /// <summary>The base layer is in this state now (not counting a transition into it).</summary>
        public bool InState(string state) =>
            Resolve() && _animator.isActiveAndEnabled && _animator.GetCurrentAnimatorStateInfo(0).IsName(state);

        private NpcRagdollProfile Profile => Resolve() && _ragdoll != null ? _ragdoll.Profile : null;

        private bool Resolve()
        {
            if (_npc == null) TryGetComponent(out _npc);
            if (_getUp == null) TryGetComponent(out _getUp);
            if (_ragdoll == null) TryGetComponent(out _ragdoll);
            if (_animator == null)
            {
                _animator = _ragdoll != null ? _ragdoll.Animator : null;
                if (_animator == null) _animator = GetComponentInChildren<Animator>(true);
                if (_animator == null) return false;
            }
            RuntimeAnimatorController controller = _animator.runtimeAnimatorController;
            // Again once an Animator that was not initialised yet (no parameters to read) is.
            if (controller != _cachedFor || (_installed != null && _installed.Parameters.Count == 0 && _animator.isInitialized))
            {
                _cachedFor = controller;
                _installed = controller != null ? Scan(controller, _animator) : null;
                _has.Clear();
                _speeds = SpeedsOf(_ragdoll != null ? _ragdoll.Profile : null, this);
            }
            return true;
        }

        private static Installed Scan(RuntimeAnimatorController controller, Animator animator)
        {
            if (Cache.TryGetValue(controller, out Installed known)) return known;
            var installed = new Installed();
            foreach (AnimationClip clip in controller.animationClips)
                if (clip != null) installed.Clips[clip.name] = clip.length;
            // An Animator lists its parameters once it is initialised (an inactive one: later).
            if (animator.isInitialized)
                foreach (AnimatorControllerParameter p in animator.parameters) installed.Parameters.Add(p.nameHash);
            if (installed.Parameters.Count > 0) Cache[controller] = installed;
            return installed;
        }

        // The authored speeds of the locomotion clips the controller plays: clips.json's, else the profile's built-ins.
        private static Speeds SpeedsOf(NpcRagdollProfile p, NpcAnimDriver d)
        {
            Speeds s = Speeds.Default;
            if (p == null) return s;
            s.Walk = SpeedOf(p, d, C.RoleWalk, p.WalkSpeed);
            s.Run = SpeedOf(p, d, C.RoleRun, p.RunSpeed);
            s.RunCop = SpeedOf(p, d, C.RoleRunCop, s.Run);
            s.RunCopFat = SpeedOf(p, d, C.RoleRunCopFat, s.Run);
            s.Scramble = SpeedOf(p, d, C.RoleScramble, s.Run);
            return s;
        }

        private static float SpeedOf(NpcRagdollProfile p, NpcAnimDriver d, string role, float fallback)
        {
            ClipInfo clip = p.Role(role);
            return clip != null && clip.Speed > 0f && d._installed != null && d._installed.Clips.ContainsKey(clip.State) ? clip.Speed : fallback;
        }

        // ---------- Inputs ----------

        /// <summary>The NPC moves at 'speed' (m/s, flat) this frame. Call every frame you move it (the NPC's own flight and
        /// escape run, a crowd walker, a police officer); without a call it stands. gait: whose run it is; rate: an extra
        /// playback factor (a fat officer without his own run clip).</summary>
        public void SetMove(float speed, NpcGait gait = NpcGait.Civilian, float rate = 1f)
        {
            _speed = speed;
            _gait = gait;
            _rate = rate > 0f ? rate : 1f;
            _moveFrame = Time.frameCount;
        }

        /// <summary>The crowd activity it is doing (CrowdWalker), or -1. Its hand prop (profile Props) comes and goes with it.</summary>
        public void SetActivity(int activity)
        {
            if (activity == _activity) return;
            _activity = activity;
            _idleRate = activity == (int)CrowdActivity.SmokeCorner && !HasActivity(CrowdActivity.SmokeCorner) ? SmokerIdleRate : 1f;
            ShowProp(activity >= 0 && HasActivity((CrowdActivity)activity) && Profile != null ? Profile.PropOf(((CrowdActivity)activity).ToString()) : null);
        }

        // ---------- The activity's hand prop (a hook: clips.json "props") ----------

        private GameObject _prop;
        private static Mesh _propMesh;
        private static Material _propMaterial;

        private void ShowProp(NpcRagdollProfile.ActivityProp prop)
        {
            if (_prop != null) Destroy(_prop);
            _prop = null;
            if (prop == null || !Resolve()) return;
            Transform bone = null;
            foreach (Transform t in _animator.GetComponentsInChildren<Transform>(true))
                if (t.name == prop.Bone)
                {
                    bone = t;
                    break;
                }
            if (bone == null) return;
            if (prop.Prefab != null) _prop = Instantiate(prop.Prefab, bone, false);
            else
            {
                // A plain white cylinder (no collider): the shared mesh and an unlit-ish material, made once.
                if (_propMesh == null)
                {
                    GameObject probe = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                    _propMesh = probe.GetComponent<MeshFilter>().sharedMesh;
                    _propMaterial = new Material(probe.GetComponent<MeshRenderer>().sharedMaterial) { color = new Color(0.95f, 0.93f, 0.88f) };
                    Destroy(probe);
                }
                _prop = new GameObject("ActivityProp_" + prop.Activity);
                _prop.transform.SetParent(bone, false);
                _prop.AddComponent<MeshFilter>().sharedMesh = _propMesh;
                _prop.AddComponent<MeshRenderer>().sharedMaterial = _propMaterial;
            }
            // Metres and degrees in the bone's frame: the bone's own scale (the armature is scaled) is taken out.
            Vector3 lossy = bone.lossyScale;
            _prop.transform.SetLocalPositionAndRotation(
                new Vector3(prop.Position.x / Mathf.Max(1e-6f, lossy.x), prop.Position.y / Mathf.Max(1e-6f, lossy.y), prop.Position.z / Mathf.Max(1e-6f, lossy.z)),
                Quaternion.Euler(prop.Rotation));
            Vector3 size = prop.Prefab != null ? Vector3.one : new Vector3(prop.Size.x, prop.Size.y * 0.5f, prop.Size.z); // the cylinder is 2 units tall
            _prop.transform.localScale = new Vector3(size.x / Mathf.Max(1e-6f, lossy.x), size.y / Mathf.Max(1e-6f, lossy.y), size.z / Mathf.Max(1e-6f, lossy.z));
        }

        private void OnDisable()
        {
            if (_prop != null) Destroy(_prop);
            _prop = null;
            _activity = -1;
        }

        /// <summary>A police officer aims (the upper-body layer).</summary>
        public void SetAim(bool aim) => _aim = aim;

        /// <summary>Plays a one-shot (see NpcAnimTrigger) if its clip is installed and the driver has the Animator; onlyIn: and
        /// only from that state, not in a transition (the knock from the sit idle). True: it starts this frame.</summary>
        public bool Trigger(NpcAnimTrigger trigger, string onlyIn = null)
        {
            if (Held || !HasContract || !Has(C.RoleOf(trigger))) return false;
            if (onlyIn != null && (!_animator.GetCurrentAnimatorStateInfo(0).IsName(onlyIn) || _animator.IsInTransition(0))) return false;
            int id = TriggerIds[(int)trigger];
            if (!_installed.Parameters.Contains(id)) return false;
            _animator.SetTrigger(id);
            Writes++;
            _pulsed.Add(id);
            return true;
        }

        // ---------- NpcGetUp's starts ----------

        /// <summary>NpcGetUp (and GreyboxNpc's capsule sit-up): starts the clip of 'kind' in 'state' at its first frame now
        /// (Play + Update(0)), with the contract's parameters of that moment: awake, GetUp = kind, in a van for the sit-up,
        /// panicking for the hop out of one (speedAfter: the run it lands into). Without the clip only the parameters go in
        /// (the hop: the run plays). The driver itself stays out while NpcGetUp owns the get-up (Held). False: nothing
        /// played (no Animator, no contract, no clip).</summary>
        public bool PlayGetUp(GetUpKind kind, string state, float speedAfter = 0f)
        {
            if (!Resolve() || !_animator.isActiveAndEnabled || !HasContract) return false;
            var p = new Params
            {
                Driven = true,
                StunPhase = (int)StunPhase.Awake,
                InCargo = kind == GetUpKind.SitUp,
                Panic = kind == GetUpKind.JumpOut,
                Activity = -1,
                Speed = Mathf.Max(0f, speedAfter),
                SpeedMul = 1f,
                GetUp = (int)kind,
            };
            OwnerWrites += Write(p, true);
            ClearTriggers();
            _animator.speed = 1f;
            bool play = HasClip(state);
            if (play)
            {
                _animator.Play(state, 0, 0f);
                OwnerWrites++;
            }
            _animator.Update(0f);
            return play;
        }

        // ---------- Every frame ----------

        private void Update()
        {
            if (!Resolve()) return;
            if (Held)
            {
                HeldFrames++;
                return;
            }
            if (!HasContract) return;
            Writes += Write(Compose(CurrentInputs(), _speeds), false);
            if (_animator.speed != 1f)
            {
                _animator.speed = 1f; // the stage-1 code played clips through the global speed
                Writes++;
            }
        }

        // Its own trigger pulses: reset at the end of the frame if no transition took them (a stale trigger fires later).
        private void LateUpdate()
        {
            if (_pulsed.Count == 0) return;
            if (_animator != null && _animator.isActiveAndEnabled)
                foreach (int id in _pulsed) _animator.ResetTrigger(id);
            _pulsed.Clear();
        }

        private Inputs CurrentInputs()
        {
            var i = new Inputs
            {
                State = _npc != null ? _npc.State : NpcState.Free,
                Phase = _npc != null ? _npc.Phase : StunPhase.None,
                Fleeing = _npc != null && _npc.Fleeing,
                Speed = _moveFrame == Time.frameCount ? _speed : 0f,
                Gait = _moveFrame == Time.frameCount ? _gait : NpcGait.Civilian,
                Rate = _moveFrame == Time.frameCount ? _rate : 1f,
                Activity = _activity,
                Aim = _aim,
                IdleRate = _idleRate,
            };
            INpcBody body = _npc != null ? _npc.PhysicalBody : null;
            i.Held = body != null && body.Active && body.HolderCount > 0;
            return i;
        }

        /// <summary>The contract's parameters for one situation (pure: the EditMode tests check it state by state).</summary>
        public static Params Compose(in Inputs i, in Speeds s)
        {
            bool free = i.State == NpcState.Free;
            bool escaping = i.State == NpcState.Escaping;
            var p = new Params
            {
                Driven = true,
                InCargo = i.State == NpcState.CargoSeated || escaping,
                StunPhase = free ? 0 : (int)i.Phase,
                Panic = escaping || (free && i.Fleeing),
                Carried = i.State == NpcState.Down && i.Held,
                Speed = free || escaping ? Mathf.Max(0f, i.Speed) : 0f,
                Gait = free ? (float)i.Gait : 0f,
                Aim = free && i.Aim,
            };
            p.Activity = free && !p.Panic ? i.Activity : -1;
            p.SpeedMul = Rate(p, i, s);
            return p;
        }

        // The locomotion clip's playback: speed / the authored speed of the clip the controller picks for it (the same
        // thresholds), clamped; standing: the idle rate.
        private static float Rate(in Params p, in Inputs i, in Speeds s)
        {
            if (p.InCargo && p.Panic) return Mathf.Clamp(p.Speed / Mathf.Max(0.1f, s.Scramble), MinRate, MaxRate);
            if (p.StunPhase != 0 && p.StunPhase != (int)StunPhase.Awake) return 1f;
            if (p.Speed <= C.WalkFrom) return i.IdleRate > 0f ? i.IdleRate : 1f;
            bool police = i.Gait != NpcGait.Civilian;
            if (p.Panic || p.Speed > C.RunFrom)
                return Mathf.Clamp(p.Speed / Mathf.Max(0.1f, s.RunOf(i.Gait)) * (i.Rate > 0f ? i.Rate : 1f), MinRate, police ? MaxPoliceRate : MaxRate);
            return Mathf.Clamp(p.Speed / Mathf.Max(0.1f, s.Walk), MinRate, MaxRate);
        }

        // Writes what differs from the Animator's values (a re-enabled Animator may have reset them); returns the count.
        private int Write(in Params p, bool owner)
        {
            Animator a = _animator;
            HashSet<int> has = _installed.Parameters;
            int n = 0;
            if (has.Contains(DrivenId) && a.GetBool(DrivenId) != p.Driven) { a.SetBool(DrivenId, p.Driven); n++; }
            if (has.Contains(RagdollId) && a.GetBool(RagdollId) != p.Ragdoll) { a.SetBool(RagdollId, p.Ragdoll); n++; }
            if (has.Contains(StunId) && a.GetInteger(StunId) != p.StunPhase) { a.SetInteger(StunId, p.StunPhase); n++; }
            if (has.Contains(CargoId) && a.GetBool(CargoId) != p.InCargo) { a.SetBool(CargoId, p.InCargo); n++; }
            if (has.Contains(PanicId) && a.GetBool(PanicId) != p.Panic) { a.SetBool(PanicId, p.Panic); n++; }
            if (has.Contains(ActivityId) && a.GetInteger(ActivityId) != p.Activity) { a.SetInteger(ActivityId, p.Activity); n++; }
            if (has.Contains(CarriedId) && a.GetBool(CarriedId) != p.Carried) { a.SetBool(CarriedId, p.Carried); n++; }
            if (has.Contains(AimId) && a.GetBool(AimId) != p.Aim) { a.SetBool(AimId, p.Aim); n++; }
            if (has.Contains(GetUpId) && a.GetInteger(GetUpId) != p.GetUp) { a.SetInteger(GetUpId, p.GetUp); n++; }
            if (has.Contains(GaitId) && !Mathf.Approximately(a.GetFloat(GaitId), p.Gait)) { a.SetFloat(GaitId, p.Gait); n++; }
            if (has.Contains(SpeedId) && Mathf.Abs(a.GetFloat(SpeedId) - p.Speed) > 0.005f) { a.SetFloat(SpeedId, p.Speed); n++; }
            if (has.Contains(SpeedMulId) && Mathf.Abs(a.GetFloat(SpeedMulId) - p.SpeedMul) > 0.005f) { a.SetFloat(SpeedMulId, p.SpeedMul); n++; }
            Last = p;
            return n;
        }

        // Every trigger off (a get-up starts clean: a pulse left from before must not fire into it).
        private void ClearTriggers()
        {
            foreach (int id in TriggerIds)
                if (_installed.Parameters.Contains(id)) _animator.ResetTrigger(id);
            foreach (int id in GetUpTriggerIds)
                if (id != 0 && _installed.Parameters.Contains(id)) _animator.ResetTrigger(id);
            _pulsed.Clear();
        }
    }
}
