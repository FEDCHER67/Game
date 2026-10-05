using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>
    /// Presentation only: a dropped organ flattens a little on a hard landing and wobbles back, so it reads as soft.
    /// Scales the model child, never the physics body or its collider.
    /// </summary>
    public sealed class SquishOnImpact : MonoBehaviour
    {
        private const float MinImpactSpeed = 0.8f;
        private const float FullImpactSpeed = 5f;
        private const float WobbleFrequency = 14f;
        private const float WobbleDecay = 9f;

        [SerializeField] private Transform model;
        [SerializeField, Range(0f, 0.5f)] private float amount = 0.2f;

        private Vector3 baseScale;
        private float squash;
        private float time;

        public void Setup(Transform target, float maxSquash)
        {
            model = target;
            amount = maxSquash;
            baseScale = target.localScale;
            enabled = false;
        }

        private void OnCollisionEnter(Collision collision)
        {
            if (model == null || amount <= 0f) return;
            float speed = collision.relativeVelocity.magnitude;
            if (speed < MinImpactSpeed) return;
            squash = amount * Mathf.Clamp01(speed / FullImpactSpeed);
            time = 0f;
            enabled = true;
        }

        private void Update()
        {
            time += Time.deltaTime;
            float s = squash * Mathf.Exp(-WobbleDecay * time) * Mathf.Cos(WobbleFrequency * time);
            if (Mathf.Abs(s) < 0.002f && time > 0.1f)
            {
                model.localScale = baseScale;
                enabled = false;
                return;
            }
            // Flattens along the model's up axis and bulges sideways, keeping the volume roughly the same.
            model.localScale = Vector3.Scale(baseScale, new Vector3(1f + s * 0.5f, 1f - s, 1f + s * 0.5f));
        }

        private void OnDisable()
        {
            if (model != null && baseScale != Vector3.zero) model.localScale = baseScale;
        }
    }
}
