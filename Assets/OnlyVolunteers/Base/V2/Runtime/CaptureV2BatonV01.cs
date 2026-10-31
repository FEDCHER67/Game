using OnlyVolunteers.Audio;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Capture.V2;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Map;
using OnlyVolunteers.Player.Hands;
using UnityEngine;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>
    /// The rubber baton (V2 shop item, Fedya 31.10): an alternative LMB hit for Vadim's Capture V2 hands. It sits on the
    /// same player as CaptureV2Hands (BaseV2DirectorV01 adds it) and takes LMB through CaptureV2Hands.AltStrike only while
    /// it is drawn (X, once the team owns it). Its own numbers (BatonTuningV2): reach 2.8 m, an overhead swing that lands
    /// 0.16 s after the press, one swing per 0.9 s, no charge, and he is out cold 4 s every time (CaptureV2Npc.Bonk: he
    /// drops where he stands, no spin and no handprint; the slap's 5/3/2/1 ladder is untouched). Everything else stays
    /// the hands': holding someone, LMB slaps him as before; a lying body or a getting-up one still low is grabbed; RMB
    /// lets go, E throws. Nonlethal: a cartoon bonk, stars, no blood.
    /// </summary>
    [DefaultExecutionOrder(90)]
    public sealed class CaptureV2BatonV01 : MonoBehaviour
    {
        [System.NonSerialized] public BaseV2DirectorV01 Director;
        public BatonTuningV2 Tuning = new BatonTuningV2();

        private static readonly RaycastHit[] Sweep = new RaycastHit[16];
        private CaptureV2Hands hands;
        private GameObject held;
        private float lastSwing = -10f, swingAt = -1f;
        private CaptureV2Npc target;
        private Vector3 targetPoint;
        private bool landedSound;

        public bool Drawn { get; private set; }
        public bool Swinging => swingAt > 0f;
        /// <summary>Tests: the last swing landed on someone.</summary>
        public bool LastLanded { get; private set; }
        public int Swings { get; private set; }

        private void Awake() => hands = GetComponent<CaptureV2Hands>();

        private void OnEnable() => CaptureV2Hands.AltStrike = Strike;

        private void OnDisable()
        {
            if (CaptureV2Hands.AltStrike == (System.Func<CaptureV2Hands, bool>)Strike) CaptureV2Hands.AltStrike = null;
            Draw(false);
        }

        private void Update()
        {
            if (hands == null) return;
            bool owned = BaseV2DirectorV01.TeamOwns(GearCatalogV2.Baton);
            if (Drawn && !owned) Draw(false);
            if (!OnlyVolunteers.UI.OvMenuGate.Blocking && Cursor.lockState == CursorLockMode.Locked)
            {
                UnityEngine.InputSystem.Keyboard k = UnityEngine.InputSystem.Keyboard.current;
                if (k != null && k.xKey.wasPressedThisFrame) Toggle(owned);
            }
            TickSwing();
            Pose();
        }

        /// <summary>X: draw / put away (only when the team owns it).</summary>
        public void Toggle(bool owned)
        {
            if (!owned)
            {
                CaptureDirector.Instance?.Toast("Дубинки нет — её продают в GEAR (оружейная)", CaptureHud.Warn, 3f);
                return;
            }
            Draw(!Drawn);
        }

        public void Draw(bool on)
        {
            if (on == Drawn && (on == (held != null))) return;
            Drawn = on;
            if (on) EnsureHeld();
            if (held != null) held.SetActive(on);
            swingAt = -1f;
            Debug.Log("[BASEV2] baton " + (on ? "drawn" : "put away"));
        }

        private void EnsureHeld()
        {
            if (held != null || hands.View == null) return;
            held = new GameObject("Held baton (V2 shop)");
            held.transform.SetParent(hands.View.transform, false);
            held.transform.localPosition = new Vector3(0.27f, -0.31f, 0.5f);
            var mf = held.AddComponent<MeshFilter>();
            mf.sharedMesh = Director != null ? Director.BatonMesh : null;
            var mr = held.AddComponent<MeshRenderer>();
            mr.sharedMaterial = Director != null ? Director.BatonMaterial : null;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
            mr.renderingLayerMask = 1u | (1u << 1) | (1u << 2);
            if (mf.sharedMesh == null) Debug.LogWarning("[BASEV2] no baton mesh on the director: the held baton is invisible", this);
        }

        // ---------- LMB (CaptureV2Hands.PressLmb asks first) ----------

        /// <summary>True = the baton took this LMB press; false = the hands do what they always do.</summary>
        private bool Strike(CaptureV2Hands h)
        {
            if (!Drawn || h != hands || h.HeldNpc != null) return false;
            if (Swinging || !BatonRulesV2.Ready(Time.time, lastSwing, Tuning.Cooldown)) return true; // a press during the swing / cooldown
            GreyboxNpc npc = FindTarget(out Vector3 point);
            if (npc != null)
            {
                if (npc.IsDown) return false; // lying: the hands grab him
                if (npc.State == NpcState.GettingUp && CaptureV2Hands.StillLow(npc)) return false; // still low: the hands drop and grab him
                if (npc.State != NpcState.Free && npc.State != NpcState.GettingUp) return false;
                Begin(CaptureV2Rig.Instance != null ? CaptureV2Rig.Instance.Ensure(npc) : null, point);
                return true;
            }
            // nobody standing in reach: a loose prop is still grabbed; otherwise a swing at the air
            if (h.Grabber != null && !h.Grabber.IsHolding && h.Grabber.ScriptGrab()) return true;
            Begin(null, Vector3.zero);
            return true;
        }

        /// <summary>Test hook: the LMB press with the baton drawn (same path as the mouse).</summary>
        public bool ScriptStrike() => Strike(hands);

        private void Begin(CaptureV2Npc t, Vector3 point)
        {
            target = t;
            targetPoint = point;
            swingAt = Time.time;
            lastSwing = Time.time;
            landedSound = false;
            Swings++;
        }

        private GreyboxNpc FindTarget(out Vector3 point)
        {
            point = Vector3.zero;
            Camera view = hands.View;
            if (view == null) return null;
            var ray = new Ray(view.transform.position, view.transform.forward);
            if (Physics.Raycast(ray, out RaycastHit hit, Tuning.Reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore) &&
                hit.collider.GetComponentInParent<GreyboxNpc>() is GreyboxNpc direct)
            {
                point = hit.point;
                return direct;
            }
            int n = Physics.SphereCastNonAlloc(ray, 0.3f, Sweep, Tuning.Reach, OvLayers.ShootMask, QueryTriggerInteraction.Ignore);
            GreyboxNpc best = null;
            float bestD = float.MaxValue;
            for (int i = 0; i < n; i++)
            {
                RaycastHit s = Sweep[i];
                Sweep[i] = default;
                if (s.collider == null || s.distance <= 0f || s.distance >= bestD) continue;
                GreyboxNpc c = s.collider.GetComponentInParent<GreyboxNpc>();
                if (c == null) continue;
                best = c;
                bestD = s.distance;
                point = s.point;
            }
            return best;
        }

        private void TickSwing()
        {
            if (swingAt <= 0f) return;
            float t = Time.time - swingAt;
            if (t < Tuning.Windup) return;
            if (landedSound) { if (t > Tuning.Windup + 0.4f) swingAt = -1f; return; }
            landedSound = true;
            LastLanded = false;
            Vector3 feet = hands.Feet;
            if (target != null && target.isActiveAndEnabled)
            {
                Vector3 to = target.Center - feet;
                to.y = 0f;
                Vector3 head = target.Npc.IsDown ? target.Npc.Center : target.transform.position + Vector3.up * 1.62f;
                if (to.magnitude <= Tuning.LungeReach)
                    LastLanded = CaptureV2Authority.Bonk(target, this, feet, targetPoint == Vector3.zero ? head : targetPoint, BatonRulesV2.KnockOut(Tuning, 0));
                if (LastLanded)
                {
                    CaptureV2Juice.HitStop(0.06f);
                    CaptureV2Juice.Shake(0.35f, 0.08f);
                    CaptureV2Juice.KickFast(0.9f, 0f);
                    CaptureV2Sounds.Play(CaptureV2Sounds.Bonk, head, 1f, 0.95f);
                    Sfx.PlayAt(SfxIds.HitHead, head, 0.9f);
                    PlayerArmsTuningV01 at = PlayerArmsTuningV01.Load();
                    if (at != null) PunchStarsV01.Schedule(head + Vector3.up * 0.15f, 0.7f, 0f, Mathf.Max(4, at.StarCount), at.StarSize * 0.8f, at.StarLife);
                    Debug.Log($"[BASEV2] baton bonk: {target.name} down, out cold {BatonRulesV2.KnockOut(Tuning, 0):0.0} s");
                }
            }
            if (!LastLanded && hands.View != null)
                CaptureV2Sounds.Play(CaptureV2Sounds.Whoosh, hands.View.transform.position + hands.View.transform.forward * 0.6f, 0.45f, 0.8f);
            target = null;
        }

        // the held baton: resting tip forward-up, a quick cock back, the chop forward-down at the contact, back to rest
        private void Pose()
        {
            if (held == null || !held.activeSelf) return;
            float rest = 18f, cock = -42f, chop = 98f, x;
            if (swingAt <= 0f) x = rest;
            else
            {
                float t = Time.time - swingAt, w = Mathf.Max(0.05f, Tuning.Windup);
                if (t < w * 0.4f) x = Mathf.Lerp(rest, cock, t / (w * 0.4f));
                else if (t < w) x = Mathf.Lerp(cock, chop, Mathf.SmoothStep(0f, 1f, (t - w * 0.4f) / (w * 0.6f)));
                else x = Mathf.Lerp(chop, rest, Mathf.Clamp01((t - w) / 0.35f));
            }
            held.transform.localRotation = Quaternion.Euler(x, -12f, -18f);
        }

        private void OnGUI()
        {
            if (!Drawn || OnlyVolunteers.UI.OvMenuGate.Blocking) return;
            var s = new GUIStyle(GUI.skin.label) { fontSize = 16, alignment = TextAnchor.MiddleLeft };
            s.normal.textColor = new Color(1f, 0.9f, 0.7f);
            bool ready = !Swinging && BatonRulesV2.Ready(Time.time, lastSwing, Tuning.Cooldown);
            GUI.Label(new Rect(24f, Screen.height - 140f, 600f, 26f), "Дубинка: ЛКМ — удар" + (ready ? "" : " (замах…)") + " · X — убрать", s);
        }
    }
}
