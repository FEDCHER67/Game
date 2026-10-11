using System.Collections.Generic;
using KinematicCharacterController;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Player;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Audio
{
    // Registered once per entity. One physics watcher samples a ragdoll's pelvis, never all its limbs.
    [DisallowMultipleComponent]
    public sealed class WaterBodyAudio : MonoBehaviour
    {
        private static readonly List<WaterBodyAudio> Bodies = new List<WaterBodyAudio>(128);
        private static WaterBodyAudio _watcher;
        private bool _manager;
        private KccFirstPersonInput _kcc;
        private GreyboxNpc _npc;
        private CharacterController _controller;
        private Rigidbody _rigidbody;
        private AudioSource _wade;
        private Vector3 _previous;
        private Rigidbody _previousBody;
        private bool _ready, _deep, _airborne;
        private float _nextSplash, _stepDistance, _wadeLevel;
        private int _drips;
        private float _nextDrip, _dripInterval;

        public static void Ensure(GameObject body)
        {
            if (!body.TryGetComponent(out WaterBodyAudio _)) body.AddComponent<WaterBodyAudio>();
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void Reset()
        {
            WorldItem.Enabled -= ItemEnabled;
            OfflineWorldItem.Enabled -= OfflineItemEnabled;
            SceneManager.sceneLoaded -= SceneLoaded;
            Bodies.Clear();
            _watcher = null;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void Subscribe()
        {
            WorldItem.Enabled += ItemEnabled;
            OfflineWorldItem.Enabled += OfflineItemEnabled;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (_watcher == null)
            {
                var root = new GameObject("Water body audio watcher");
                DontDestroyOnLoad(root);
                _watcher = root.AddComponent<WaterBodyAudio>();
            }
            SceneManager.sceneLoaded -= SceneLoaded;
            SceneManager.sceneLoaded += SceneLoaded;
            SceneLoaded(default, LoadSceneMode.Single);
        }

        private static void ItemEnabled(WorldItem item) => Ensure(item.gameObject);
        private static void OfflineItemEnabled(OfflineWorldItem item) => Ensure(item.gameObject);
        private static void SceneLoaded(Scene scene, LoadSceneMode mode)
        {
            // Handles direct scene entry / domain reload; later drops register through their enable events.
            foreach (WorldItem item in Object.FindObjectsByType<WorldItem>()) ItemEnabled(item);
            foreach (OfflineWorldItem item in Object.FindObjectsByType<OfflineWorldItem>()) OfflineItemEnabled(item);
        }

        private void Awake()
        {
            _kcc = GetComponent<KccFirstPersonInput>();
            _npc = GetComponent<GreyboxNpc>();
            _controller = GetComponent<CharacterController>();
            _rigidbody = GetComponent<Rigidbody>();
            _manager = _kcc == null && _npc == null && _rigidbody == null &&
                GetComponent<WorldItem>() == null && GetComponent<OfflineWorldItem>() == null;
            if (_kcc != null || _npc != null) _wade = WaterLoop.Create(gameObject, SfxIds.WaterWade, 2f, 25f);
        }

        private void OnEnable()
        {
            _ready = false; _deep = false; _drips = 0; _stepDistance = 0f;
            if (!_manager && !Bodies.Contains(this)) Bodies.Add(this);
        }

        private void OnDisable()
        {
            Bodies.Remove(this);
            _drips = 0;
            _wadeLevel = 0f;
            if (_wade != null) { _wade.Stop(); _wade.volume = 0f; }
        }

        private void OnDestroy()
        {
            if (_watcher != this) return;
            WorldItem.Enabled -= ItemEnabled;
            OfflineWorldItem.Enabled -= OfflineItemEnabled;
            SceneManager.sceneLoaded -= SceneLoaded;
            _watcher = null;
        }

        private void FixedUpdate()
        {
            if (!_manager) return;
            for (int i = 0; i < Bodies.Count; i++)
                if (Bodies[i] != null && Bodies[i].isActiveAndEnabled) Bodies[i].Tick();
        }

        public void Rebase()
        {
            _ready = false; _deep = false; _drips = 0; _stepDistance = 0f;
        }

        private void Tick()
        {
            Vector3 point = transform.position, velocity = Vector3.zero;
            Rigidbody body = _rigidbody;
            bool walking = false, grounded = false;
            float mass = body != null ? body.mass : 1f;
            if (_kcc != null && _kcc.Character != null && _kcc.Character.Motor != null)
            {
                KinematicCharacterMotor motor = _kcc.Character.Motor;
                body = null; // KCC splash position is its feet, even if the prefab also has a Rigidbody.
                point = motor.TransientPosition;
                velocity = motor.BaseVelocity;
                walking = true;
                grounded = motor.GroundingStatus.IsStableOnGround;
                mass = motor.SimulatedCharacterMass;
            }
            else if (_npc != null)
            {
                INpcBody physical = _npc.PhysicalBody;
                body = physical != null && physical.Active ? physical.MainBody : null;
                if (body != null)
                {
                    point = physical.Landmark(NpcLandmark.Pelvis);
                    mass = _npc.Ragdoll != null && _npc.Ragdoll.Active && _npc.Ragdoll.Profile != null
                        ? _npc.Ragdoll.Profile.TotalMass : body.mass;
                }
                else if (_controller != null && _controller.enabled)
                {
                    walking = true;
                    grounded = _controller.isGrounded;
                    // Displacement covers both CrowdWalker and the NPC's fleeing controller moves.
                    mass = _npc.Body != null ? _npc.Body.Mass : 40f;
                }
            }
            if (body != null) { if (_npc == null) point = body.worldCenterOfMass; velocity = body.linearVelocity; }
            bool continuous = _ready && _previousBody == body;
            if (continuous && body == null && _kcc == null) velocity = (point - _previous) / Time.fixedDeltaTime;
            // Explicit teleports use Rebase; this also suppresses scene/sea-return jumps and large corrections.
            if (continuous && (point - _previous).sqrMagnitude > 100f) continuous = false;
            bool surface = WaterQuery.SurfaceAt(point, out float y, out _);
            bool wet = surface && point.y <= y;
            float depth = wet ? WaterQuery.Depth(point) : 0f;
            bool deep = wet && depth > 0.8f;
            if (continuous && surface && _previous.y > y && point.y <= y && point.y < _previous.y && Time.time >= _nextSplash)
            {
                float t = (_previous.y - y) / (_previous.y - point.y);
                Vector3 crossing = Vector3.Lerp(_previous, point, t);
                // Do not place a splash on land if the sweep entered the water's horizontal bounds later.
                if (WaterQuery.SurfaceAt(crossing, out float crossingY, out _))
                {
                    crossing.y = crossingY;
                    float speed = Mathf.Max(velocity.magnitude, (point - _previous).magnitude / Time.fixedDeltaTime);
                    Sfx.PlayAt(mass < 15f || speed < 3f ? SfxIds.SplashSmall : SfxIds.SplashBig, crossing);
                    if (_kcc != null && (_airborne || !grounded) && WaterQuery.Depth(crossing) > 0.8f)
                        Sfx.PlayAt(SfxIds.WaterJumpIn, crossing);
                    _nextSplash = Time.time + 0.5f;
                }
            }
            if (continuous && _deep && !deep && _kcc != null)
            {
                Sfx.PlayAt(SfxIds.WaterGetOut, point);
                _drips = Random.Range(2, 4);
                _dripInterval = 2f / _drips;
                _nextDrip = Time.time + _dripInterval;
            }
            if (deep) _drips = 0;
            if (_drips > 0 && Time.time >= _nextDrip)
            {
                Sfx.PlayAt(SfxIds.WaterDrip, point);
                _drips--;
                _nextDrip += _dripInterval;
            }
            float speedXZ = new Vector2(velocity.x, velocity.z).magnitude;
            float footDepth = walking ? WaterQuery.FootDepth(point) : 0f;
            if (_wade != null)
            {
                float target = walking && grounded && footDepth > 0.4f && speedXZ > 0.3f ? 1f : 0f;
                _wadeLevel = Mathf.MoveTowards(_wadeLevel, target, Time.fixedDeltaTime / 0.2f);
                WaterLoop.Level(_wade, _wadeLevel);
            }
            // NPCs had no footstep caller. Add watery footfalls here without duplicating crowd/flee locomotion.
            if (_npc != null && continuous && walking && grounded && speedXZ > 0.3f && footDepth >= 0.03f && footDepth <= 0.4f)
            {
                _stepDistance += speedXZ * Time.fixedDeltaTime;
                bool run = _npc.Fleeing || speedXZ > 3f;
                float stride = run ? 2.75f : 0.8f;
                if (_stepDistance >= stride)
                {
                    _stepDistance -= stride;
                    Sfx.PlayAt(run ? SfxIds.StepWaterRun : SfxIds.StepWater, point, 0.6f);
                }
            }
            else _stepDistance = 0f;
            _previous = point; _previousBody = body; _ready = true; _deep = deep; _airborne = walking && !grounded;
        }
    }

    internal static class WaterLoop
    {
        public static AudioSource Create(GameObject owner, string id, float min, float max)
        {
            AudioSource source = owner.AddComponent<AudioSource>();
            source.playOnAwake = false; source.loop = true; source.spatialBlend = 1f;
            source.minDistance = min; source.maxDistance = max; source.dopplerLevel = 0f;
            source.rolloffMode = AudioRolloffMode.Logarithmic; source.volume = 0f;
            SfxLibrary library = Sfx.Library;
            source.outputAudioMixerGroup = library != null ? library.Output : null;
            SfxLibrary.Entry entry = library != null ? library.Find(id) : null;
            source.priority = entry != null ? entry.Priority : 100;
            if (entry != null && entry.Clips != null)
                for (int i = 0; i < entry.Clips.Length; i++)
                    if (entry.Clips[i] != null) { source.clip = entry.Clips[i]; break; }
            return source;
        }

        public static void Level(AudioSource source, float level)
        {
            source.volume = Mathf.Clamp01(level);
            if (level > 0f && source.clip != null && !source.isPlaying) source.Play();
            else if (level <= 0f && source.isPlaying) source.Stop();
        }
    }
}
