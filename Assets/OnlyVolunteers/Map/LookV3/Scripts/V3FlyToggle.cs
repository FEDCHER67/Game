using System.Collections.Generic;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Player;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.Rendering.Universal;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace OnlyVolunteers.Map.Look.V3
{
    // Fly mode inside the v17 Play scene (Fedya 2026-10-12: "fly over the map, not only drive"). Backslash (`\`, the key
    // above Enter; BackQuote is the police HUD) detaches the view into a free LookFlyCamera at the current camera pose:
    // WASD, Q/E down/up, Shift x4, hold RMB + mouse to look, wheel = speed. The player and van input are suspended
    // meanwhile (KCC walk/look locked; interactor, inventory, phone, van driving, van seat and van camera switched off;
    // a driven van gets the handbrake). The same key restores exactly what was switched: cameras, components, KCC flags,
    // cursor. Debug keys (F1-F8 trip meter, F11/F12 crowd, BackQuote police) keep working. Placed by MapLookGameplayV3.
    public sealed class V3FlyToggle : MonoBehaviour
    {
        public const string KeyName = "Backslash";

        public bool Flying => fly != null;

        private Camera fly;
        private readonly List<Camera> cameras = new List<Camera>();
        private readonly List<Behaviour> behaviours = new List<Behaviour>();
        private readonly List<(KccFirstPersonInput input, bool movementLocked, bool lookSuspended)> kccs =
            new List<(KccFirstPersonInput, bool, bool)>();
        private readonly List<VanController> vans = new List<VanController>();
        private CursorLockMode cursorLock;
        private bool cursorVisible;

        private void Update()
        {
            if (!TogglePressed()) return;
            if (Flying) Land();
            else TakeOff();
        }

        private static bool TogglePressed()
        {
#if ENABLE_INPUT_SYSTEM
            if (Keyboard.current != null) return Keyboard.current.backslashKey.wasPressedThisFrame;
#endif
#if ENABLE_LEGACY_INPUT_MANAGER
            return Input.GetKeyDown(KeyCode.Backslash);
#else
            return false;
#endif
        }

        public void TakeOff()
        {
            if (Flying) return;
            // The camera on screen: the highest-depth enabled base camera that renders to the display.
            Camera source = null;
            foreach (Camera c in Camera.allCameras)
            {
                if (c.targetTexture != null) continue;
                if (c.TryGetComponent(out UniversalAdditionalCameraData d) && d.renderType != CameraRenderType.Base) continue;
                cameras.Add(c);
                if (source == null || c.depth > source.depth) source = c;
            }
            if (source == null)
            {
                cameras.Clear();
                return;
            }
            cursorLock = Cursor.lockState;
            cursorVisible = Cursor.visible;

            foreach (KccFirstPersonInput k in FindObjectsByType<KccFirstPersonInput>(FindObjectsSortMode.None))
            {
                kccs.Add((k, k.MovementLocked, k.LookSuspended));
                k.MovementLocked = true;
                k.LookSuspended = true;
            }
            // The interactor first: its OnDisable may give the inventory back, which is then recorded as it stands.
            Suspend<GreyboxInteractor>();
            Suspend<InventoryInput>();
            Suspend<PhoneController>();
            Suspend<GreyboxVanSeat>();
            Suspend<VanCameraRig>();
            foreach (VanDriveInput drive in FindObjectsByType<VanDriveInput>(FindObjectsSortMode.None))
            {
                if (!drive.enabled) continue;
                drive.enabled = false;
                behaviours.Add(drive);
                if (drive.TryGetComponent(out VanController van))
                {
                    van.Throttle = 0f;
                    van.Steer = 0f;
                    van.Handbrake = true;
                    vans.Add(van);
                }
            }

            var go = new GameObject("V3_FlyCamera") { tag = "MainCamera" };
            go.transform.SetPositionAndRotation(source.transform.position, source.transform.rotation);
            fly = go.AddComponent<Camera>();
            fly.CopyFrom(source);
            fly.targetTexture = null;
            var data = go.AddComponent<UniversalAdditionalCameraData>();
            if (source.TryGetComponent(out UniversalAdditionalCameraData src))
            {
                data.renderPostProcessing = src.renderPostProcessing;
                data.antialiasing = src.antialiasing;
                data.antialiasingQuality = src.antialiasingQuality;
                data.stopNaN = src.stopNaN;
                data.dithering = src.dithering;
                data.renderShadows = src.renderShadows;
                data.requiresDepthOption = src.requiresDepthOption;
                data.requiresColorOption = src.requiresColorOption;
                data.volumeLayerMask = src.volumeLayerMask;
            }
            foreach (Camera c in cameras) c.enabled = false;
            go.AddComponent<LookFlyCamera>();
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }

        public void Land()
        {
            if (!Flying) return;
            Destroy(fly.gameObject);
            fly = null;
            foreach (Camera c in cameras)
                if (c != null) c.enabled = true;
            cameras.Clear();
            for (int i = behaviours.Count - 1; i >= 0; i--)
                if (behaviours[i] != null) behaviours[i].enabled = true;
            behaviours.Clear();
            // A van driven before take-off: its input writes throttle, steering and handbrake again from this frame on.
            vans.Clear();
            foreach (var k in kccs)
            {
                if (k.input == null) continue;
                k.input.MovementLocked = k.movementLocked;
                k.input.LookSuspended = k.lookSuspended;
            }
            kccs.Clear();
            Cursor.lockState = cursorLock;
            Cursor.visible = cursorVisible;
        }

        private void Suspend<T>() where T : Behaviour
        {
            foreach (T b in FindObjectsByType<T>(FindObjectsSortMode.None))
            {
                if (!b.enabled) continue;
                b.enabled = false;
                behaviours.Add(b);
            }
        }

        private void OnDisable()
        {
            if (Flying) Land();
        }

        private void OnGUI()
        {
            if (!Flying) return;
            var style = new GUIStyle(GUI.skin.label) { fontSize = 16, alignment = TextAnchor.UpperLeft };
            GUI.Label(new Rect(16f, 12f, 900f, 26f),
                "Полёт: WASD, Q/E вниз/вверх, Shift ×4, ПКМ+мышь — осмотр, колесо — скорость; \\ — вернуться", style);
        }
    }
}
