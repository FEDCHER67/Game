using System.Collections.Generic;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using UnityEngine;

namespace OnlyVolunteers.Police
{
    // A police officer on foot (design 1.3): a crowd foot patrol officer (CrowdWalker walks him until he is needed) or one
    // of a car's crew of two (inactive inside the car, out when the car stops at the van). Same logic for both, two
    // looks of numbers: thin (7.4 m/s) and fat (5.6 m/s, the Run clip x1.35, trips now and then). Vadim owns the looks:
    // this only tints the Buddy blue (MaterialPropertyBlock) and keeps the "ПОЛИЦИЯ" label.
    //   Idle (patrol / in the car) -> Alerted (0.5-1 s, "!") -> Respond (runs over the crowd walk graph) or Chase
    //   (straight at the suspect within 20 m) -> Beat (0.45 s wind-up, a hit if still within 1.6 m: the player is thrown
    //   5 m/s + 2.5 m/s up; three hits in 12 s = ArrestRequested) -> Return (patrol / back to the car).
    // Rare shots: at night or heat 60+, at a player on foot running away 6-15 m off, 1 s aim, 50 % hit = one Beat hit,
    // never at the van. Knocked down: GreyboxNpc slapstick as for anyone; on waking he goes for the attacker within 30 m.
    // NPC stage 9 step 4 (design §4.6, decision 5): the fat one's trip goes through the ragdoll (Trip: GreyboxNpc.Stumble,
    // lies TripTime, gets up with the get-up clip). He is not Down meanwhile (Stumbling): his state carries on after it,
    // nothing here runs while he lies or gets up. Without a ragdoll for him (the cap, no get-up clips) the old look: face
    // down for TripTime. Review fixes (GPT review 2026-10-07): a new attack waits BeatCooldown after the last one (finding
    // 4), the foot chase's time cap counts from the chase's start, not from the last hit or shot (5), and the visual is
    // GreyboxNpc's while he is not free (6: the seat clips turn it; a ragdoll hangs under it).
    // NPC stage 9 step 5 (design §5.4): his clips go through the NPC's NpcAnimDriver: Move gives it his speed and gait (the
    // police run, the fat one's own run; without it the civilian run x FatAnimFactor as before) and whether he aims (Aim:
    // the upper-body aim while he takes the shot); Beat starts the punch (its Hit at the end of the 0.45 s wind-up), Bang
    // shakes a fist at the van between the thuds, and the fat one's trip first stumbles in the Cop_Trip clip (when the rig
    // has it), then goes down through the ragdoll at its end. Rigs without those clips look as before.
    [RequireComponent(typeof(GreyboxNpc))]
    public sealed class PoliceOfficer : MonoBehaviour
    {
        public enum OfficerState : byte { Idle, Alerted, Respond, Chase, Beat, Aim, Bang, Look, Return, Leave }

        [SerializeField, UnityEngine.Serialization.FormerlySerializedAs("Fat")] private bool _fat;
        /// <summary>The fat look (slower, trips). Set after AddComponent at runtime too: the tint follows.</summary>
        public bool Fat
        {
            get => _fat;
            set
            {
                _fat = value;
                if (_npc != null) Tint();
            }
        }

        // Every active officer's body, for the cars' pedestrian check (no component lookup per NPC per car).
        private static readonly HashSet<GreyboxNpc> Bodies = new();
        public static bool IsOfficer(GreyboxNpc npc) => Bodies.Contains(npc);

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() => Bodies.Clear();
        [System.NonSerialized] public PoliceUnit CrewOf;
        [System.NonSerialized] public PoliceDirector.Suspect Attacker;

        public OfficerState State { get; private set; } = OfficerState.Idle;
        // Crew in the car (the object is inactive then). Serialized: the builder places crews inside, inactive.
        [SerializeField] private bool _inside;
        public bool Inside { get => _inside; private set => _inside = value; }
        public bool Orphaned { get; private set; }
        // Tripped (GreyboxNpc.Stumbling) is not down: he gets up and carries on (design §4.6).
        public bool Down => _npc == null || (_npc.State != NpcState.Free && !_npc.Stumbling);
        public bool CanRespond => isActiveAndEnabled && !Down && (State == OfficerState.Idle || State == OfficerState.Look || State == OfficerState.Return) && !Inside;
        public GreyboxNpc Npc => _npc;
        public int Hits { get; private set; }

        private PoliceDirector _d;
        private PoliceConfig C => _d.Config;
        private GreyboxNpc _npc;
        private CharacterController _controller;
        private CrowdWalker _walker;
        private Transform _visual;
        private Quaternion _visualRotation;
        private TextMesh _label;
        private PoliceDirector.Suspect _target;
        private Vector3 _goal;
        private float _stateSince, _until, _vy, _lastSeen, _nextPath, _nextShot, _tripUntil, _nextBang;
        private float _nextBeat, _chaseSince; // the next attack's earliest time; the foot chase's start
        // Step 5: the next fist shaken at the van (Bang); the Cop_Trip stumble before the ragdoll (its start, end, velocity).
        private float _nextFist, _tripLeadFrom, _tripLeadUntil;
        private Vector3 _tripVelocity;
        private readonly List<Vector2> _path = new();
        private int _pathIndex;
        private readonly List<float> _hitTimes = new();
        private bool _wasDown, _arrestSent;
        private Vector3 _pawnLast;
        private float _pawnSpeed;
        private Vector2 _scare;
        private bool _mayShoot;
        private static MaterialPropertyBlock _block;
        private static readonly int BaseColor = Shader.PropertyToID("_BaseColor"), ColorId = Shader.PropertyToID("_Color");

        public float RunSpeed => Fat ? C.FatSpeed : C.ThinSpeed;

        private void Awake()
        {
            _npc = GetComponent<GreyboxNpc>();
            _controller = GetComponent<CharacterController>();
            Animator animator = GetComponentInChildren<Animator>(true);
            if (animator != null && animator.transform != transform)
            {
                _visual = animator.transform;
                _visualRotation = _visual.localRotation;
            }
            // Cops do not run from the van or the player like the crowd does (given back if the body turns civilian).
            _scare = new Vector2(_npc.WalkerScareRadius, _npc.VanScareRadius);
            _npc.WalkerScareRadius = 0f;
            _npc.VanScareRadius = 0f;
            Tint();
        }

        private void OnEnable()
        {
            if (_npc != null) Bodies.Add(_npc);
            _d = PoliceDirector.Instance;
            if (_d != null && !_d.Officers.Contains(this)) _d.Officers.Add(this);
            _walker = GetComponent<CrowdWalker>();
            EnsureLabel();
        }

        private void OnDisable()
        {
            if (_npc != null) Bodies.Remove(_npc);
            if (_d != null) _d.Officers.Remove(this);
        }

        // The crowd reuses pooled NPCs for any role: an officer's body that comes back as a passer-by loses the uniform.
        private void OnDestroy()
        {
            foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
                if (r != null && r.GetComponent<TextMesh>() == null) r.SetPropertyBlock(null);
            if (_npc != null && _scare != Vector2.zero)
            {
                _npc.WalkerScareRadius = _scare.x;
                _npc.VanScareRadius = _scare.y;
            }
            if (_walker != null) _walker.Suspended = false;
        }

        private void Tint()
        {
            _block ??= new MaterialPropertyBlock();
            Color color = Fat ? new Color(0.25f, 0.32f, 0.75f) : new Color(0.35f, 0.5f, 1f);
            foreach (Renderer r in GetComponentsInChildren<Renderer>(true))
            {
                if (r.GetComponent<TextMesh>() != null) continue;
                r.GetPropertyBlock(_block);
                _block.SetColor(BaseColor, color);
                _block.SetColor(ColorId, color);
                r.SetPropertyBlock(_block);
            }
        }

        // The crowd's officer label ("ПОЛИЦИЯ"), also on crews and on officers the crowd let go of.
        private void EnsureLabel()
        {
            Transform existing = transform.Find("Label_Police");
            if (existing != null)
            {
                _label = existing.GetComponent<TextMesh>();
                if (_walker == null) existing.gameObject.SetActive(true); // a walker shows it itself (police role only)
                return;
            }
            var go = new GameObject("Label_Police");
            go.transform.SetParent(transform, false);
            go.transform.localPosition = new Vector3(0f, 1.95f, 0f);
            _label = go.AddComponent<TextMesh>();
            _label.text = "ПОЛИЦИЯ";
            _label.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            go.GetComponent<MeshRenderer>().sharedMaterial = _label.font.material;
            _label.fontSize = 48;
            _label.characterSize = 0.035f;
            _label.anchor = TextAnchor.MiddleCenter;
            _label.color = new Color(0.4f, 0.6f, 1f);
            go.AddComponent<GreyboxBillboard>();
        }

        private void Say(string text)
        {
            if (_label != null) _label.text = string.IsNullOrEmpty(text) ? "ПОЛИЦИЯ" : text;
        }

        // ---------- Queries ----------

        public bool IsAfter(PoliceDirector.Suspect s) => _target == s && (State == OfficerState.Alerted || State == OfficerState.Respond ||
                                                                           State == OfficerState.Chase || State == OfficerState.Beat || State == OfficerState.Aim || State == OfficerState.Bang);

        public bool Sees(Vector3 point)
        {
            if (!isActiveAndEnabled || Down || Inside || _d == null) return false;
            Vector3 eye = transform.position + Vector3.up * 1.55f;
            Vector3 to = point - eye;
            float range = (_d.Crowd != null ? _d.Crowd.ViewRange : 32f) * C.OfficerRangeFactor;
            float d = to.magnitude;
            if (d > range) return false;
            if (d > 1.5f && Vector3.Angle(transform.forward, new Vector3(to.x, 0f, to.z)) > 70f) return false;
            return !Physics.Linecast(eye, point, CrowdDirector.OcclusionMask, QueryTriggerInteraction.Ignore);
        }

        // ---------- Orders ----------

        /// <summary>Saw it himself (or was hit nearby): Alerted, then Chase or Respond.</summary>
        public void Aggro(PoliceDirector.Suspect s, Vector3 where)
        {
            if (Down || Inside || !isActiveAndEnabled) return;
            if (s != null) _target = s;
            if (State == OfficerState.Chase || State == OfficerState.Beat || State == OfficerState.Aim) return;
            _goal = where;
            Take();
            Enter(OfficerState.Alerted);
            _until = Time.time + Random.Range(0.5f, 1f);
        }

        /// <summary>A witness reported to him, or the dispatcher sent him: run to the scene.</summary>
        public void Respond(Vector3 where, PoliceDirector.Suspect s)
        {
            if (Down || Inside || !isActiveAndEnabled) return;
            if (State == OfficerState.Chase || State == OfficerState.Beat || State == OfficerState.Aim) return;
            if (s != null) _target = s;
            _goal = where;
            Take();
            Enter(OfficerState.Alerted);
            _until = Time.time + Random.Range(0.5f, 1f);
        }

        public void StandDown()
        {
            _target = null;
            if (Down) return;
            Enter(OfficerState.Return);
        }

        /// <summary>Crew: out of the car at 'door', after the suspect.</summary>
        public void GetOut(Vector3 door, float yaw, PoliceDirector.Suspect s)
        {
            Inside = false;
            Orphaned = false;
            gameObject.SetActive(true);
            _controller.enabled = false;
            transform.SetPositionAndRotation(door, Quaternion.Euler(0f, yaw, 0f));
            _controller.enabled = true;
            _npc.ExternalLocomotion = true;
            _target = s;
            _hitTimes.Clear();
            _arrestSent = false;
            if (_d != null && _d.PawnSuspect.Wanted && _d.PawnOnFoot && (_d.Pawn.Position - door).magnitude < 40f) _target = _d.PawnSuspect;
            Enter(_target == _d.PawnSuspect && _d.PawnOnFoot ? OfficerState.Chase : OfficerState.Bang);
        }

        /// <summary>Crew: back to the car.</summary>
        public void CallBack()
        {
            if (Inside || Down) return;
            _target = null;
            Enter(OfficerState.Return);
        }

        /// <summary>Crew: into the car (instant = just vanish into it: a reset, or a reclaimed orphan).</summary>
        public void Board(bool instant)
        {
            Inside = true;
            Orphaned = false;
            _target = null;
            State = OfficerState.Idle;
            gameObject.SetActive(false);
        }

        /// <summary>Crew left behind (the car gave up or drove on): walks off and leaves the map unseen.</summary>
        public void Orphan()
        {
            if (Inside) return;
            Orphaned = true;
            if (!Down) Enter(OfficerState.Leave);
        }

        // Out of the crowd's hands while he works (the walker yields like when fleeing, and rejoins after).
        private void Take()
        {
            if (State == OfficerState.Idle || State == OfficerState.Look || State == OfficerState.Return || State == OfficerState.Leave)
            {
                _hitTimes.Clear();
                _arrestSent = false;
            }
            if (_walker == null) _walker = GetComponent<CrowdWalker>();
            if (_walker != null) _walker.Suspended = true;
            _npc.ExternalLocomotion = true;
        }

        private void Enter(OfficerState state)
        {
            // A new foot chase (not back from a hit or a shot): whether he may shoot at night in this one (canon 77: rarely),
            // and the start its time cap counts from.
            if (state == OfficerState.Chase && State != OfficerState.Chase && State != OfficerState.Beat && State != OfficerState.Aim)
            {
                _mayShoot = _d != null && Random.value < C.NightShootChance;
                _chaseSince = Time.time;
            }
            State = state;
            _stateSince = Time.time;
            _nextPath = 0f;
            _path.Clear();
            switch (state)
            {
                case OfficerState.Alerted: Say("!"); break;
                case OfficerState.Chase: Say("СТОЯТЬ!"); break;
                case OfficerState.Aim: Say("ЦЕЛИТСЯ"); break;
                case OfficerState.Bang: Say("ОТКРЫВАЙ!"); break;
                case OfficerState.Look: Say("?"); break;
                default: Say(null); break;
            }
        }

        // ---------- Update ----------

        private void Update()
        {
            using Unity.Profiling.ProfilerMarker.AutoScope scope = PoliceDirector.Marker.Auto();
            if (_d == null)
            {
                _d = PoliceDirector.Instance;
                if (_d == null) return;
                if (!_d.Officers.Contains(this)) _d.Officers.Add(this);
            }
            float now = Time.time;
            TrackPawn();
            // Tripped (stage 9 step 4): lying as the ragdoll or getting up with the clip. Not down; nothing to do until he is
            // up, then his state carries on (moving or turning him now would drag the ragdoll or cut the get-up clip).
            if (_npc.Stumbling) return;
            if (Down)
            {
                // GreyboxNpc owns the visual while he is not free (it sets it straight when he goes down as the capsule; the
                // seat clips turn it in the van; a ragdoll hangs under it): only a trip in progress is called off.
                _wasDown = true;
                _tripUntil = 0f;
                _tripLeadUntil = 0f;
                return;
            }
            if (_wasDown) WokeUp();
            if (State == OfficerState.Idle)
            {
                if (CrewOf == null && _walker != null && _walker.Role != CrowdRole.Police)
                {
                    Destroy(this); // a pooled body the crowd now walks as a passer-by
                    return;
                }
                if (_walker == null && CrewOf == null) Enter(OfficerState.Leave); // a crowd officer the crowd let go of
                return;
            }
            // Step 5: stumbling in the Cop_Trip clip: only the stumble moves him until the ragdoll takes over (Move).
            if (_tripLeadUntil > 0f)
            {
                Move(Vector3.zero, now);
                return;
            }
            Vector3 velocity = Vector3.zero;
            switch (State)
            {
                case OfficerState.Alerted:
                    Face(_goal);
                    if (now >= _until) AfterAlert();
                    break;
                case OfficerState.Respond:
                    velocity = TickRespond(now);
                    break;
                case OfficerState.Chase:
                    velocity = TickChase(now);
                    break;
                case OfficerState.Beat:
                    TickBeat(now);
                    break;
                case OfficerState.Aim:
                    TickAim(now);
                    break;
                case OfficerState.Bang:
                    velocity = TickBang(now);
                    break;
                case OfficerState.Look:
                    transform.Rotate(0f, 60f * Time.deltaTime, 0f);
                    if (now - _stateSince > C.LookAroundTime) Enter(OfficerState.Return);
                    break;
                case OfficerState.Return:
                    velocity = TickReturn();
                    break;
                case OfficerState.Leave:
                    velocity = TickLeave(now);
                    break;
            }
            // Boarded the car or vanished this frame: the object is inactive now, its controller cannot move.
            if (!gameObject.activeInHierarchy) return;
            Move(velocity, now);
        }

        private void TrackPawn()
        {
            if (_d.Pawn == null) return;
            Vector3 p = _d.Pawn.Position;
            float dt = Mathf.Max(1e-3f, Time.deltaTime);
            Vector3 v = (p - _pawnLast) / dt;
            v.y = 0f;
            _pawnSpeed = Mathf.Lerp(_pawnSpeed, v.magnitude, 0.2f);
            _pawnLast = p;
        }

        private void WokeUp()
        {
            _wasDown = false;
            _npc.Calm();
            _npc.ExternalLocomotion = true;
            _walker = GetComponent<CrowdWalker>(); // the crowd dropped him when he went down: he is on his own now
            EnsureLabel();
            if (Inside) return;
            PoliceDirector.Suspect who = Attacker ?? _target;
            Attacker = null;
            if (who != null && who.Wanted && TargetPosition(who, out Vector3 p) && Vector3.Distance(p, transform.position) < C.WakeChaseRange)
            {
                _target = who;
                Enter(OfficerState.Chase);
                _chaseSince = Time.time; // a new chase after waking, even if he was chasing when he went down
                return;
            }
            Enter(CrewOf != null && CrewOf.State == PoliceUnit.UnitState.Dismount ? OfficerState.Return : OfficerState.Leave);
        }

        private void AfterAlert()
        {
            if (_target != null && TargetPosition(_target, out Vector3 p) && _target == _d.PawnSuspect && _d.PawnOnFoot &&
                Vector3.Distance(p, transform.position) < C.ChaseStartRange)
                Enter(OfficerState.Chase);
            else Enter(OfficerState.Respond);
        }

        private bool TargetPosition(PoliceDirector.Suspect s, out Vector3 p)
        {
            p = Vector3.zero;
            if (s == null) return false;
            if (s == _d.PawnSuspect)
            {
                if (_d.Pawn == null || !_d.Pawn.Controlled) return false;
                p = _d.Pawn.Position;
                return true;
            }
            if (_d.Van == null) return false;
            p = _d.Van.transform.position;
            return true;
        }

        private Vector3 TickRespond(float now)
        {
            if (_target != null && _target == _d.PawnSuspect && _d.PawnOnFoot && Sees(_d.Pawn.Position + Vector3.up * 1.2f))
            {
                Enter(OfficerState.Chase);
                return Vector3.zero;
            }
            if (Vector3.Distance(transform.position, _goal) < 3f || now - _stateSince > 60f)
            {
                Enter(OfficerState.Look);
                return Vector3.zero;
            }
            return PathTo(_goal, RunSpeed, now);
        }

        private Vector3 TickChase(float now)
        {
            if (_target == null || !_target.Wanted || !TargetPosition(_target, out Vector3 p))
            {
                Enter(OfficerState.Return);
                return Vector3.zero;
            }
            // The suspect got into the van: the car's job now.
            if (_target == _d.PawnSuspect && _d.PawnInVan)
            {
                Enter(CrewOf != null ? OfficerState.Bang : OfficerState.Return);
                return Vector3.zero;
            }
            Vector3 eyeTarget = p + Vector3.up * 1.2f;
            float dist = Vector3.Distance(transform.position, p);
            if (Sees(eyeTarget) || dist < 3f)
            {
                _lastSeen = now;
                _d.Sighted(_target, eyeTarget, Vector3.zero);
            }
            bool lost = now - _lastSeen > C.ChaseLoseTime && dist > C.ChaseLoseDistance;
            // The cap counts from the chase's start (_chaseSince): hits and shots on the way do not restart it.
            if (lost || now - _chaseSince > C.FootChaseCap.At(_d.Night) || _d.InsideSafe(transform.position))
            {
                Enter(CrewOf != null ? OfficerState.Return : OfficerState.Look);
                return Vector3.zero;
            }
            // A new attack no sooner than BeatCooldown after the last one (_nextBeat, TickBeat).
            if (dist < C.BeatStart && _target == _d.PawnSuspect && now >= _nextBeat)
            {
                Enter(OfficerState.Beat);
                _until = now + C.BeatWindup;
                Say("БАМ!");
                if (_npc.Anim != null) _npc.Anim.Trigger(NpcAnimTrigger.Beat); // step 5: the punch, its Hit at the wind-up's end
                return Vector3.zero;
            }
            // The rare shot: a player on foot running away, 6-15 m, in sight, at night or in a hot district.
            if (_target == _d.PawnSuspect && now >= _nextShot && dist >= C.ShootMin && dist <= C.ShootMax && _pawnSpeed > 3f &&
                now - _lastSeen < 0.3f && _d.ShootingAllowed(p, _mayShoot) && Vector3.Dot(p - transform.position, _d.Pawn.Body.forward) > 0f)
            {
                Enter(OfficerState.Aim);
                _until = now + C.ShootAim;
                _nextShot = now + C.ShootCooldown;
                return Vector3.zero;
            }
            if (dist < C.ChaseDirectRange && now - _lastSeen < 0.5f) return Steer(p, RunSpeed);
            return PathTo(p, RunSpeed, now);
        }

        private void TickBeat(float now)
        {
            if (TargetPosition(_target, out Vector3 p)) Face(p);
            if (now < _until) return;
            if (_target == _d.PawnSuspect && TargetPosition(_target, out p) && Vector3.Distance(p, transform.position) <= C.BeatReach && _d.PawnOnFoot)
                LandHit(p, "hit");
            _until = now + C.BeatCooldown;
            _nextBeat = now + C.BeatCooldown; // TickChase waits for it (it used to swing again at once)
            Enter(OfficerState.Chase);
            _nextPath = now + C.BeatCooldown; // a short pause before running again
        }

        private void TickAim(float now)
        {
            if (TargetPosition(_target, out Vector3 p)) Face(p);
            if (now < _until) return;
            Say("БАХ!");
            if (_target == _d.PawnSuspect && _d.PawnOnFoot && Sees(p + Vector3.up * 1.2f) && Random.value < C.ShootHitChance) LandHit(p, "shot");
            Enter(OfficerState.Chase);
        }

        // One hit (fist or bullet, the same in v1): the player is thrown, three within 12 s = arrest.
        private void LandHit(Vector3 pawnPos, string how)
        {
            Vector3 away = pawnPos - transform.position;
            away.y = 0f;
            if (away.sqrMagnitude < 1e-4f) away = transform.forward;
            away = Quaternion.Euler(0f, Random.Range(-30f, 30f), 0f) * away.normalized;
            _d.Pawn.Knock(away * C.BeatSide + Vector3.up * C.BeatUp);
            Sfx.PlayAt(SfxIds.HitTorso, pawnPos + Vector3.up * 1.2f);
            float now = Time.time;
            _hitTimes.Add(now);
            _hitTimes.RemoveAll(t => now - t > C.ArrestWindow);
            Hits++;
            if (_d.Log) Debug.Log($"[Police] {name} {how} the player ({_hitTimes.Count}/{C.HitsToArrest} within {C.ArrestWindow:0} s)", this);
            if (_hitTimes.Count >= C.HitsToArrest && !_arrestSent)
            {
                _arrestSent = true;
                PoliceEvents.RaiseArrest(_d.Pawn, this);
                _hitTimes.Clear();
                Enter(CrewOf != null ? OfficerState.Return : OfficerState.Look);
            }
        }

        // The van stands there with everyone inside: walk up and bang on it (sound only in v1).
        private Vector3 TickBang(float now)
        {
            if (_d.PawnSuspect.Wanted && _d.PawnOnFoot && TargetPosition(_d.PawnSuspect, out Vector3 pawn) && Vector3.Distance(pawn, transform.position) < C.ChaseStartRange)
            {
                _target = _d.PawnSuspect;
                Enter(OfficerState.Chase);
                return Vector3.zero;
            }
            if (_d.Van == null)
            {
                Enter(OfficerState.Return);
                return Vector3.zero;
            }
            Vector3 v = _d.Van.transform.position;
            // The van drives off or is already too far to bang on: back to the car (the car decides what next).
            if (_d.VanSpeedKmh > C.DismountVanKmh || Vector3.Distance(transform.position, v) > C.CrewReturnDistance)
            {
                _target = null;
                Enter(OfficerState.Return);
                return Vector3.zero;
            }
            Vector3 side = v + (Vector3.Dot(transform.position - v, _d.Van.transform.right) > 0f ? _d.Van.transform.right : -_d.Van.transform.right) * 1.6f;
            if (Vector3.Distance(transform.position, side) > 1.2f) return Steer(side, Mathf.Min(RunSpeed, 3f));
            Face(v);
            if (now >= _nextBang)
            {
                _nextBang = now + Random.Range(0.6f, 1.1f);
                Sfx.PlayAt(SfxIds.ThudVan, side + Vector3.up * 1.2f, 0.8f);
            }
            // Step 5: shakes his fist at the van, again each time the clip is over (while he stands there).
            if (now >= _nextFist && _npc.Anim != null && _npc.Anim.Trigger(NpcAnimTrigger.ShakeFist))
                _nextFist = now + _npc.Anim.Seconds(NpcAnimContract.RoleShakeFist) + Random.Range(0.2f, 0.8f);
            return Vector3.zero;
        }

        private Vector3 TickReturn()
        {
            if (CrewOf != null)
            {
                Vector3 car = CrewOf.transform.position;
                if (Vector3.Distance(transform.position, car) < 2.5f)
                {
                    Board(false);
                    return Vector3.zero;
                }
                // The car left without him.
                if (CrewOf.State != PoliceUnit.UnitState.Dismount)
                {
                    Orphan();
                    return Vector3.zero;
                }
                return Steer(car, RunSpeed);
            }
            if (_walker != null)
            {
                Say(null);
                _walker.Suspended = false; // back to the crowd's patrol loop (it paths there itself)
                State = OfficerState.Idle;
                return Vector3.zero;
            }
            Enter(OfficerState.Leave);
            return Vector3.zero;
        }

        // To the nearest crowd despawn point, then off the map once no camera sees him (back in the car's crew later).
        private Vector3 TickLeave(float now)
        {
            CrowdDirector crowd = _d.Crowd;
            if (crowd == null || crowd.Map == null || crowd.Map.Spawns.Count == 0)
            {
                Vanish();
                return Vector3.zero;
            }
            if (_path.Count == 0 && now >= _nextPath)
            {
                Vector2 here = PoliceDirector.Plan(transform.position);
                float best = float.MaxValue;
                Vector2 goal = here;
                foreach (CrowdSpawn s in crowd.Map.Spawns)
                {
                    float d = (s.Position - here).sqrMagnitude;
                    if (d < best)
                    {
                        best = d;
                        goal = s.Position;
                    }
                }
                _goal = new Vector3(goal.x, transform.position.y, goal.y);
            }
            float flat = Vector2.Distance(PoliceDirector.Plan(transform.position), PoliceDirector.Plan(_goal));
            if ((flat < 2f || now - _stateSince > 90f) && !crowd.Visible(transform.position, 25f))
            {
                Vanish();
                return Vector3.zero;
            }
            return flat < 2f ? Vector3.zero : PathTo(_goal, 1.4f, now);
        }

        private void Vanish()
        {
            if (CrewOf != null)
            {
                Orphaned = true;
                State = OfficerState.Idle;
                gameObject.SetActive(false); // the car reclaims him (PoliceUnit.ReclaimCrew)
                return;
            }
            gameObject.SetActive(false); // a crowd officer the crowd let go of: the crowd already sent a replacement
        }

        // ---------- Movement ----------

        private Vector3 PathTo(Vector3 goal, float speed, float now)
        {
            CrowdDirector crowd = _d.Crowd;
            if (crowd == null || crowd.Map == null) return Steer(goal, speed);
            if (now >= _nextPath)
            {
                _nextPath = now + 1f;
                _path.Clear();
                _pathIndex = 0;
                CrowdGraph graph = crowd.Map.Graph;
                Vector2 from = PoliceDirector.Plan(transform.position), to = PoliceDirector.Plan(goal);
                int a = graph.Nearest(from, CrowdProfile.Town), b = graph.Nearest(to, CrowdProfile.Town);
                if (a >= 0 && b >= 0 && graph.FindPath(a, b, CrowdProfile.Town, _path)) _path.Add(to);
                else _path.Add(to);
            }
            Vector2 pos = PoliceDirector.Plan(transform.position);
            while (_pathIndex < _path.Count - 1 && (_path[_pathIndex] - pos).sqrMagnitude < 1f) _pathIndex++;
            if (_pathIndex >= _path.Count) return Vector3.zero;
            Vector2 next = _path[_pathIndex];
            return Steer(new Vector3(next.x, transform.position.y, next.y), speed);
        }

        private Vector3 Steer(Vector3 to, float speed)
        {
            Vector3 d = to - transform.position;
            d.y = 0f;
            float dist = d.magnitude;
            if (dist < 0.3f) return Vector3.zero;
            return d / dist * Mathf.Min(speed, dist * 4f);
        }

        private void Face(Vector3 point)
        {
            Vector3 d = point - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude > 1e-4f)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(d), 540f * Time.deltaTime);
        }

        /// <summary>Trips now (Move rolls it for the fat one while he runs: FatTripPerSecond). Stage 9 step 4: through the
        /// ragdoll, lying TripTime, then up with the get-up clip (GreyboxNpc.Stumble; not Down meanwhile, his state carries
        /// on); without a ragdoll for him the old look, face down for TripTime. False if he cannot trip now.</summary>
        public bool Trip()
        {
            if (_npc == null || Down || Inside || _npc.Stumbling || !isActiveAndEnabled) return false;
            float lie = _d != null ? C.TripTime : 1.2f;
            if (_npc.Stumble(_controller != null && _controller.enabled ? _controller.velocity : Vector3.zero, lie))
            {
                _tripUntil = 0f;
                return true;
            }
            _tripUntil = Time.time + lie;
            Sfx.PlayAt(SfxIds.ThudGround, transform.position, 0.6f);
            return true;
        }

        // Step 5: the fat one's trip starts with the Cop_Trip clip when the rig has it (a stumble that ends in the dive the
        // ragdoll takes over); Move calls Trip at its end. False without the clip (Trip goes down at once).
        private bool BeginTrip(Vector3 velocity)
        {
            NpcAnimDriver anim = _npc.Anim;
            float seconds = anim != null ? anim.Seconds(NpcAnimContract.RoleTrip) : 0f;
            if (seconds <= 0f || !anim.Trigger(NpcAnimTrigger.Trip)) return false;
            _tripLeadFrom = Time.time;
            _tripLeadUntil = Time.time + seconds * 0.95f; // the ragdoll before the clip hands back to the run
            _tripVelocity = velocity;
            return true;
        }

        private void Move(Vector3 velocity, float now)
        {
            float dt = Time.deltaTime;
            if (_tripLeadUntil > 0f)
            {
                // Stumbling (BeginTrip): on with his momentum, slowing down a little, then down through the ragdoll.
                if (now >= _tripLeadUntil)
                {
                    _tripLeadUntil = 0f;
                    if (Trip() && _npc.Stumbling) return;
                }
                else
                {
                    float k = Mathf.InverseLerp(_tripLeadFrom, _tripLeadUntil, now);
                    velocity = _tripVelocity * Mathf.Lerp(1f, 0.6f, k);
                }
            }
            // The fat one trips now and then while running: down on his face for a moment (through the ragdoll: Trip;
            // step 5: after the Cop_Trip stumble when the rig has it).
            else if (Fat && velocity.magnitude > 3f && now >= _tripUntil && Random.value < C.FatTripPerSecond * dt &&
                     !BeginTrip(velocity) && Trip() && _npc.Stumbling)
                return;
            bool tripped = now < _tripUntil;
            if (_visual != null) _visual.localRotation = tripped ? _visualRotation * Quaternion.Euler(80f, 0f, 0f) : _visualRotation;
            if (tripped) velocity = Vector3.zero;
            _vy = _controller.isGrounded ? -1f : _vy - 20f * dt;
            if (_controller.enabled) _controller.Move((velocity + Vector3.up * _vy) * dt);
            float speed = velocity.magnitude;
            if (speed > 0.05f)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(velocity), 540f * dt);
            float planarSpeed = _controller.enabled
                ? Vector3.ProjectOnPlane(_controller.velocity, Vector3.up).magnitude : 0f;
            // Step 5: the driver picks Idle / Walk / the police run (the fat one's own run, else the run x FatAnimFactor).
            NpcAnimDriver anim = _npc.Anim;
            if (anim == null) return;
            float rate = Fat && !anim.Has(NpcAnimContract.RoleRunCopFat) ? C.FatAnimFactor : 1f;
            anim.SetMove(tripped ? 0f : planarSpeed, Fat ? NpcGait.PoliceFat : NpcGait.Police, rate);
            anim.SetAim(State == OfficerState.Aim);
        }
    }
}
