using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Map
{
    // Vadim 28.10: the forest swamp pulls a walker down. About 10 s in the mud = drowned, then respawn at the wagon (B01).
    // Stepping out lets the player climb back up (the timer runs down twice as fast). The view sinks only while rendering
    // (camera moved in beginCameraRendering, put back after): the KCC and its camera are untouched.
    public sealed class SwampSink : MonoBehaviour
    {
        [Tooltip("Swamp outline, world x/z (from the forest design).")]
        public Vector2[] Outline = new Vector2[0];
        [Tooltip("Feet below this height inside the outline = in the mud (the pools are at 4.5 m).")]
        public float MudTopY = 4.75f;
        public float SinkSeconds = 10f;
        public float SinkDepth = 1.75f;
        [Tooltip("Part of the F1-F8 spot name to respawn at.")]
        public string RespawnSpot = "Вагон";

        private const float DeadHold = 2.5f;
        private GreyboxVanSeat _seat;
        private float _t, _dead = -1f;
        private Camera _moved;
        private Vector3 _camPos;
        private Texture2D _px;

        private float Progress => Mathf.Clamp01(_t / Mathf.Max(0.1f, SinkSeconds));

        private void OnEnable()
        {
            RenderPipelineManager.beginCameraRendering += Begin;
            RenderPipelineManager.endCameraRendering += End;
        }

        private void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering -= Begin;
            RenderPipelineManager.endCameraRendering -= End;
        }

        private void Update()
        {
            if (!_seat) _seat = FindAnyObjectByType<GreyboxVanSeat>();
            var pawn = _seat ? _seat.Pawn : null;
            if (_dead >= 0f)
            {
                _dead += Time.deltaTime;
                if (_dead > DeadHold) Respawn(pawn);
                return;
            }
            if (OnlyVolunteers.UI.OvMenuGate.Blocking) return;
            bool inMud = pawn && !_seat.Driving && pawn.Controlled && InMud(pawn.Position);
            _t = inMud ? _t + Time.deltaTime : Mathf.Max(0f, _t - 2f * Time.deltaTime);
            if (_t >= SinkSeconds) _dead = 0f;
        }

        private bool InMud(Vector3 p)
        {
            if (p.y > MudTopY || Outline.Length < 3) return false;
            bool inside = false;
            for (int i = 0, j = Outline.Length - 1; i < Outline.Length; j = i++)
            {
                Vector2 a = Outline[i], b = Outline[j];
                if ((a.y > p.z) != (b.y > p.z) && p.x < (b.x - a.x) * (p.z - a.y) / (b.y - a.y) + a.x) inside = !inside;
            }
            return inside;
        }

        private void Respawn(GreyboxPawn pawn)
        {
            _t = 0f; _dead = -1f;
            var trip = FindAnyObjectByType<GreyboxTripMeter>();
            if (!pawn || !trip) return;
            for (int i = 0; i < trip.Spots.Length; i++)
            {
                if (trip.Spots[i].Name == null || !trip.Spots[i].Name.Contains(RespawnSpot)) continue;
                var spot = trip.Spots[i];
                if (!trip.TryGetComponent(out GreyboxTripFootSpots feet) || !feet.TryGet(i, out Vector3 at))
                {
                    at = spot.Position + Quaternion.Euler(0f, spot.Yaw, 0f) * Vector3.right * 4f;
                    if (Physics.Raycast(at + Vector3.up * 30f, Vector3.down, out var hit, 60f, ~0, QueryTriggerInteraction.Ignore)) at = hit.point;
                    at += Vector3.up * 0.1f;
                }
                pawn.Teleport(at, spot.Yaw);
                return;
            }
        }

        private void Begin(ScriptableRenderContext ctx, Camera cam)
        {
            var pawn = _seat ? _seat.Pawn : null;
            float depth = _dead >= 0f ? SinkDepth : SinkDepth * Progress;
            if (depth <= 0.001f || !pawn || cam != pawn.ViewCamera) return;
            _moved = cam; _camPos = cam.transform.position;
            cam.transform.position = _camPos - Vector3.up * depth;
        }

        private void End(ScriptableRenderContext ctx, Camera cam)
        {
            if (cam != _moved || !_moved) return;
            cam.transform.position = _camPos; _moved = null;
        }

        private void OnGUI()
        {
            float p = _dead >= 0f ? 1f : Progress;
            if (p <= 0.001f) return;
            if (!_px) { _px = new Texture2D(1, 1); _px.SetPixel(0, 0, Color.white); _px.Apply(); }
            // the mud rises from the bottom of the view; at the end it closes over the eyes
            float h = Screen.height * Mathf.Clamp01(p * 1.1f - 0.1f);
            var old = GUI.color;
            GUI.color = new Color(0.16f, 0.13f, 0.07f, 0.93f);
            GUI.DrawTexture(new Rect(0, Screen.height - h, Screen.width, h), _px);
            GUI.color = new Color(0f, 0f, 0f, Mathf.Clamp01((p - 0.6f) * 2f) * (_dead >= 0f ? 1f : 0.7f));
            GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), _px);
            GUI.color = old;
            var style = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter, fontSize = Mathf.RoundToInt(Screen.height / 28f), fontStyle = FontStyle.Bold };
            style.normal.textColor = Color.white;
            string msg = _dead >= 0f ? "Тебя затянуло в болото" : "Болото затягивает! Выбирайся";
            GUI.Label(new Rect(0, Screen.height * 0.3f, Screen.width, Screen.height * 0.1f), msg, style);
        }
    }
}
