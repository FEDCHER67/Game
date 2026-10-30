using UnityEngine;
using UnityEngine.Rendering;

/// <summary>VanOnly (Vadim 30.10, FPS): the G22 painted sky raymarches its clouds for every sky pixel (64 steps). Measured in
/// the VanOnly build at 3840x2160, render scale 0.85, RTX 3060 Ti: the sky alone is 13-16 ms of GPU with half the screen sky
/// and ~30 ms looking up, while the van, floor, shadows and post together are ~2.5 ms. In VanOnly the sky stands still (its
/// SkyRenderer22 waits for a district source this scene does not have), so the sky material is rendered once into six faces
/// at start and the skybox becomes a lookup of those faces (same look, a fraction of a millisecond). If the sky material
/// changes (another sky driver, a clock) the faces are rendered again. The game's map scenes are not touched.</summary>
[DefaultExecutionOrder(1000)]
public sealed class VanOnlySkyCache : MonoBehaviour
{
    [Tooltip("The cached-sky material (shader VadimLocal/VanOnly Sky Cached).")]
    public Material CachedSky;
    [Tooltip("Pixels per face side (6 faces, RGB 11-11-10 float: 1536 = 56 MB).")]
    public int FaceSize = 1536;
    [Tooltip("A little over 90 degrees, so a lookup never reaches a face's edge texels (no seams).")]
    public float FaceFov = 92f;
    [Tooltip("Flips the face lookup vertically: the faces are stored bottom-up (Unity's render-texture convention); measured " +
             "against the raymarched sky in the D3D11 build: flipped matches it (mean difference 0.5 / 255).")]
    public bool FlipV = true;

    private Material _source;
    private RenderTexture _faces;
    private Mesh _cube;
    private readonly Matrix4x4[] _vp = new Matrix4x4[6];
    private int _hash;
    private float _nextCheck;
    private static readonly Vector3[] Dirs = { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back };
    private static readonly Vector3[] Ups = { Vector3.up, Vector3.up, Vector3.forward, Vector3.forward, Vector3.up, Vector3.up };
    private static readonly string[] Floats = { "_Cover", "_Gloom", "_Stars", "_Golden", "_Daylight", "_CloudTime", "_CloudScale", "_Steps" };
    private static readonly string[] Colours = { "_Zenith", "_Horizon", "_CloudTop", "_CloudBase", "_SunColour", "_MoonColour", "_SunDirection", "_MoonDirection" };

    public bool Active => _faces != null && _source != null;

    private void OnEnable() => RenderPipelineManager.beginCameraRendering += BeginCamera;

    private void OnDisable()
    {
        RenderPipelineManager.beginCameraRendering -= BeginCamera;
        if (_source != null && RenderSettings.skybox == CachedSky) RenderSettings.skybox = _source;
        _source = null;
        if (_faces != null) { _faces.Release(); Destroy(_faces); _faces = null; }
    }

    // Registered after SkyRenderer22 (it enables first): whatever it set as the skybox for this camera is baked and replaced.
    private void BeginCamera(ScriptableRenderContext context, Camera camera)
    {
        if (CachedSky == null || camera.cameraType == CameraType.Preview) return;
        Material sky = RenderSettings.skybox;
        if (sky != null && sky != CachedSky) _source = sky;
        if (_source == null) return;
        bool check = Time.unscaledTime >= _nextCheck;
        if (check) _nextCheck = Time.unscaledTime + 0.5f;
        if (_faces == null || (check && Hash(_source) != _hash)) Bake();
        RenderSettings.skybox = CachedSky;
    }

    private static int Hash(Material m)
    {
        int h = m.GetHashCode();
        foreach (string f in Floats) if (m.HasProperty(f)) h = h * 31 + m.GetFloat(f).GetHashCode();
        foreach (string c in Colours) if (m.HasProperty(c)) h = h * 31 + m.GetVector(c).GetHashCode();
        return h;
    }

    private void Bake()
    {
        if (_cube == null)
        {
            var g = GameObject.CreatePrimitive(PrimitiveType.Cube);
            _cube = g.GetComponent<MeshFilter>().sharedMesh;
            Destroy(g);
        }
        if (_faces == null)
        {
            _faces = new RenderTexture(FaceSize, FaceSize, 0, RenderTextureFormat.RGB111110Float)
            {
                dimension = TextureDimension.Tex2DArray, volumeDepth = 6, useMipMap = false,
                wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "VanOnly sky faces",
            };
            _faces.Create();
        }
        Matrix4x4 proj = Matrix4x4.Perspective(FaceFov, 1f, 0.05f, 10f);
        Matrix4x4 gpu = GL.GetGPUProjectionMatrix(proj, true);
        var cmd = new CommandBuffer { name = "VanOnly sky bake" };
        for (int i = 0; i < 6; i++)
        {
            Matrix4x4 view = Matrix4x4.Scale(new Vector3(1f, 1f, -1f)) *
                             Matrix4x4.TRS(Vector3.zero, Quaternion.LookRotation(Dirs[i], Ups[i]), Vector3.one).inverse;
            _vp[i] = proj * view;
            cmd.SetRenderTarget(_faces, 0, CubemapFace.Unknown, i);
            cmd.ClearRenderTarget(false, true, Color.black);
            cmd.SetViewProjectionMatrices(view, gpu);
            cmd.DrawMesh(_cube, Matrix4x4.identity, _source, 0, 0);
        }
        Graphics.ExecuteCommandBuffer(cmd);
        cmd.Release();
        CachedSky.SetTexture("_Faces", _faces);
        CachedSky.SetMatrixArray("_FaceVP", _vp);
        Shader.SetGlobalTexture("_Faces", _faces);
        Shader.SetGlobalMatrixArray("_FaceVP", _vp);
        CachedSky.SetFloat("_FlipV", FlipV ? 1f : 0f);
        _hash = Hash(_source);
        Debug.Log($"[VanOnlySkyCache] sky {_source.name} baked into 6 x {FaceSize} px faces");
    }

    /// <summary>Test hook: the lookup's vertical flip (applied at once, no re-bake).</summary>
    public void SetFlip(bool flip)
    {
        FlipV = flip;
        if (CachedSky != null) CachedSky.SetFloat("_FlipV", flip ? 1f : 0f);
    }
}
