using UnityEngine;

namespace OnlyVolunteers.VadimLocal
{
    /// <summary>Vadim 25.10 (local W86): a stationary air-defence gun on Tramduro island. The turret sweeps slowly from side to
    /// side; with a Target (later: the van during the island alarm) it turns to track it instead.</summary>
    public sealed class VadimAaTurret : MonoBehaviour
    {
        public Transform turret;
        public Transform target;
        public float sweepDegrees = 70f;
        public float sweepSpeed = .18f;
        public float trackDegreesPerSecond = 60f;

        private float _phase, _baseYaw;

        private void Start()
        {
            _phase = Random.value * 10f;
            if (turret) _baseYaw = turret.localEulerAngles.y;
        }

        private void Update()
        {
            if (!turret) return;
            if (target)
            {
                var d = target.position - turret.position; d.y = 0f;
                if (d.sqrMagnitude > 1f) turret.rotation = Quaternion.RotateTowards(turret.rotation, Quaternion.LookRotation(d), trackDegreesPerSecond * Time.deltaTime);
            }
            else turret.localRotation = Quaternion.Euler(0f, _baseYaw + Mathf.Sin(Time.time * sweepSpeed + _phase) * sweepDegrees, 0f);
        }
    }
}
