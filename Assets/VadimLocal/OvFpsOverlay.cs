using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.VadimLocal
{
    /// <summary>Always-on FPS counter in the top-right corner (Vadim's local builds).</summary>
    public class OvFpsOverlay : MonoBehaviour
    {
        float _acc, _fps;
        int _frames;
        GUIStyle _style;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Spawn()
        {
            var go = new GameObject("[FPS]");
            DontDestroyOnLoad(go);
            go.AddComponent<OvFpsOverlay>();
        }

        void Update()
        {
            var cam = Camera.main;                                         // camera dithering: no colour rings in the sky
            _aim = Aim(cam);
            if (cam) { var d = cam.GetUniversalAdditionalCameraData(); if (d && !d.dithering) d.dithering = true; }
            _acc += Time.unscaledDeltaTime;
            _frames++;
            if (_acc >= 0.5f) { _fps = _frames / _acc; _acc = 0; _frames = 0; }
        }

        static Texture2D _dot, _ring;
        static int _aim;                  // 0 nothing, 1 NPC, 2 friend (another player)

        /// <summary>What the crosshair points at (up to 60 m): an NPC (any Npc/Patient/Crowd component in its parents) or a friend
        /// (a player body that is not ours, i.e. not within 4 m of the camera).</summary>
        static int Aim(Camera cam)
        {
            if (!cam) return 0;
            var ray = new Ray(cam.transform.position, cam.transform.forward);
            var hits = Physics.RaycastAll(ray, 60f, ~0, QueryTriggerInteraction.Collide);
            System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
            float blockAt = 60f;
            foreach (var h in hits)
            {
                bool friend = false, npc = false;
                foreach (var mb in h.collider.GetComponentsInParent<MonoBehaviour>())
                {
                    if (!mb) continue;
                    string n = mb.GetType().Name;
                    if (n.Contains("Npc") || n.Contains("Patient") || n.Contains("Ragdoll")) npc = true;
                    if (n.Contains("Player") || n.Contains("KinematicCharacter") || n.Contains("Pawn")) friend = true;
                }
                if (friend && (h.collider.transform.position - cam.transform.position).sqrMagnitude < 16f) continue;   // our own body
                if (npc) return 1;
                if (friend) return 2;
                if (!h.collider.isTrigger) { blockAt = h.distance; break; }  // something solid blocks the view
            }
            // crowd NPCs may have no colliders: look for an NPC body close to the aim line in front of the wall
            if (Time.unscaledTime > _npcScan) { _npcScan = Time.unscaledTime + 2f; _npcs.Clear();
                foreach (var mb in Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Exclude))
                    if (mb && (mb.GetType().Name.Contains("Npc") || mb.GetType().Name.Contains("CrowdAgent"))) _npcs.Add(mb.transform); }
            foreach (var n in _npcs)
            {
                if (!n) continue;
                var c = n.position + Vector3.up * 1.0f;
                float along = Vector3.Dot(c - ray.origin, ray.direction);
                if (along < 1f || along > Mathf.Min(blockAt + 0.5f, 60f)) continue;
                if ((ray.origin + ray.direction * along - c).sqrMagnitude < 0.45f * 0.45f) return 1;
            }
            return 0;
        }
        static float _npcScan; static readonly System.Collections.Generic.List<Transform> _npcs = new();

        static Texture2D Disc(int size, float inner, float outer, Color fill, Color edge)
        {
            var t = new Texture2D(size, size, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear };
            float c = (size - 1) / 2f;
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float d = Mathf.Sqrt((x - c) * (x - c) + (y - c) * (y - c));
                    float a = Mathf.Clamp01(outer + 0.5f - d) * Mathf.Clamp01(d - inner + 0.5f);
                    float e = Mathf.Clamp01(outer + 1.5f - d) * Mathf.Clamp01(d - inner + 1.5f);
                    var col = Color.Lerp(edge, fill, a);
                    col.a = Mathf.Max(a * fill.a, e * edge.a);
                    t.SetPixel(x, y, col);
                }
            t.Apply();
            return t;
        }

        /// <summary>Crosshair: small plus with a gap and a centre dot, neutral off-white with a dark outline; first person only.</summary>
        static void Crosshair()
        {
            if (Cursor.lockState != CursorLockMode.Locked) return;
            float cx = Mathf.Round(Screen.width / 2f), cy = Mathf.Round(Screen.height / 2f);
            const float len = 5f, th = 2f, gap = 3f;
            var tex = Texture2D.whiteTexture;
            Rect[] bars =
            {
                new Rect(cx - gap - len, cy - th / 2, len, th), new Rect(cx + gap, cy - th / 2, len, th),
                new Rect(cx - th / 2, cy - gap - len, th, len), new Rect(cx - th / 2, cy + gap, th, len),
            };
            var old = GUI.color;
            GUI.color = new Color(0f, 0f, 0f, 0.55f);
            foreach (var r in bars) GUI.DrawTexture(new Rect(r.x - 1, r.y - 1, r.width + 2, r.height + 2), tex);
            GUI.color = _aim == 1 ? new Color(1f, 0.2f, 0.2f, 0.95f) : _aim == 2 ? new Color(0.45f, 0.95f, 0.55f, 0.95f) : new Color(0.92f, 0.92f, 0.88f, 0.95f);
            foreach (var r in bars) GUI.DrawTexture(r, tex);
            GUI.color = old;
        }

        void OnGUI()
        {
            Crosshair();
            if (_style == null)
                _style = new GUIStyle(GUI.skin.label) { fontSize = 28, fontStyle = FontStyle.Bold, alignment = TextAnchor.UpperRight };
            var r = new Rect(Screen.width - 220, 8, 210, 40);
            _style.normal.textColor = Color.black;
            GUI.Label(new Rect(r.x + 2, r.y + 2, r.width, r.height), Mathf.RoundToInt(_fps) + " FPS", _style);
            _style.normal.textColor = _fps >= 60 ? Color.green : _fps >= 30 ? Color.yellow : Color.red;
            GUI.Label(r, Mathf.RoundToInt(_fps) + " FPS", _style);
        }
    }
}
