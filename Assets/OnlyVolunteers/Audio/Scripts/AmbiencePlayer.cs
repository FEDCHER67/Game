using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Audio
{
    // Local presentation only. A scene needs a main camera with an enabled AudioListener and a baked Resources asset.
    public sealed class AmbiencePlayer : MonoBehaviour
    {
        private const float SampleInterval = 0.25f;
        private const float DistrictHold = 1f;
        private const float FadeSeconds = 2f;
        private const float HalfPi = 1.57079632679f;

        [SerializeField, Range(0f, 1f)] private float masterVolume = 0.8f;
        // Optional scene-owned revision, used by G18 to preserve the approved checkpoint asset.
        public AmbienceData SceneData;

        public static bool Muted;

        private static AmbiencePlayer _instance;

        private AmbienceData _data;
        private Transform _listener;
        private bool _listenerActive;
        private SfxLibrary _library;
        private AudioSource _bedA;
        private AudioSource _bedB;
        private AudioSource _sea;
        private AudioSource _office;
        private AudioSource[] _fountains;
        private AudioSource[] _districtBeds, _spots;
        private float[] _spatialWeights, _spatialLevels;
        private WaterData _water;
        private AudioSource[] _waterSources;
        private bool[] _waterSelected;
        private float[] _waterGains;

        private int _lastHit = -1;
        private int _activeDistrict = int.MinValue;
        private int _candidateDistrict = int.MinValue;
        private float _candidateSince;
        private float _sampleTimer;

        private float _weightA;
        private float _weightB;
        private float _fadeFromA;
        private float _fadeFromB;
        private float _fadeToA;
        private float _fadeToB;
        private float _fadeTime;
        private bool _fading;

        private float _seaTarget;
        private float _officeTarget;
        private float _seaLevel;
        private float _officeLevel;

        public float MasterVolume
        {
            get { return masterVolume; }
            set { masterVolume = Mathf.Clamp01(value); }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            SceneManager.sceneLoaded -= SceneLoaded;
            _instance = null;
            Muted = false;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            SceneManager.sceneLoaded -= SceneLoaded;
            SceneManager.sceneLoaded += SceneLoaded;
            TryCreate();
        }

        private static void SceneLoaded(Scene scene, LoadSceneMode mode)
        {
            TryCreate();
        }

        private static void TryCreate()
        {
            if (_instance != null) return;
            // The ambience of the scene's own plan revision (Map_Greybox_v16 -> Ambience_v16), else the v12-era Ambience_latest.
            System.Text.RegularExpressions.Match revision =
                System.Text.RegularExpressions.Regex.Match(SceneManager.GetActiveScene().name, @"_(v\d+)(_|$)");
            AmbienceData data = revision.Success ? Resources.Load<AmbienceData>("Ambience_" + revision.Groups[1].Value) : null;
            if (data == null) data = Resources.Load<AmbienceData>("Ambience_latest");
            if (data == null) return;
            Camera camera = Camera.main;
            if (camera == null) return;
            AudioListener listener = camera.GetComponent<AudioListener>();
            if (listener == null || !listener.enabled) return;

            AmbiencePlayer existing = Object.FindFirstObjectByType<AmbiencePlayer>();
            if (existing != null)
            {
                if (existing.SceneData != null) data = existing.SceneData;
                _instance = existing;
                existing.Initialize(data, listener.transform);
                return;
            }

            GameObject root = new GameObject("AmbiencePlayer");
            AmbiencePlayer player = root.AddComponent<AmbiencePlayer>();
            _instance = player;
            player.Initialize(data, listener.transform);
        }

        private void Initialize(AmbienceData data, Transform listener)
        {
            if (_data != null) return;
            _data = data;
            _listener = listener;
            _listenerActive = true;
            _library = Sfx.Library;

            if (_data.PlanRevision == "v19" && _data.DistrictBlendMetres > 0 &&
                _data.BlendBounds.Length == _data.Districts.Length)
            {
                int n = _data.Districts.Length;
                _districtBeds = new AudioSource[n]; _spatialWeights = new float[n]; _spatialLevels = new float[n];
                for (int i = 0; i < n; i++)
                {
                    var mapping = _data.MappingFor(_data.Districts[i].Id);
                    var entry = mapping != null ? Entry(mapping.AmbienceId) : null;
                    if (entry == null || entry.Clips == null || entry.Clips.Length == 0) continue;
                    _districtBeds[i] = CreateSource("Spatial district " + _data.Districts[i].Id, entry, false);
                    StartLoop(_districtBeds[i], entry);
                }
            }
            _spots = new AudioSource[_data.Spots != null ? _data.Spots.Length : 0];
            for (int i = 0; i < _spots.Length; i++)
            {
                var spot = _data.Spots[i]; var entry = Entry(spot.SoundId);
                if (entry == null || entry.Clips == null || entry.Clips.Length == 0) continue;
                _spots[i] = CreateSource("Life " + spot.Name, entry, true);
                _spots[i].transform.position = spot.Position; _spots[i].minDistance = 2;
                _spots[i].maxDistance = spot.Range; _spots[i].rolloffMode = AudioRolloffMode.Linear;
                StartLoop(_spots[i], entry);
            }

            _bedA = CreateSource("District A", null, false);
            _bedB = CreateSource("District B", null, false);
            _sea = CreateSource("Sea and gulls", Entry("amb_sea_gulls"), false);
            _office = CreateSource("Office murmur", Entry("amb_office"), false);
            StartLoop(_sea, Entry("amb_sea_gulls"));
            StartLoop(_office, Entry("amb_office"));

            Vector3[] positions = _data.Fountains;
            int count = positions != null ? positions.Length : 0;
            _fountains = new AudioSource[count];
            SfxLibrary.Entry fountainEntry = Entry("amb_fountain");
            for (int i = 0; i < count; i++)
            {
                AudioSource source = CreateSource("Fountain " + (i + 1), fountainEntry, true);
                Vector3 position = positions[i];
                RaycastHit hit;
                if (Physics.Raycast(new Vector3(position.x, 1000f, position.z), Vector3.down,
                                    out hit, 2000f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
                    position.y = hit.point.y;
                source.transform.position = position + Vector3.up * 0.5f;
                source.minDistance = 3f;
                source.maxDistance = 25f;
                source.rolloffMode = AudioRolloffMode.Logarithmic;
                StartLoop(source, fountainEntry);
                _fountains[i] = source;
            }

            _water = WaterQuery.Data;
            int waterCount = _water != null && _water.Emitters != null ? _water.Emitters.Length : 0;
            _waterSources = new AudioSource[waterCount];
            _waterSelected = new bool[waterCount];
            _waterGains = new float[waterCount];
            for (int i = 0; i < waterCount; i++)
            {
                WaterData.Emitter emitter = _water.Emitters[i];
                SfxLibrary.Entry entry = Entry(emitter.SoundId);
                AudioSource source = CreateSource("Water " + (i + 1), entry, true);
                source.transform.position = emitter.Position;
                source.minDistance = entry != null ? Mathf.Max(1f, entry.MinDistance) : 4f;
                source.maxDistance = emitter.SoundId == SfxIds.AmbLakeShore ? 40f : 60f;
                source.rolloffMode = AudioRolloffMode.Logarithmic;
                source.clip = Pick(entry);
                _waterSources[i] = source;
                _waterGains[i] = entry != null ? Mathf.Clamp01((entry.Volume.x + entry.Volume.y) * 0.5f) : 0f;
            }

            SampleZones();
            ApplyVolumes();
        }

        private void Update()
        {
            if (_data == null) return;
            float delta = Time.unscaledDeltaTime;
            _sampleTimer += delta;
            if (_sampleTimer >= SampleInterval)
            {
                _sampleTimer = 0f;
                SampleZones();
            }

            AdvanceFade(delta);
            if (_spatialLevels != null)
                for (int i = 0; i < _spatialLevels.Length; i++)
                    _spatialLevels[i] = Mathf.Lerp(_spatialLevels[i], _spatialWeights[i], 1-Mathf.Exp(-delta*5));
            _seaLevel = Mathf.MoveTowards(_seaLevel, _seaTarget, delta * 2f);
            _officeLevel = Mathf.MoveTowards(_officeLevel, _officeTarget, delta * 2f);
            ApplyVolumes();
        }

        private void OnDestroy()
        {
            if (_instance == this) _instance = null;
        }

        private AudioSource CreateSource(string name, SfxLibrary.Entry entry, bool threeDimensional)
        {
            GameObject child = new GameObject(name);
            child.transform.SetParent(transform, false);
            AudioSource source = child.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.loop = true;
            source.outputAudioMixerGroup = _library != null ? _library.Output : null;
            source.spatialBlend = threeDimensional ? 1f : 0f;
            source.dopplerLevel = 0f;
            source.priority = entry != null ? entry.Priority : 200;
            source.volume = 0f;
            return source;
        }

        private SfxLibrary.Entry Entry(string id)
        {
            return _library != null ? _library.Find(id) : null;
        }

        private static AudioClip Pick(SfxLibrary.Entry entry)
        {
            if (entry == null || entry.Clips == null || entry.Clips.Length == 0) return null;
            int count = entry.Clips.Length;
            int index = Random.Range(0, count);
            if (count > 1 && index == entry.LastClip)
                index = (index + 1 + Random.Range(0, count - 1)) % count;
            for (int i = 0; i < count; i++)
            {
                int at = (index + i) % count;
                if (entry.Clips[at] == null) continue;
                entry.LastClip = at;
                return entry.Clips[at];
            }
            return null;
        }

        private static void StartLoop(AudioSource source, SfxLibrary.Entry entry)
        {
            AudioClip clip = Pick(entry);
            if (clip == null) return;
            source.clip = clip;
            source.Play();
        }

        private void SampleZones()
        {
            System.Array.Clear(_waterSelected, 0, _waterSelected.Length);
            Camera camera = Camera.main;
            AudioListener activeListener = camera != null ? camera.GetComponent<AudioListener>() : null;
            _listenerActive = activeListener != null && activeListener.enabled;
            if (!_listenerActive)
            {
                _seaTarget = 0f;
                _officeTarget = 0f;
                return;
            }
            _listener = activeListener.transform;

            Vector3 position = _listener.position;
            SelectWater(position, false, 4, 60f);
            SelectWater(position, true, 2, 40f);
            for (int i = 0; i < _waterSources.Length; i++)
                if (_water.Emitters[i].SoundId == SfxIds.AmbWaterfall &&
                    (_water.Emitters[i].Position - position).sqrMagnitude < 3600f) _waterSelected[i] = true;
            Vector2 point = new Vector2(position.x, position.z);
            if (_districtBeds != null)
            {
                OnlyVolunteers.Map.Look.V3.DistrictBlend19.Weights(_data.BlendBounds, point, _data.DistrictBlendMetres, _spatialWeights);
                _seaTarget = SmoothProximity(NearestCoastDistance(point), 15f, 80f);
                _officeTarget = SmoothProximity(NearestOfficeDistance(point), 12f, 65f);
                return;
            }
            int hit = FindDistrict(point);
            if (_activeDistrict == int.MinValue)
            {
                BeginTransition(hit);
                _candidateDistrict = hit;
            }
            else if (hit == _activeDistrict)
            {
                _candidateDistrict = hit;
            }
            else if (hit != _candidateDistrict)
            {
                _candidateDistrict = hit;
                _candidateSince = Time.unscaledTime;
            }
            else if (Time.unscaledTime - _candidateSince >= DistrictHold && !_fading)
            {
                BeginTransition(hit);
            }

            _seaTarget = SmoothProximity(NearestCoastDistance(point), 15f, 80f);
            _officeTarget = SmoothProximity(NearestOfficeDistance(point), 12f, 65f);
        }

        private void BeginTransition(int districtIndex)
        {
            _activeDistrict = districtIndex;
            AmbienceData.Mapping mapping = null;
            if (_data.Districts != null && districtIndex >= 0 && districtIndex < _data.Districts.Length)
            {
                AmbienceData.District district = _data.Districts[districtIndex];
                if (district != null) mapping = _data.MappingFor(district.Id);
            }
            SfxLibrary.Entry entry = mapping != null ? Entry(mapping.AmbienceId) : null;
            AudioClip clip = Pick(entry);

            _fadeFromA = _weightA;
            _fadeFromB = _weightB;
            _fadeToA = 0f;
            _fadeToB = 0f;
            if (clip != null && mapping != null)
            {
                bool useA = _weightA <= _weightB;
                AudioSource incoming = useA ? _bedA : _bedB;
                incoming.Stop();
                incoming.clip = clip;
                incoming.priority = entry.Priority;
                incoming.volume = 0f;
                incoming.Play();
                if (useA)
                {
                    _weightA = 0f;
                    _fadeFromA = 0f;
                    _fadeToA = Mathf.Clamp01(mapping.Volume);
                }
                else
                {
                    _weightB = 0f;
                    _fadeFromB = 0f;
                    _fadeToB = Mathf.Clamp01(mapping.Volume);
                }
            }
            _fadeTime = 0f;
            _fading = true;
        }

        private void AdvanceFade(float delta)
        {
            if (!_fading) return;
            _fadeTime = Mathf.Min(_fadeTime + delta, FadeSeconds);
            float angle = (_fadeTime / FadeSeconds) * HalfPi;
            float outgoing = Mathf.Cos(angle);
            float incoming = Mathf.Sin(angle);
            _weightA = _fadeFromA * outgoing + _fadeToA * incoming;
            _weightB = _fadeFromB * outgoing + _fadeToB * incoming;
            if (_fadeTime < FadeSeconds) return;
            _fading = false;
            if (_weightA <= 0f) _bedA.Stop();
            if (_weightB <= 0f) _bedB.Stop();
        }

        private void ApplyVolumes()
        {
            float master = Muted || !_listenerActive ? 0f : Mathf.Clamp01(masterVolume);
            _bedA.volume = master * _weightA;
            _bedB.volume = master * _weightB;
            _sea.volume = master * 0.6f * _seaLevel;
            _office.volume = master * 0.35f * _officeLevel;
            if (_districtBeds != null)
                for (int i = 0; i < _districtBeds.Length; i++)
                {
                    if (_districtBeds[i] == null) continue;
                    var mapping = _data.MappingFor(_data.Districts[i].Id);
                    _districtBeds[i].volume = master * _spatialLevels[i] * (mapping != null ? mapping.Volume : 0);
                }
            for (int i = 0; i < _spots.Length; i++)
                if (_spots[i] != null) _spots[i].volume = master * _data.Spots[i].Volume;
            for (int i = 0; i < _fountains.Length; i++)
                _fountains[i].volume = master * 0.4f;
            for (int i = 0; i < _waterSources.Length; i++)
            {
                AudioSource source = _waterSources[i];
                bool active = _waterSelected[i] && master > 0f && source.clip != null;
                source.volume = active ? master * _waterGains[i] : 0f;
                if (active && !source.isPlaying) source.Play();
                else if (!active && source.isPlaying) source.Stop();
            }
        }

        private void SelectWater(Vector3 listener, bool lake, int limit, float radius)
        {
            // Fixed bounded selections; all candidate sources were allocated during Initialize.
            for (int slot = 0; slot < limit; slot++)
            {
                int nearest = -1;
                float best = radius * radius;
                for (int i = 0; i < _waterSources.Length; i++)
                {
                    string id = _water.Emitters[i].SoundId;
                    bool candidate = lake ? id == SfxIds.AmbLakeShore : id == SfxIds.AmbRiver || id == SfxIds.AmbStream;
                    if (!candidate || _waterSelected[i] || _waterSources[i].clip == null) continue;
                    float distance = (_water.Emitters[i].Position - listener).sqrMagnitude;
                    if (distance >= best) continue;
                    best = distance; nearest = i;
                }
                if (nearest < 0) break;
                _waterSelected[nearest] = true;
            }
        }

        private int FindDistrict(Vector2 point)
        {
            AmbienceData.District[] districts = _data.Districts;
            if (districts == null) return -1;
            if (_lastHit >= 0 && _lastHit < districts.Length && districts[_lastHit] != null &&
                Contains(districts[_lastHit].Polygon, point)) return _lastHit;
            for (int i = 0; i < districts.Length; i++)
            {
                if (i == _lastHit || districts[i] == null || !Contains(districts[i].Polygon, point)) continue;
                _lastHit = i;
                return i;
            }
            _lastHit = -1;
            return -1;
        }

        private static bool Contains(Vector2[] polygon, Vector2 point)
        {
            if (polygon == null || polygon.Length < 3) return false;
            bool inside = false;
            int previous = polygon.Length - 1;
            for (int i = 0; i < polygon.Length; previous = i++)
            {
                Vector2 a = polygon[previous];
                Vector2 b = polygon[i];
                Vector2 edge = b - a;
                Vector2 offset = point - a;
                float cross = edge.x * offset.y - edge.y * offset.x;
                if (Mathf.Abs(cross) < 0.001f && Vector2.Dot(offset, point - b) <= 0f) return true;
                if ((a.y > point.y) == (b.y > point.y)) continue;
                float intersectionX = a.x + edge.x * (point.y - a.y) / edge.y;
                if (point.x < intersectionX) inside = !inside;
            }
            return inside;
        }

        private float NearestCoastDistance(Vector2 point)
        {
            if (_data.Coastlines == null) return float.PositiveInfinity;
            float bestSquared = float.PositiveInfinity;
            for (int i = 0; i < _data.Coastlines.Length; i++)
            {
                AmbienceData.Coastline coast = _data.Coastlines[i];
                if (coast == null || coast.Points == null) continue;
                for (int j = 1; j < coast.Points.Length; j++)
                    bestSquared = Mathf.Min(bestSquared, DistanceToSegmentSquared(point, coast.Points[j - 1], coast.Points[j]));
            }
            return Mathf.Sqrt(bestSquared);
        }

        private float NearestOfficeDistance(Vector2 point)
        {
            if (_data.Offices == null) return float.PositiveInfinity;
            float bestSquared = float.PositiveInfinity;
            for (int i = 0; i < _data.Offices.Length; i++)
            {
                float dx = point.x - _data.Offices[i].x;
                float dz = point.y - _data.Offices[i].z;
                bestSquared = Mathf.Min(bestSquared, dx * dx + dz * dz);
            }
            return Mathf.Sqrt(bestSquared);
        }

        private static float DistanceToSegmentSquared(Vector2 point, Vector2 a, Vector2 b)
        {
            Vector2 line = b - a;
            float lengthSquared = line.sqrMagnitude;
            float t = lengthSquared > 0f ? Mathf.Clamp01(Vector2.Dot(point - a, line) / lengthSquared) : 0f;
            return (point - (a + line * t)).sqrMagnitude;
        }

        private static float SmoothProximity(float distance, float near, float far)
        {
            float t = Mathf.Clamp01((far - distance) / (far - near));
            return t * t * (3f - 2f * t);
        }
    }
}
