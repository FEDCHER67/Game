using System;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Map;
using OnlyVolunteers.Police;
using UnityEngine;

namespace OnlyVolunteers.Vehicles
{
    // Local presentation only. One instance follows each van or police motor; a second instance on a persistent
    // bootstrap object discovers motors placed in the scene and police cars spawned later.
    public sealed class VehicleEngineAudio : MonoBehaviour
    {
        private const float EngineSmoothTime = 0.08f;
        private const float ShiftDuration = 0.15f;
        private const float SurfaceCheckInterval = 0.2f;
        private const float SurfaceCrossfade = 0.3f;
        private const float SkidSurfaceCheckInterval = 0.1f;
        private const float SkidCrossfade = 0.15f;
        private const float StartOverlap = 0.7f;
        private static readonly float[] VanGearEnds = { 0.18f, 0.42f, 0.68f, 1f };
        private static readonly float[] PoliceGearEnds = { 0.15f, 0.32f, 0.5f, 0.7f, 1f };

        private static VehicleEngineAudio _bootstrap;
        public static bool DebugLog;
        private bool _scanner;
        private float _nextScan;
#if UNITY_EDITOR
        private float _nextDebugLog;
#endif

        private VanController _van;
        private VanDriveInput _input;
        private GreyboxVanSeat _seat;
        private PoliceCarMotor _police;
        private readonly AudioSource[] _engine = new AudioSource[3];
        private readonly float[] _smoothedVolume = new float[3];
        private readonly float[] _volumeVelocity = new float[3];
        private readonly float[] _pitchVelocity = new float[3];
        private AudioSource _dirt;
        private AudioSource _grass;
        private AudioSource _skid;
        private readonly AudioSource[] _otherSkids = new AudioSource[4];
        private SkidSurface _skidSurface;
        private float _nextSkidSurfaceCheck;
        private float _nextGravelSpray;
        private float _skidLevel;
        private WheelCollider[] _wheels;
        private readonly float[] _lastCompression = new float[4];
        private readonly bool[] _compressionReady = new bool[4];
        private bool _lastHandbrake;
        private float _nextRattle;
        private float _nextSurfaceCheck;
        private SurfaceBed _surface;
        private float _rearSideSlip;
        private float _lastRearSideSlip;
        private float _lastSlipSampleTime;
        private bool _slipReady;
        private bool _wheelspinArmed = true;
        private float _nextChirp;
        private float _lastBrakeSpeed;
        private bool _brakeSampleReady;
        private bool _brakeArmed = true;
        private float _brakeRearmTime;
        private float _restGain = 1f;

        private bool _engineWanted;
        private float _engineFade;
        private float _startDelay;
        private float _throttle01;
        private float _throttleVelocity;
        private float _lastPoliceSpeed;
        private int _gear = -1;
        private float _rpm01 = 0.25f;
        private float _shiftFromRpm;
        private float _shiftRemaining;

        private enum SurfaceBed : byte { None, Dirt, Grass }
        private enum SkidSurface : byte { Asphalt, Gravel, Grass, Sand, Mud }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            _bootstrap = null;
            DebugLog = false;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (_bootstrap != null) return;
            var root = new GameObject("Vehicle engine audio bootstrap");
            DontDestroyOnLoad(root);
            _bootstrap = root.AddComponent<VehicleEngineAudio>();
            _bootstrap.ScanScene();
        }

        private void Awake()
        {
            _van = GetComponent<VanController>();
            _police = GetComponent<PoliceCarMotor>();
            if (_van == null && _police == null)
            {
                _scanner = true;
                return;
            }

            bool police = _police != null;
            if (!police)
            {
                _input = GetComponent<VanDriveInput>();
                _seat = GetComponent<GreyboxVanSeat>();
                _wheels = new[] { _van.Front.Left, _van.Front.Right, _van.Rear.Left, _van.Rear.Right };
                _lastHandbrake = _van.Handbrake;
            }
            else
            {
                _lastPoliceSpeed = Mathf.Abs(_police.Speed);
            }

            float maxDistance = police ? 60f : 40f;
            _engine[0] = MakeLoop(police ? SfxIds.PoliceEngineIdle : SfxIds.VanEngineIdle, maxDistance, 70);
            _engine[1] = MakeLoop(police ? SfxIds.PoliceEngineLow : SfxIds.VanEngineLow, maxDistance, 70);
            _engine[2] = MakeLoop(police ? SfxIds.PoliceEngineHigh : SfxIds.VanEngineHigh, maxDistance, 70);
            if (!police)
            {
                _dirt = MakeLoop(SfxIds.VanDriveDirt, maxDistance, 80, false);
                _grass = MakeLoop(SfxIds.VanDriveGrass, maxDistance, 80, false);
                _skid = MakeLoop(SfxIds.VanTireSkid, maxDistance, 80, false);
                _otherSkids[0] = MakeLoop(SfxIds.VanSkidGravel, maxDistance, 80, false);
                _otherSkids[1] = MakeLoop(SfxIds.VanSkidGrass, maxDistance, 80, false);
                _otherSkids[2] = MakeLoop(SfxIds.VanSkidSand, maxDistance, 80, false);
                _otherSkids[3] = MakeLoop(SfxIds.VanSkidMud, maxDistance, 80, false);
            }
        }

        private AudioSource MakeLoop(string id, float maxDistance, int priority, bool engine = true)
        {
            AudioSource source = gameObject.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.loop = true;
            source.spatialBlend = 1f;
            source.minDistance = engine && _van != null ? 6f : 4f;
            source.maxDistance = maxDistance;
            source.rolloffMode = AudioRolloffMode.Logarithmic;
            source.dopplerLevel = 0f; // engine pitch is controlled by the fake gearbox
            source.priority = priority;
            source.volume = 0f;
            SfxLibrary library = Sfx.Library;
            source.outputAudioMixerGroup = library != null ? library.Output : null;
            SfxLibrary.Entry entry = library != null ? library.Find(id) : null;
            if (entry != null && entry.Clips != null)
            {
                for (int i = 0; i < entry.Clips.Length; i++)
                    if (entry.Clips[i] != null) { source.clip = entry.Clips[i]; break; }
            }
            return source;
        }

        private void Update()
        {
            if (_scanner)
            {
                if (Time.time >= _nextScan) ScanScene();
                return;
            }

            float dt = Time.deltaTime;
            bool wanted = _police != null ? _police.isActiveAndEnabled :
                _seat != null ? _seat.Driving : _input != null && _input.isActiveAndEnabled;
            if (_van != null)
            {
                float spatialBlend = wanted ? 0.6f : 1f;
                for (int i = 0; i < _engine.Length; i++) _engine[i].spatialBlend = spatialBlend;
                _dirt.spatialBlend = spatialBlend;
                _grass.spatialBlend = spatialBlend;
                _skid.spatialBlend = spatialBlend;
                for (int i = 0; i < _otherSkids.Length; i++) _otherSkids[i].spatialBlend = spatialBlend;
            }
            if (wanted != _engineWanted)
            {
                _engineWanted = wanted;
                if (wanted)
                {
                    string startId = _police != null ? SfxIds.PoliceEngineStart : SfxIds.VanEngineStart;
                    _startDelay = Sfx.PlayAt(startId, transform.position) ?
                        Mathf.Max(0f, FirstClipLength(startId) - StartOverlap) : 0f;
                    for (int i = 0; i < _engine.Length; i++) PlayIfReady(_engine[i]);
                }
                else if (_van != null)
                {
                    _startDelay = 0f;
                    Sfx.PlayAt(SfxIds.VanEngineStop, transform.position);
                }
                else _startDelay = 0f;
            }

            UpdateEngine(dt);
            if (_van != null)
            {
                UpdateSurface(dt);
                UpdateSkid(dt);
            }
#if UNITY_EDITOR
            if (_van != null && DebugLog && Time.time >= _nextDebugLog)
            {
                _nextDebugLog = Time.time + 1f;
                Debug.Log($"VehicleEngineAudio van: engineWanted={_engineWanted}, startDelay={_startDelay:F2}, engineFade={_engineFade:F2}, rpm01={_rpm01:F2}, idle={_engine[0].volume:F2}/{_engine[0].isPlaying}, low={_engine[1].volume:F2}/{_engine[1].isPlaying}, high={_engine[2].volume:F2}/{_engine[2].isPlaying}", this);
            }
#endif
        }

        private void UpdateEngine(float dt)
        {
            float speedKmh = Mathf.Abs(_police != null ? _police.SpeedKmh : _van.SpeedKmh);
            float maxKmh = _police != null ? Mathf.Max(1f, _police.MaxSpeed * 3.6f) : Mathf.Max(1f, _van.MaxSpeedKmh);
            float speed01 = Mathf.Clamp01(speedKmh / maxKmh);
            if (_van != null)
            {
                _throttle01 = Mathf.SmoothDamp(_throttle01, Mathf.Clamp01(Mathf.Abs(_van.Throttle)),
                    ref _throttleVelocity, EngineSmoothTime, Mathf.Infinity, dt);
            }
            else
            {
                float speed = Mathf.Abs(_police.Speed);
                float acceleration = dt > 0f ? Mathf.Max(0f, (speed - _lastPoliceSpeed) / dt) : 0f;
                _lastPoliceSpeed = speed;
                _throttle01 = Mathf.Clamp01(speed01 + 0.3f * acceleration / 10f);
            }

            float gearRpm = GearRpm(speed01, _police != null, out int gear);
            float rpmTarget = _van != null
                ? Mathf.Max(gearRpm, Mathf.Min(0.85f, 0.25f + 0.6f * _throttle01))
                : Mathf.Max(gearRpm, 0.25f + 0.75f * _throttle01);
            if (_gear >= 0 && gear != _gear)
            {
                _shiftFromRpm = _rpm01;
                _shiftRemaining = ShiftDuration;
            }
            _gear = gear;
            if (_shiftRemaining > 0f)
            {
                _shiftRemaining = Mathf.Max(0f, _shiftRemaining - dt);
                rpmTarget = Mathf.Lerp(_shiftFromRpm, 0.35f, 1f - _shiftRemaining / ShiftDuration);
            }
            float rpmRate = _van != null && _shiftRemaining <= 0f && rpmTarget < _rpm01 ? 1f : 5f;
            _rpm01 = Mathf.MoveTowards(_rpm01, rpmTarget, dt * rpmRate);

            if (_startDelay > 0f) _startDelay = Mathf.Max(0f, _startDelay - dt);
            bool bedOn = _engineWanted && _startDelay <= 0f;
            _engineFade = Mathf.MoveTowards(_engineFade, bedOn ? 1f : 0f,
                dt / (bedOn ? StartOverlap : 0.4f));
            _restGain = _van == null ? 1f :
                speedKmh < 0.5f && _throttle01 < 0.01f ? 0.45f :
                Mathf.Lerp(0.45f, 1f, SmoothStep(0.15f, 0.7f, Mathf.Max(_throttle01, _rpm01)));
            float activity = _rpm01 * Mathf.Max(speed01, _throttle01);
            float idle = 1f - SmoothStep(0.05f, 0.3f, activity);
            float low = SmoothStep(0.1f, 0.45f, _rpm01) * (1f - SmoothStep(0.45f, 0.8f, _rpm01));
            float high = SmoothStep(0.5f, 0.9f, _rpm01);
            float master = 0.9f;
            SetEngineSource(0, idle * master, Mathf.Lerp(0.9f, 1.08f, _rpm01), dt);
            SetEngineSource(1, low * master, Mathf.Lerp(0.85f, 1.35f, _rpm01), dt);
            SetEngineSource(2, high * master, Mathf.Lerp(0.9f, 1.45f, _rpm01), dt);
            if (!_engineWanted && _engineFade <= 0f)
                for (int i = 0; i < _engine.Length; i++)
                    if (_engine[i].isPlaying) _engine[i].Stop();
        }

        private void SetEngineSource(int index, float volume, float pitch, float dt)
        {
            AudioSource source = _engine[index];
            _smoothedVolume[index] = Mathf.SmoothDamp(_smoothedVolume[index], volume, ref _volumeVelocity[index],
                EngineSmoothTime, Mathf.Infinity, dt);
            source.volume = _smoothedVolume[index] * Mathf.Sin(_engineFade * Mathf.PI * 0.5f) * _restGain;
            source.pitch = Mathf.SmoothDamp(source.pitch, pitch, ref _pitchVelocity[index],
                EngineSmoothTime, Mathf.Infinity, dt);
        }

        private static float GearRpm(float speed01, bool police, out int gear)
        {
            float[] ends = police ? PoliceGearEnds : VanGearEnds;
            float start = 0f;
            for (int i = 0; i < ends.Length; i++)
            {
                if (speed01 <= ends[i] || i == ends.Length - 1)
                {
                    gear = i;
                    return Mathf.Lerp(0.25f, 1f, Mathf.InverseLerp(start, ends[i], speed01));
                }
                start = ends[i];
            }
            gear = 0;
            return 0.25f;
        }

        private static float SmoothStep(float low, float high, float value)
        {
            float t = Mathf.Clamp01((value - low) / (high - low));
            return t * t * (3f - 2f * t);
        }

        private static void PlayIfReady(AudioSource source)
        {
            if (source != null && source.clip != null && !source.isPlaying) source.Play();
        }

        private static float FirstClipLength(string id)
        {
            SfxLibrary library = Sfx.Library;
            SfxLibrary.Entry entry = library != null ? library.Find(id) : null;
            if (entry == null || entry.Clips == null) return 0f;
            for (int i = 0; i < entry.Clips.Length; i++)
                if (entry.Clips[i] != null) return entry.Clips[i].length;
            return 0f;
        }

        private void UpdateSurface(float dt)
        {
            if (Time.time >= _nextSurfaceCheck)
            {
                _nextSurfaceCheck = Time.time + SurfaceCheckInterval;
                _surface = SurfaceBed.None;
                CheckRearSurface(_van.Rear.Left);
                CheckRearSurface(_van.Rear.Right);
            }
            float level = 0.8f * SmoothStep(5f, 40f, Mathf.Abs(_van.SpeedKmh));
            float step = dt * 0.8f / SurfaceCrossfade;
            FadeSurface(_dirt, _surface == SurfaceBed.Dirt ? level : 0f, step);
            FadeSurface(_grass, _surface == SurfaceBed.Grass ? level : 0f, step);
        }

        private void UpdateSkid(float dt)
        {
            if (Time.time >= _nextSkidSurfaceCheck)
            {
                _nextSkidSurfaceCheck = Time.time + SkidSurfaceCheckInterval;
                _skidSurface = RearSkidSurface();
            }
            float speed = Mathf.Abs(_van.SpeedKmh);
            float target = SmoothStep(0.25f, 0.7f, _rearSideSlip) * SmoothStep(8f, 30f, speed);
            if (_van.Handbrake && speed > 10f) target = Mathf.Max(target, 0.7f);
            _skidLevel = Mathf.MoveTowards(_skidLevel, target, dt / (target > _skidLevel ? 0.08f : 0.2f));
            float pitch = Mathf.Lerp(0.95f, 1.08f, Mathf.Clamp01(speed / Mathf.Max(1f, _van.MaxSpeedKmh)));
            FadeSurface(_skid, _skidSurface == SkidSurface.Asphalt ? _skidLevel : 0f, dt / SkidCrossfade);
            _skid.pitch = pitch;
            for (int i = 0; i < _otherSkids.Length; i++)
            {
                AudioSource source = _otherSkids[i];
                FadeSurface(source, _skidSurface == (SkidSurface)(i + 1) ? _skidLevel : 0f, dt / SkidCrossfade);
                source.pitch = pitch;
            }
            if (_skidSurface == SkidSurface.Gravel && _skidLevel > 0.05f && Time.time >= _nextGravelSpray)
            {
                Sfx.PlayAt(SfxIds.VanGravelSpray, transform.position, _skidLevel * 0.7f);
                _nextGravelSpray = Time.time + UnityEngine.Random.Range(0.25f, 0.45f);
            }
        }

        private SkidSurface RearSkidSurface()
        {
            WheelCollider left = _van.Rear.Left;
            WheelCollider right = _van.Rear.Right;
            WheelHit leftHit = default;
            WheelHit rightHit = default;
            bool hasLeft = left != null && left.GetGroundHit(out leftHit) && leftHit.collider != null;
            bool hasRight = right != null && right.GetGroundHit(out rightHit) && rightHit.collider != null;
            if (!hasLeft && !hasRight) return SkidSurface.Asphalt;
            WheelHit hit = hasLeft && (!hasRight || Mathf.Abs(leftHit.sidewaysSlip) >= Mathf.Abs(rightHit.sidewaysSlip))
                ? leftHit : rightHit;
            switch (SfxSurfaces.At(hit.collider, hit.point))
            {
                case SfxSurface.Gravel: return SkidSurface.Gravel;
                case SfxSurface.Grass: return SkidSurface.Grass;
                case SfxSurface.Sand: return SkidSurface.Sand;
                case SfxSurface.Mud: return SkidSurface.Mud;
                default: return SkidSurface.Asphalt;
            }
        }

        private void CheckRearSurface(WheelCollider wheel)
        {
            if (wheel == null || !wheel.GetGroundHit(out WheelHit hit) || hit.collider == null) return;
            SfxSurface surface = SfxSurfaces.At(hit.collider, hit.point);
            if (surface == SfxSurface.Sand || surface == SfxSurface.Gravel || surface == SfxSurface.Mud)
                _surface = SurfaceBed.Dirt;
            else if (surface == SfxSurface.Grass && _surface == SurfaceBed.None)
                _surface = SurfaceBed.Grass;
        }

        // SfxSurfaces groups dirt with grass for footsteps. Keep its terrain/material detection, then distinguish
        // dirt names here so a dirt road drives the dirt bed while a meadow drives the grass bed.
        private static bool IsDirt(Collider ground, Vector3 point)
        {
            if (ground is TerrainCollider && ground.TryGetComponent(out Terrain terrain) && terrain.terrainData != null)
            {
                TerrainData data = terrain.terrainData;
                if (data.alphamapLayers > 0 && data.size.x > 0f && data.size.z > 0f)
                {
                    Vector3 local = point - terrain.transform.position;
                    int x = Mathf.Clamp(Mathf.FloorToInt(local.x / data.size.x * data.alphamapWidth), 0, data.alphamapWidth - 1);
                    int z = Mathf.Clamp(Mathf.FloorToInt(local.z / data.size.z * data.alphamapHeight), 0, data.alphamapHeight - 1);
                    float[,,] weights = data.GetAlphamaps(x, z, 1, 1);
                    int best = 0;
                    for (int i = 1; i < data.alphamapLayers; i++)
                        if (weights[0, 0, i] > weights[0, 0, best]) best = i;
                    TerrainLayer[] layers = data.terrainLayers;
                    return best < layers.Length && layers[best] != null && DirtName(layers[best].name);
                }
            }
            Renderer renderer = ground.GetComponent<Renderer>();
            if (renderer == null) renderer = ground.GetComponentInParent<Renderer>();
            Material material = renderer != null ? renderer.sharedMaterial : null;
            return DirtName(material != null ? material.name : ground.gameObject.name);
        }

        private static bool DirtName(string name) => !string.IsNullOrEmpty(name) &&
            (name.IndexOf("dirt", StringComparison.OrdinalIgnoreCase) >= 0 ||
             name.IndexOf("mud", StringComparison.OrdinalIgnoreCase) >= 0 ||
             name.IndexOf("soil", StringComparison.OrdinalIgnoreCase) >= 0 ||
             name.IndexOf("gravel", StringComparison.OrdinalIgnoreCase) >= 0 ||
             name.IndexOf("sand", StringComparison.OrdinalIgnoreCase) >= 0 ||
             name.IndexOf("ballast", StringComparison.OrdinalIgnoreCase) >= 0);

        private static void FadeSurface(AudioSource source, float target, float step)
        {
            source.volume = Mathf.MoveTowards(source.volume, target, step);
            if (target > 0f) PlayIfReady(source);
            else if (source.volume <= 0f && source.isPlaying) source.Stop();
        }

        private void FixedUpdate()
        {
            if (_van == null) return;
            float jump = 0f;
            float rearSlipSum = 0f;
            int groundedRear = 0;
            for (int i = 0; i < _wheels.Length; i++)
            {
                WheelCollider wheel = _wheels[i];
                if (wheel == null) continue;
                float compression = 0f;
                if (wheel.GetGroundHit(out WheelHit hit))
                {
                    if (i >= 2)
                    {
                        rearSlipSum += Mathf.Abs(hit.sidewaysSlip);
                        groundedRear++;
                    }
                    // Same wheel travel geometry as VanController.ApplyAntiRoll: convert it to metres of compression.
                    float travel = (-wheel.transform.InverseTransformPoint(hit.point).y - wheel.radius) /
                        Mathf.Max(0.001f, wheel.suspensionDistance);
                    compression = (1f - Mathf.Clamp01(travel)) * wheel.suspensionDistance;
                }
                if (_compressionReady[i]) jump = Mathf.Max(jump, Mathf.Abs(compression - _lastCompression[i]));
                _lastCompression[i] = compression;
                _compressionReady[i] = true;
            }
            _rearSideSlip = groundedRear > 0 ? rearSlipSum / groundedRear : 0f;
            float speed = Mathf.Abs(_van.SpeedKmh);
            float throttle = Mathf.Abs(_van.Throttle);
            bool slipChirp = _slipReady && _lastRearSideSlip <= 0.45f && _rearSideSlip > 0.45f &&
                Time.fixedTime - _lastSlipSampleTime <= 0.1f && speed > 20f;
            if (throttle < 0.2f) _wheelspinArmed = true;
            bool wheelspinChirp = _wheelspinArmed && throttle > 0.8f && speed < 10f;
            if (throttle > 0.8f) _wheelspinArmed = false;
            if (_skidSurface == SkidSurface.Asphalt && (slipChirp || wheelspinChirp) && Time.time >= _nextChirp &&
                Sfx.PlayAt(SfxIds.VanTireChirp, transform.position))
                _nextChirp = Time.time + 0.8f;
            _lastRearSideSlip = _rearSideSlip;
            _lastSlipSampleTime = Time.fixedTime;
            _slipReady = true;
            if (speed > 30f || Time.time >= _brakeRearmTime) _brakeArmed = true;
            bool decelerating = _brakeSampleReady && _lastBrakeSpeed - speed > 0.5f * Time.fixedDeltaTime;
            bool braking = _van.SpeedKmh * _van.Throttle < -0.1f;
            if (_brakeArmed && braking && decelerating && speed >= 3f && speed <= 25f &&
                Sfx.PlayAt(SfxIds.VanBrakeSqueak, transform.position))
            {
                _brakeArmed = false;
                _brakeRearmTime = Time.time + 4f;
            }
            _lastBrakeSpeed = speed;
            _brakeSampleReady = true;
            if (jump > 0.06f && Time.time >= _nextRattle)
            {
                float volume = Mathf.Lerp(0.4f, 1f, Mathf.InverseLerp(0.06f, 0.25f, jump));
                if (Sfx.PlayAt(SfxIds.VanBodyRattle, transform.position, volume))
                    _nextRattle = Time.time + 0.35f;
            }
            bool handbrake = _van.Handbrake;
            if (handbrake && !_lastHandbrake && Mathf.Abs(_van.SpeedKmh) > 3f)
                Sfx.PlayAt(SfxIds.VanHandbrake, transform.position);
            _lastHandbrake = handbrake;
        }

        private void OnDisable()
        {
            if (_scanner) return;
            for (int i = 0; i < _engine.Length; i++)
                if (_engine[i] != null) { _engine[i].volume = 0f; _engine[i].Stop(); }
            if (_dirt != null) _dirt.Stop();
            if (_grass != null) _grass.Stop();
            if (_skid != null) _skid.Stop();
            for (int i = 0; i < _otherSkids.Length; i++)
                if (_otherSkids[i] != null) _otherSkids[i].Stop();
            _engineWanted = false;
            _engineFade = 0f;
            _startDelay = 0f;
        }

        private void ScanScene()
        {
            _nextScan = Time.time + 2f;
            foreach (VanController van in FindObjectsByType<VanController>())
                if (van != null && !van.TryGetComponent(out VehicleEngineAudio _))
                    van.gameObject.AddComponent<VehicleEngineAudio>();
            foreach (PoliceCarMotor police in FindObjectsByType<PoliceCarMotor>())
                if (police != null && !police.TryGetComponent(out VehicleEngineAudio _))
                    police.gameObject.AddComponent<VehicleEngineAudio>();
        }
    }
}
