using System.Collections.Generic;
using System.Reflection;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Player;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>The ONE writer of the local player's speed limits (KccFirstPersonInput.ExternalSpeedScale; Claude, Fedya's
    /// round-2 playtest and the lead's round-2 review: two writers could clobber each other). Requesters:
    /// - absolute caps in m/s (Request): pushing the gurney, holding it with LMB, carrying a body bag;
    /// - scale factors 0..1 (RequestScale): the map PhysicsGrabber's heavy-drag slow-down.
    /// Every request lasts Expiry seconds unless renewed (frame-rate and physics-rate requesters alike), or ends at once
    /// with Clear; the strictest one wins; with none left the scale goes back to 1. Caps are absolute speeds (fractions
    /// of the walk speed), so sprinting while pushing is no faster.</summary>
    [DefaultExecutionOrder(20000)]
    public sealed class OperationPlayerSpeed : MonoBehaviour
    {
        /// <summary>KccFirstPersonInput's walk speed (a private constant there).</summary>
        public const float WalkSpeed = 4.7025f;
        public const float Expiry = 0.12f;

        private struct Limit { public float Speed, Scale, Until; }
        private static readonly Dictionary<KccFirstPersonInput, Dictionary<object, Limit>> Limits = new();
        private static readonly HashSet<KccFirstPersonInput> Owned = new();
        private static OperationPlayerSpeed runner;
        private static readonly FieldInfo MoveInputField = typeof(ExampleCharacterController).GetField("_moveInputVector", BindingFlags.Instance | BindingFlags.NonPublic);

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() { Limits.Clear(); Owned.Clear(); runner = null; local = null; }

        /// <summary>For the next Expiry seconds the player's grounded target speed is at most 'maxSpeed' m/s.</summary>
        public static void Request(KccFirstPersonInput input, object key, float maxSpeed) => Set(input, key, Mathf.Max(0f, maxSpeed), 1f);

        /// <summary>For the next Expiry seconds the player's speed is multiplied by at most 'scale' (0..1).</summary>
        public static void RequestScale(KccFirstPersonInput input, object key, float scale) => Set(input, key, float.PositiveInfinity, Mathf.Clamp01(scale));

        /// <summary>Ends a request now (a release).</summary>
        public static void Clear(KccFirstPersonInput input, object key)
        {
            if (input != null && key != null && Limits.TryGetValue(input, out var map)) map.Remove(key);
        }

        private static void Set(KccFirstPersonInput input, object key, float speed, float scale)
        {
            if (input == null || key == null) return;
            if (runner == null)
            {
                var go = new GameObject("[Operation] Player speed limits");
                runner = go.AddComponent<OperationPlayerSpeed>();
            }
            if (!Limits.TryGetValue(input, out var map)) Limits[input] = map = new Dictionary<object, Limit>();
            map[key] = new Limit { Speed = speed, Scale = scale, Until = Time.time + Expiry };
        }

        /// <summary>The lowest speed cap in force for this player (float.PositiveInfinity when none).</summary>
        public static float CurrentCap(KccFirstPersonInput input)
        {
            if (input == null || !Limits.TryGetValue(input, out var map)) return float.PositiveInfinity;
            float best = float.PositiveInfinity;
            foreach (var l in map.Values) if (Time.time <= l.Until) best = Mathf.Min(best, l.Speed);
            return best;
        }

        private static float CurrentScale(KccFirstPersonInput input, out bool any)
        {
            any = false;
            if (input == null || !Limits.TryGetValue(input, out var map)) return 1f;
            float best = 1f;
            foreach (var l in map.Values) if (Time.time <= l.Until) { any = true; best = Mathf.Min(best, l.Scale); }
            return best;
        }

        /// <summary>The player's movement intent (camera-relative input on the ground plane, length 0..1), the same vector the
        /// character controller steers by: works for the keyboard and for a scripted driver alike.</summary>
        public static Vector3 MoveIntent(ExampleCharacterController character)
        {
            if (character == null || MoveInputField == null) return Vector3.zero;
            Vector3 v = (Vector3)MoveInputField.GetValue(character); v.y = 0f;
            return Vector3.ClampMagnitude(v, 1f);
        }

        private static KccFirstPersonInput local;
        private static float nextLocalSearch;
        /// <summary>The player this machine controls (an enabled KccFirstPersonInput on an active pawn), or null.</summary>
        public static KccFirstPersonInput Local
        {
            get
            {
                if (local != null && local.isActiveAndEnabled) return local;
                if (Time.unscaledTime < nextLocalSearch) return null;
                nextLocalSearch = Time.unscaledTime + 0.5f;
                local = null;
                foreach (var input in FindObjectsByType<KccFirstPersonInput>(FindObjectsSortMode.None))
                    if (input != null && input.isActiveAndEnabled && input.Character != null) { local = input; break; }
                return local;
            }
        }

        private readonly List<KccFirstPersonInput> stale = new();
        private void LateUpdate()
        {
            stale.Clear();
            foreach (var pair in Limits)
            {
                var input = pair.Key;
                if (input == null) { stale.Add(input); continue; }
                float scaleLimit = CurrentScale(input, out bool any);
                if (!any)
                {
                    if (Owned.Remove(input)) input.ExternalSpeedScale = 1f;
                    continue;
                }
                float cap = CurrentCap(input);
                // KccFirstPersonInput.Update set MaxStableMoveSpeed = base (walk/sprint/crouch, diagonal) x the current scale,
                // and only this class writes that scale, so the base is recovered exactly.
                float current = input.ExternalSpeedScale;
                float baseSpeed = current > 0.001f && input.Character != null ? input.Character.MaxStableMoveSpeed / current : WalkSpeed;
                if (baseSpeed < 0.01f) baseSpeed = WalkSpeed;
                float capScale = float.IsPositiveInfinity(cap) ? 1f : cap / baseSpeed;
                input.ExternalSpeedScale = Mathf.Clamp(Mathf.Min(scaleLimit, capScale), 0.02f, 1f);
                Owned.Add(input);
            }
            foreach (var input in stale) Limits.Remove(input);
        }

        private void OnDestroy()
        {
            foreach (var input in Owned) if (input != null) input.ExternalSpeedScale = 1f;
            Owned.Clear();
            if (runner == this) runner = null;
        }
    }
}
