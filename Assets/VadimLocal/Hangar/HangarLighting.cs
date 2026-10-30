using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>HangarLab (Vadim 30.10, base = one big military hangar): the "cozy darkness" inside, sunlight outside.
/// Rendering layers (set by VadimHangarLab): bit 0 everything (the van's own lamps), bit 1 the hall, bit 2 the rooms,
/// bit 3 sunlit. The sun lights bit 3 only, so nothing inside the hangar is ever sunlit (no shadow distance, cascade or
/// light-leak issue); the hall lamps light bit 1, the room lamps bits 1-2. Static hangar parts carry their bits from
/// the generator. Moving things (the van, NPCs, the player, anything spawned) are switched here: inside the hangar box
/// bit 1, outside bit 3 (with 0.6 m of hysteresis, so nothing at the gate line can blink).
/// The ambient and the reflection intensity follow the camera: low inside, the scene's own outside (blended over
/// BlendSeconds when the camera crosses the gate).</summary>
[DefaultExecutionOrder(900)]
public sealed class HangarLighting : MonoBehaviour
{
    [Tooltip("The hangar root (its local space holds the interior box).")] public Transform Hangar;
    public Vector3 InteriorMin = new(-25f, -1f, -17f);
    public Vector3 InteriorMax = new(25f, 12f, 17f);
    [Tooltip("Ambient inside (linear): onto up-facing surfaces (the floor) / onto down-facing ones (the roof and trusses get the lamps' warm bounce off the floor, so they stay readable).")]
    public Color InsideSky = new(0.075f, 0.07f, 0.065f);
    public Color InsideGround = new(0.13f, 0.105f, 0.08f);
    [Range(0f, 1f)] public float InsideReflection = 0.25f;
    public float BlendSeconds = 0.6f;
    public float Hysteresis = 0.6f;
    [Tooltip("Renderers never switched (the outside floor).")] public Renderer[] Fixed = new Renderer[0];

    public const uint HallBit = 1u << 1, RoomBit = 1u << 2, SunBit = 1u << 3;

    private SphericalHarmonicsL2 _outside, _inside;
    private float _outsideReflection, _blend = -1f;
    private readonly List<Renderer> _dynamic = new();
    private readonly HashSet<Renderer> _fixed = new();
    private float _nextScan, _nextMask;

    public bool CameraInside { get; private set; }
    public int DynamicCount => _dynamic.Count;

    private void Start()
    {
        _outside = RenderSettings.ambientProbe;
        _outsideReflection = RenderSettings.reflectionIntensity;
        _inside = new SphericalHarmonicsL2();
        _inside.AddAmbientLight(InsideGround);
        _inside.AddDirectionalLight(Vector3.up, InsideSky - InsideGround, 1f);
        foreach (var r in Fixed) if (r) _fixed.Add(r);
    }

    private bool Inside(Vector3 world, float grow)
    {
        Vector3 p = Hangar ? Hangar.InverseTransformPoint(world) : world;
        return p.x > InteriorMin.x - grow && p.x < InteriorMax.x + grow && p.y > InteriorMin.y - grow && p.y < InteriorMax.y + grow &&
               p.z > InteriorMin.z - grow && p.z < InteriorMax.z + grow;
    }

    private void Scan()
    {
        _dynamic.Clear();
        foreach (var r in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
        {
            if (r == null || _fixed.Contains(r) || r.isPartOfStaticBatch) continue;
            if (Hangar && r.transform.IsChildOf(Hangar)) continue;
            _dynamic.Add(r);
        }
    }

    private void UpdateMasks()
    {
        foreach (var r in _dynamic)
        {
            if (r == null) continue;
            uint m = r.renderingLayerMask;
            Vector3 c = r.bounds.center;
            bool inNow = (m & HallBit) != 0, outNow = (m & SunBit) != 0;
            bool goIn = (!inNow || outNow) && Inside(c, -Hysteresis);
            bool goOut = (!outNow || inNow) && !Inside(c, Hysteresis);
            if (!inNow && !outNow) { if (Inside(c, 0f)) goIn = true; else goOut = true; }
            if (goIn) r.renderingLayerMask = (m | 1u | HallBit) & ~SunBit;
            else if (goOut) r.renderingLayerMask = (m | 1u | SunBit) & ~HallBit;
        }
    }

    private void LateUpdate()
    {
        if (Time.unscaledTime >= _nextScan) { _nextScan = Time.unscaledTime + 2f; Scan(); }
        if (Time.unscaledTime >= _nextMask) { _nextMask = Time.unscaledTime + 0.1f; UpdateMasks(); }

        var cam = Camera.main;
        if (cam != null)
        {
            bool inside = CameraInside ? Inside(cam.transform.position, 0.3f) : Inside(cam.transform.position, -0.3f);
            CameraInside = inside;
        }
        float target = CameraInside ? 1f : 0f;
        _blend = _blend < 0f ? target : Mathf.MoveTowards(_blend, target, Time.unscaledDeltaTime / Mathf.Max(0.01f, BlendSeconds));
        RenderSettings.ambientProbe = _outside * (1f - _blend) + _inside * _blend;
        RenderSettings.reflectionIntensity = Mathf.Lerp(_outsideReflection, InsideReflection, _blend);
    }

    private void OnDisable()
    {
        if (_blend < 0f) return;
        RenderSettings.ambientProbe = _outside;
        RenderSettings.reflectionIntensity = _outsideReflection;
    }
}
