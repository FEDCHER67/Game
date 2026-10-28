using OnlyVolunteers.Audio;
using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map
{
    // Vadim 28.10: with the eyes under the sea or a lake you are in blue water, as in every game: dense blue-green fog
    // (a few metres of sight) and a blue tint over the view. The water level comes from WaterQuery (the same data the
    // water sounds use). The bog is left to SwampSink (head under = drowned). Subscribed in Start, so it runs after the
    // sky (SkyRenderer22 sets the district fog at every camera begin) and wins for the game cameras.
    public sealed class UnderwaterView : MonoBehaviour
    {
        public Color SeaColour = new Color(.05f, .30f, .40f, 1f);
        public Color LakeColour = new Color(.09f, .27f, .27f, 1f);
        [Tooltip("Metres of sight under water (linear fog end).")]
        public float SeaSight = 14f, LakeSight = 8f;
        [Range(0f, 1f)] public float TintAlpha = .38f;

        private bool _under, _saved, _fog; private FogMode _mode; private Color _col, _tint; private float _start, _end;
        private Texture2D _px;

        private void Start()
        {
            RenderPipelineManager.beginCameraRendering += Begin;
            RenderPipelineManager.endCameraRendering += End;
        }

        private void OnDestroy()
        {
            RenderPipelineManager.beginCameraRendering -= Begin;
            RenderPipelineManager.endCameraRendering -= End;
        }

        private void Begin(ScriptableRenderContext ctx, Camera cam)
        {
            if (cam.cameraType != CameraType.Game || cam.targetTexture) return;
            var p = cam.transform.position;
            _under = WaterQuery.SurfaceAt(p, out float y, out WaterKind kind) && kind != WaterKind.Bog && kind != WaterKind.Puddle && p.y < y - .05f;
            if (!_under) return;
            bool sea = kind == WaterKind.Sea;
            _saved = true; _fog = RenderSettings.fog; _mode = RenderSettings.fogMode; _col = RenderSettings.fogColor; _start = RenderSettings.fogStartDistance; _end = RenderSettings.fogEndDistance;
            _tint = sea ? SeaColour : LakeColour;
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Linear; RenderSettings.fogColor = _tint;
            RenderSettings.fogStartDistance = .3f; RenderSettings.fogEndDistance = sea ? SeaSight : LakeSight;
        }

        private void End(ScriptableRenderContext ctx, Camera cam)
        {
            if (!_saved) return;
            _saved = false;
            RenderSettings.fog = _fog; RenderSettings.fogMode = _mode; RenderSettings.fogColor = _col; RenderSettings.fogStartDistance = _start; RenderSettings.fogEndDistance = _end;
        }

        private void OnGUI()
        {
            if (!_under) return;
            if (!_px) { _px = new Texture2D(1, 1); _px.SetPixel(0, 0, Color.white); _px.Apply(); }
            var old = GUI.color; GUI.color = new Color(_tint.r, _tint.g, _tint.b, TintAlpha);
            GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), _px); GUI.color = old;
        }
    }
}
