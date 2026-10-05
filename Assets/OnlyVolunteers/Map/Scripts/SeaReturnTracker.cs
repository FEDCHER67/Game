using System.Collections.Generic;
using OnlyVolunteers.Vehicles;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Remembers where its object recently stood on dry ground; when the object gets into a SeaReturnZone it is put back
    // at the last such point a few metres from the water's edge, i.e. where it jumped or drove in from. Dry = outside
    // the zone and not under the sea surface (SeaReturnZone.Dry: on the look map the surf strip of the beach lies below
    // the sea level before the zone starts); heights come from where the object really stood, never a flat y = 0.
    // Works for the van (VanController.ResetUpright), the on-foot pawn (GreyboxPawn.Teleport; the KCC player must move
    // through its motor) and for plain rigidbodies/transforms.
    public sealed class SeaReturnTracker : MonoBehaviour
    {
        [Tooltip("Minimum distance between the return point and the point where the object entered the sea.")]
        public float Backoff = 6f;
        public float SampleInterval = 0.25f;

        private const int HistorySize = 48;
        private readonly List<(Vector3 pos, float yaw)> _history = new();
        // Last dry point ever recorded; Rebase keeps it, so a teleport into the sea still has somewhere to return to.
        private (Vector3 pos, float yaw)? _lastDry;
        private VanController _van;
        private Rigidbody _body;
        private GreyboxPawn _pawn;
        private float _nextSample;

        private void Awake()
        {
            _van = GetComponent<VanController>();
            _body = GetComponent<Rigidbody>();
            _pawn = GetComponentInParent<GreyboxPawn>(true);
            Record();
        }

        private void FixedUpdate()
        {
            Vector3 p = transform.position;
            if (SeaReturnZone.InSea(p))
            {
                ReturnToLand(p);
                return;
            }
            if (Time.time >= _nextSample && Grounded())
            {
                Record();
                _nextSample = Time.time + SampleInterval;
            }
        }

        /// <summary>Forget old dry points after a teleport, so the sea never sends the object back to where it was before.
        /// A teleport into the sea (or the surf) keeps the old history: there is no dry point to start from there.</summary>
        public void Rebase()
        {
            if (!SeaReturnZone.Dry(transform.position)) return;
            _history.Clear();
            Record();
        }

        private void Record()
        {
            // A sea point in the history would be returned to, rebased onto and returned to again (a climb every tick).
            if (!SeaReturnZone.Dry(transform.position)) return;
            if (_history.Count == HistorySize) _history.RemoveAt(0);
            var point = (transform.position, transform.eulerAngles.y);
            _history.Add(point);
            _lastDry = point;
        }

        private bool Grounded()
        {
            if (_van != null)
                return Touching(_van.Front.Left) || Touching(_van.Front.Right) || Touching(_van.Rear.Left) || Touching(_van.Rear.Right);
            foreach (RaycastHit hit in Physics.RaycastAll(transform.position + Vector3.up * 0.3f, Vector3.down, 1.5f, ~0, QueryTriggerInteraction.Ignore))
                if (!hit.collider.transform.IsChildOf(transform)) return true;
            return false;
        }

        private static bool Touching(WheelCollider wheel) => wheel != null && wheel.isGrounded;

        private void ReturnToLand(Vector3 entry)
        {
            (Vector3 pos, float yaw)? found = _history.Count > 0 ? _history[0] : _lastDry;
            for (int i = _history.Count - 1; i >= 0; i--)
            {
                Vector3 d = _history[i].pos - entry;
                if (new Vector2(d.x, d.z).magnitude >= Backoff && SeaReturnZone.Dry(_history[i].pos))
                {
                    found = _history[i];
                    break;
                }
            }
            if (found.HasValue && !SeaReturnZone.Dry(found.Value.pos)) found = _lastDry;
            // Never been on dry land (e.g. spawned in the sea): leave it where it is rather than lift it every tick.
            if (!found.HasValue || !SeaReturnZone.Dry(found.Value.pos)) return;
            (Vector3 pos, float yaw) target = found.Value;
            Vector3 up = target.pos + Vector3.up * 0.5f;
            if (_van != null)
            {
                _van.ResetUpright(up, target.yaw);
                return;
            }
            if (_pawn != null)
            {
                _pawn.Teleport(up, target.yaw);
                return;
            }
            if (_body != null)
            {
                _body.linearVelocity = Vector3.zero;
                _body.angularVelocity = Vector3.zero;
            }
            // A CharacterController would overwrite a plain transform move on its next Move call.
            bool hadController = TryGetComponent(out CharacterController controller) && controller.enabled;
            if (hadController) controller.enabled = false;
            transform.SetPositionAndRotation(up, Quaternion.Euler(0f, target.yaw, 0f));
            if (hadController)
            {
                controller.enabled = true;
                // Re-enabling recreates the shape and drops its IgnoreCollision pairs (GreyboxNpc re-applies them).
                SendMessage("OnSeaReturned", SendMessageOptions.DontRequireReceiver);
            }
        }
    }
}
