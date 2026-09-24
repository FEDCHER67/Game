using UnityEngine;

namespace OnlyVolunteers.Player.Physics
{
    [CreateAssetMenu(menuName = "VOLUNTEERS ONLY/Grab Physics Profile")]
    public sealed class GrabPhysicsProfile : ScriptableObject
    {
        [SerializeField, Min(0.1f)] private float acquireDistance = 2.8f;
        [SerializeField, Min(0.1f)] private float holdDistance = 2.25f;
        [SerializeField, Min(1f)] private float springStrength = 220f;
        [SerializeField, Range(0.1f, 2f)] private float dampingRatio = 1f;
        [SerializeField, Min(1f)] private float maxForce = 900f;
        [SerializeField, Min(1f)] private float maxLinearSpeed = 12f;
        [SerializeField, Min(1f)] private float maxAngularSpeed = 25f;
        [SerializeField, Min(0.5f)] private float breakDistance = 4.5f;
        [SerializeField] private LayerMask acquisitionLayers = ~0;

        public float AcquireDistance => acquireDistance;
        public float HoldDistance => holdDistance;
        public float SpringStrength => springStrength;
        public float DampingRatio => dampingRatio;
        public float MaxForce => maxForce;
        public float MaxLinearSpeed => maxLinearSpeed;
        public float MaxAngularSpeed => maxAngularSpeed;
        public float BreakDistance => breakDistance;
        public LayerMask AcquisitionLayers => acquisitionLayers;
    }
}
