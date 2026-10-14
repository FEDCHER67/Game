using UnityEngine;

namespace OnlyVolunteers.Vehicles.Paint
{
    public sealed class VanPaintProp : MonoBehaviour
    {
        [SerializeField] bool isBrush;
        [SerializeField] Color paintColor;
        [SerializeField] string colorName;
        Vector3 homePosition;
        Quaternion homeRotation;
        Transform homeParent;
        Collider[] colliders;
        public bool IsBrush => isBrush;
        public Color PaintColor => paintColor;
        public string ColorName => colorName;
        public void Configure(bool brush, Color color, string label) { isBrush = brush; paintColor = color; colorName = label; }
        void Awake() { homePosition = transform.position; homeRotation = transform.rotation; homeParent = transform.parent; colliders = GetComponentsInChildren<Collider>(); }
        public void Hold(Transform hand)
        {
            transform.SetParent(hand, false); transform.localPosition = Vector3.zero; transform.localRotation = Quaternion.identity;
            foreach (var c in colliders) c.enabled = false;
        }
        public void ReturnToStand()
        {
            transform.SetParent(homeParent); transform.SetPositionAndRotation(homePosition, homeRotation);
            foreach (var c in colliders) c.enabled = true;
        }
    }
}
