using UnityEngine;
using UnityEngine.InputSystem;

namespace Friendslop.PhysicsPlayground
{
    [DefaultExecutionOrder(100)]
    public sealed class PhysicsGrabber : MonoBehaviour
    {
        [SerializeField] private Camera interactionCamera;
        [SerializeField, Min(0f)] private float maxGrabDistance = 6f;
        [SerializeField, Min(0f)] private float holdDistance = 3f;
        [SerializeField, Min(0f)] private float springStrength = 120f;
        [SerializeField, Min(0f)] private float damping = 18f;
        [SerializeField, Min(0f)] private float maxForce = 1000f;

        private Rigidbody grabbedBody;
        private Vector3 localGrabPoint;

        public bool IsGrabbing => grabbedBody != null;

        public Rigidbody GrabbedBody => grabbedBody;

        public bool HasValidGrabTarget { get; private set; }

        private void Awake()
        {
            if (interactionCamera == null)
            {
                interactionCamera = GetComponent<Camera>();
            }

            if (interactionCamera == null)
            {
                interactionCamera = GetComponentInChildren<Camera>();
            }
        }

        private void Update()
        {
            HasValidGrabTarget = TryFindGrabTarget(out _, out _);

            Mouse mouse = Mouse.current;
            if (mouse == null)
            {
                return;
            }

            if (mouse.leftButton.wasPressedThisFrame && Cursor.lockState == CursorLockMode.Locked)
            {
                TryGrab();
            }

            if (grabbedBody != null && !mouse.leftButton.isPressed)
            {
                Release();
            }
        }

        private void FixedUpdate()
        {
            if (grabbedBody == null || grabbedBody.isKinematic || interactionCamera == null)
            {
                Release();
                return;
            }

            Vector3 worldGrabPoint = grabbedBody.transform.TransformPoint(localGrabPoint);
            Vector3 holdPoint = interactionCamera.transform.position + interactionCamera.transform.forward * holdDistance;
            Vector3 pointVelocity = grabbedBody.GetPointVelocity(worldGrabPoint);
            Vector3 force = (holdPoint - worldGrabPoint) * springStrength - pointVelocity * damping;

            grabbedBody.AddForceAtPosition(Vector3.ClampMagnitude(force, maxForce), worldGrabPoint, ForceMode.Force);
        }

        private void TryGrab()
        {
            if (!TryFindGrabTarget(out Rigidbody body, out RaycastHit hit))
            {
                return;
            }

            grabbedBody = body;
            localGrabPoint = body.transform.InverseTransformPoint(hit.point);
            grabbedBody.WakeUp();
        }

        private bool TryFindGrabTarget(out Rigidbody body, out RaycastHit hit)
        {
            body = null;

            if (interactionCamera == null)
            {
                hit = default;
                return false;
            }

            Ray ray = interactionCamera.ViewportPointToRay(new Vector3(0.5f, 0.5f));
            if (!Physics.Raycast(ray, out hit, maxGrabDistance, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            {
                return false;
            }

            body = hit.rigidbody;
            return body != null && !body.isKinematic;
        }

        private void Release()
        {
            grabbedBody = null;
            localGrabPoint = Vector3.zero;
        }

        private void OnDisable()
        {
            HasValidGrabTarget = false;
            Release();
        }

        private void OnDestroy()
        {
            Release();
        }
    }
}
