using UnityEngine;

namespace OnlyVolunteers.Operation
{
    /// <summary>A cartoon droplet: hops, falls and shrinks away. No decals, no puddles.</summary>
    public sealed class OrganDroplet : MonoBehaviour
    {
        private Vector3 velocity;
        private Vector3 baseScale;
        private float time;

        public void Launch(Vector3 initialVelocity)
        {
            velocity = initialVelocity;
            baseScale = transform.localScale;
        }

        private void Update()
        {
            time += Time.deltaTime;
            velocity += Physics.gravity * Time.deltaTime;
            transform.position += velocity * Time.deltaTime;
            transform.localScale = baseScale * Mathf.Clamp01(1f - time / 0.9f);
            if (time >= 0.9f) Destroy(gameObject);
        }
    }
}
