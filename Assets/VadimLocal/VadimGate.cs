using OnlyVolunteers.Map;
using UnityEngine;

namespace OnlyVolunteers.VadimLocal
{
    /// <summary>Vadim 25.10 (local W86): a swing gate (Tramduro island). Near it, E opens / closes it; runs before the van seat
    /// and the pawn interactor and takes the E, so the same press does not also get you out of the van.</summary>
    [DefaultExecutionOrder(-200)]
    public sealed class VadimGate : MonoBehaviour
    {
        public Transform[] leaves = new Transform[0];
        public float[] openYaw = new float[0];
        public float reach = 16f;
        public float seconds = 1.6f;

        private Quaternion[] _closed;
        private bool _open;
        private float _t;

        private void Start()
        {
            _closed = new Quaternion[leaves.Length];
            for (int i = 0; i < leaves.Length; i++) _closed[i] = leaves[i].localRotation;
        }

        private bool Near()
        {
            var cam = Camera.main;
            return cam && Vector3.Distance(cam.transform.position, transform.position) < reach;
        }

        private void Update()
        {
            if (Near() && Input.GetKeyDown(KeyCode.E) && GreyboxInput.EFree) { _open = !_open; GreyboxInput.UseE(); }
            float target = _open ? 1f : 0f;
            if (Mathf.Approximately(_t, target)) return;
            _t = Mathf.MoveTowards(_t, target, Time.deltaTime / Mathf.Max(.1f, seconds));
            float e = Mathf.SmoothStep(0f, 1f, _t);
            for (int i = 0; i < leaves.Length; i++) leaves[i].localRotation = _closed[i] * Quaternion.Euler(0f, openYaw[i] * e, 0f);
        }

        private void OnGUI()
        {
            if (!Near()) return;
            var r = new Rect(Screen.width * .5f - 120, Screen.height * .78f, 240, 28);
            GUI.Box(r, _open ? "E — закрыть ворота" : "E — открыть ворота");
        }
    }
}
