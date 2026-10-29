using System;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Story;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Session
{
    /// <summary>
    /// The opening hook of a NEW world started from the start menu (29.10). It raises the prologue start the existing
    /// rules own (PrologueState.BeginIntro with the ready participants; <see cref="PrologueStarted"/> for the later
    /// cinematic), and until that cinematic exists stands in for it with a PLACEHOLDER: a short title card ("Пролог —
    /// заставка появится позже"), then the player is put by the forest wagon and gets control (FinishIntro; "без заставки"
    /// in the new-world screen = SkipIntro: the same tutorial start, no reward, nothing spawned twice). Loading a world,
    /// a legacy world or the map started straight from the editor never runs it. Made by itself after the map scene
    /// loads (no scene edit).
    /// </summary>
    public sealed class W86PrologueHookV01 : MonoBehaviour
    {
        /// <summary>Raised once per new world when its opening starts (staging, participants). The cinematic subscribes later.</summary>
        public static event Action<PrologueStaging, int> PrologueStarted;
        /// <summary>Raised when control is handed to the player at the wagon (skipped = the owner chose no intro).</summary>
        public static event Action<bool> ControlHandedOver;

        /// <summary>Where the placeholder puts the player: beside the forest wagon (Vadim's forest, Wagon_Base1_v03), facing it.</summary>
        public static readonly Vector3 WagonStandPoint = new Vector3(255.5f, 6.5f, 151.0f);
        public static readonly Vector3 WagonLookAt = new Vector3(247f, 6.2f, 145.5f);
        public const float CardSeconds = 3.2f;

        enum Phase { WaitWorld, Card, Done }
        Phase phase = Phase.WaitWorld;
        float until;
        bool skip;
        GUIStyle big, small;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { PrologueStarted = null; ControlHandedOver = null; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
            SceneManager.sceneLoaded += OnSceneLoaded;
            OnSceneLoaded(SceneManager.GetActiveScene(), LoadSceneMode.Single);
        }

        static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            if (!WorldLaunchV01.Active || !WorldLaunchV01.NewWorld || WorldLaunchV01.PrologueClaimed) return;
            if (scene.path != WorldLaunchV01.MapScenePath) return;
            WorldLaunchV01.PrologueClaimed = true;
            new GameObject("[Session] Prologue hook (placeholder)").AddComponent<W86PrologueHookV01>();
        }

        void Update()
        {
            switch (phase)
            {
                case Phase.WaitWorld:
                {
                    var capture = CaptureDirector.Instance;
                    if (capture == null || !capture.Ready || !capture.Loaded || capture.Pawn == null) return;
                    PrologueState p = WorldSessionV01.Prologue;
                    if (p == null || p.Stage != PrologueStage.NotStarted) { Debug.Log("[OV Prologue] nothing to start (stage " + (p != null ? p.Stage.ToString() : "-") + ")"); phase = Phase.Done; Destroy(gameObject); return; }
                    bool solo = WorldSessionV01.SoloWorld;
                    int participants = Mathf.Max(1, WorldLaunchV01.Participants);
                    if (!p.BeginIntro(solo, participants)) { phase = Phase.Done; Destroy(gameObject); return; }
                    skip = WorldLaunchV01.SkipIntro;
                    Debug.Log($"[OV Prologue] new world: intro started ({p.Staging}, {participants} participant(s)){(skip ? " — skipped by the owner" : " — PLACEHOLDER card, the cinematic comes later")}");
                    try { PrologueStarted?.Invoke(p.Staging, participants); } catch (Exception e) { Debug.LogException(e); }
                    PutPlayerAtTheWagon(capture);
                    if (skip) { HandOver(capture); return; }
                    phase = Phase.Card;
                    until = Time.unscaledTime + CardSeconds;
                    return;
                }
                case Phase.Card:
                    if (Time.unscaledTime < until) return;
                    HandOver(CaptureDirector.Instance);
                    return;
            }
        }

        static void PutPlayerAtTheWagon(CaptureDirector capture)
        {
            if (capture == null || capture.Pawn == null) return;
            Vector3 at = WagonStandPoint;
            if (Physics.Raycast(at + Vector3.up * 6f, Vector3.down, out RaycastHit hit, 20f, ~0, QueryTriggerInteraction.Ignore)) at = hit.point + Vector3.up * 0.05f;
            Vector3 d = WagonLookAt - at; d.y = 0f;
            float yaw = d.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(d).eulerAngles.y : 0f;
            capture.Pawn.Teleport(at, yaw);
        }

        void HandOver(CaptureDirector capture)
        {
            PrologueState p = WorldSessionV01.Prologue;
            bool ok = p != null && (skip ? p.SkipIntro() : p.FinishIntro());
            phase = Phase.Done;
            Debug.Log($"[OV Prologue] control handed to the player at the wagon (skipped {skip}, ok {ok}, stage {(p != null ? p.Stage.ToString() : "-")})");
            capture?.Toast(skip ? "Вступление пропущено. Ты у вагона в лесу." : "Ты у вагона в лесу. Осмотрись: объявление о покупке крови на столбе.", CaptureHud.Neutral, 6f);
            if (capture != null && capture.Loaded) capture.Save(false);
            try { ControlHandedOver?.Invoke(skip); } catch (Exception e) { Debug.LogException(e); }
            Destroy(gameObject, 0.6f);
        }

        void OnGUI()
        {
            if (phase != Phase.Card) return;
            float a = Mathf.Clamp01((until - Time.unscaledTime) / 0.5f) * Mathf.Clamp01((Time.unscaledTime - (until - CardSeconds)) / 0.4f);
            GUI.color = new Color(0f, 0f, 0f, 0.92f * Mathf.Max(a, 0.6f));
            GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), Texture2D.whiteTexture);
            GUI.color = Color.white;
            big ??= new GUIStyle(GUI.skin.label) { fontSize = 46, alignment = TextAnchor.MiddleCenter, fontStyle = FontStyle.BoldAndItalic };
            small ??= new GUIStyle(GUI.skin.label) { fontSize = 20, alignment = TextAnchor.MiddleCenter, wordWrap = true };
            big.normal.textColor = new Color(0.91f, 0.83f, 0.6f);
            small.normal.textColor = new Color(0.75f, 0.74f, 0.6f);
            GUI.Label(new Rect(0, Screen.height * 0.38f, Screen.width, 70), WorldLaunchV01.WorldName.Length > 0 ? WorldLaunchV01.WorldName : "Пролог", big);
            GUI.Label(new Rect(Screen.width * 0.2f, Screen.height * 0.38f + 80, Screen.width * 0.6f, 60),
                "Пролог: здесь будет вступительная сцена у вагонов (делается отдельно). Сейчас — сразу к игре.", small);
        }
    }
}
