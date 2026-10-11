using UnityEngine;

namespace OnlyVolunteers.Map.Dev
{
    // A small art-review scene: automatic Idle/Walk/Run comparison, or the real playable Buddy controller.
    // This component is used only by Buddy_Locomotion_v01, never by the map or the networked player.
    public sealed class BuddyLocomotionPreview : MonoBehaviour
    {
        public Animator[] Actors;
        public GreyboxWalker Player;
        public GreyboxFollowCamera Follow;
        public Camera PreviewCamera;
        public bool Automatic = true;

        private readonly Vector3[] _starts = new Vector3[2];
        private float _clock;
        private string _state;
        private bool _previousAutomatic;
        private CharacterController _controller;

        private void Start()
        {
            _controller = Player.GetComponent<CharacterController>();
            for (int i = 0; i < Actors.Length; i++) _starts[i] = Actors[i].transform.parent.position;
            _previousAutomatic = !Automatic;
            SetMode();
        }

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.Space)) Automatic = !Automatic;
            if (Automatic != _previousAutomatic) SetMode();
            if (!Automatic) return;

            _clock += Time.deltaTime;
            if (_clock >= 12f)
            {
                _clock %= 12f;
                for (int i = 0; i < Actors.Length; i++) Actors[i].transform.parent.position = _starts[i];
            }
            string next = _clock < 2f || _clock >= 10f ? "Idle" : _clock < 5f || _clock >= 7f ? "Walk" : "Run";
            float speed = next == "Walk" ? 1.5f : next == "Run" ? 3.2f : 0f;
            foreach (Animator actor in Actors)
            {
                actor.speed = 1f;
                if (next != _state) actor.CrossFadeInFixedTime(next, 0.15f);
                actor.transform.parent.position += Vector3.forward * (speed * Time.deltaTime);
            }
            _state = next;
        }

        private void SetMode()
        {
            Player.enabled = !Automatic;
            _controller.enabled = !Automatic;
            Follow.enabled = !Automatic;
            if (Automatic)
            {
                _clock = 0f;
                _state = null;
                for (int i = 0; i < Actors.Length; i++)
                    Actors[i].transform.parent.SetPositionAndRotation(_starts[i], Quaternion.identity);
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }
            else
            {
                // Let GreyboxWalker's state cache and the Animator start from the same pose after the auto loop.
                Actors[0].Play("Idle", 0, 0f);
                Actors[0].speed = 1f;
                Actors[1].CrossFadeInFixedTime("Idle", 0.15f);
                Follow.SnapBehind(Player.transform);
            }
            _previousAutomatic = Automatic;
        }

        private void LateUpdate()
        {
            if (!Automatic) return;
            Vector3 middle = (Actors[0].transform.position + Actors[1].transform.position) * 0.5f + Vector3.up * 0.9f;
            PreviewCamera.transform.position = middle + new Vector3(3.8f, 1.6f, 5f);
            PreviewCamera.transform.LookAt(middle);
        }

        private void OnGUI()
        {
            GUI.Box(new Rect(16, 16, 480, 82), GUIContent.none);
            GUI.Label(new Rect(28, 24, 455, 24), "SAUSAGE BUDDY A / B — " + (Automatic ? _state : "PLAYER CONTROL"));
            GUI.Label(new Rect(28, 48, 455, 24), "Space: auto / manual    WASD: walk    Shift: run");
            GUI.Label(new Rect(28, 68, 455, 24), "Manual camera: right mouse drag.  Escape: release cursor.");
        }
    }
}
