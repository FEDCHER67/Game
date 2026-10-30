using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.LowLevel;

/// <summary>VanOnly scripted test mode (30.10). Does nothing unless the player is started with <c>-vanTest &lt;mode&gt;</c>; then it
/// drives the scene itself (no keyboard or mouse input from outside): poses the player and camera, opens doors, drives the
/// van, writes screenshots and a log to <c>-vanTestOut &lt;folder&gt;</c> (default: persistentDataPath/vantest) and writes
/// done.txt at the end (the caller then stops the process; no Quit, so no settings are saved).
/// Modes: shots (the review shots), fps (frame time with every door state, outside and inside), roof (the player on the
/// roof, parked and while the van drives: is the player ever moved by game code?).
/// While a test runs, keyboard and mouse are ignored (legacy input reset before every script phase, Input System keyboard
/// and mouse disabled): a test window that happens to get keyboard focus cannot be moved or driven by someone's typing.</summary>
[DefaultExecutionOrder(32000)]
public sealed class VanOnlyTestMode : MonoBehaviour
{
    private string _out;
    private readonly StringBuilder _log = new();
    private float _lockYaw = float.NaN, _lockPitch = float.NaN;
    private bool _relativeYaw; // lock yaw relative to the van (cockpit look-back)
    private float _throttle = float.NaN;
    private VanController _van;
    private GreyboxPawn _pawn;

    private static string Arg(string key)
    {
        var a = System.Environment.GetCommandLineArgs();
        int i = System.Array.IndexOf(a, key);
        return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
    }

    // Its own save slot (fresh each run): a test never reads or writes the player's VanOnly save.
    private void Awake()
    {
        if (Arg("-vanTest") == null) return;
        BlockInput();
        CaptureTestHooks.SaveSlot = "capture_vanonly_vantest.json";
        string dir = Path.Combine(Application.persistentDataPath, "OnlyVolunteers");
        if (Directory.Exists(dir))
            foreach (string f in Directory.GetFiles(dir, "capture_vanonly_vantest.json*")) File.Delete(f);
    }

    private IEnumerator Start()
    {
        string mode = Arg("-vanTest");
        if (mode == null) { enabled = false; yield break; }
        Application.runInBackground = true; // keeps going when the window is not in front (nothing here needs focus)
        _out = Arg("-vanTestOut") ?? Path.Combine(Application.persistentDataPath, "vantest");
        Directory.CreateDirectory(_out);
        Line($"vanTest {mode}: screen {Screen.width}x{Screen.height} {Screen.fullScreenMode}");
        float until = Time.realtimeSinceStartup + 40f;
        CaptureDirector d = null;
        while ((d == null || !d.Ready || !d.Loaded || d.Pawn == null || d.Van == null) && Time.realtimeSinceStartup < until)
        {
            yield return null;
            d = CaptureDirector.Instance;
        }
        if (d == null || d.Van == null) { Line("no director / van"); Done(); yield break; }
        _van = d.Van;
        _pawn = d.Pawn;
        yield return new WaitForSecondsRealtime(3f);
        if (mode == "shots") yield return Shots();
        else if (mode == "fps") yield return Fps();
        else if (mode == "roof") yield return Roof();
        else Line("unknown mode " + mode);
        Done();
    }

    // Legacy input reset at the start of FixedUpdate, Update and PreLateUpdate (before any script reads it), every frame.
    private static void BlockInput()
    {
        PlayerLoopSystem loop = PlayerLoop.GetCurrentPlayerLoop();
        for (int i = 0; i < loop.subSystemList.Length; i++)
        {
            System.Type t = loop.subSystemList[i].type;
            if (t != typeof(UnityEngine.PlayerLoop.FixedUpdate) && t != typeof(UnityEngine.PlayerLoop.Update) &&
                t != typeof(UnityEngine.PlayerLoop.PreLateUpdate)) continue;
            var list = new List<PlayerLoopSystem>(loop.subSystemList[i].subSystemList);
            list.Insert(0, new PlayerLoopSystem { type = typeof(VanOnlyTestMode), updateDelegate = Input.ResetInputAxes });
            loop.subSystemList[i].subSystemList = list.ToArray();
        }
        PlayerLoop.SetPlayerLoop(loop);
        if (Keyboard.current != null) InputSystem.DisableDevice(Keyboard.current);
        if (Mouse.current != null) InputSystem.DisableDevice(Mouse.current);
    }

    // ------------------------------------------------------------------ helpers
    private Transform V => _van.transform;
    private VanDoor[] Doors => _van.GetComponentsInChildren<VanDoor>(true);

    private void SetDoors(bool rear, bool slide, bool cab)
    {
        foreach (var door in Doors)
            door.Request(door.name.Contains("Rear") ? rear : door.name.Contains("Slide") ? slide : cab);
    }

    private void Stand(Vector3 local, float yawOffset, float pitch = 0f)
    {
        float yaw = V.eulerAngles.y + yawOffset;
        _pawn.Teleport(V.TransformPoint(local), yaw);
        _lockYaw = yaw;
        _lockPitch = pitch;
        _relativeYaw = false;
    }

    private IEnumerator Shot(string name, float wait = 1.2f)
    {
        yield return new WaitForSecondsRealtime(wait);
        string f = Path.Combine(_out, name + ".png");
        ScreenCapture.CaptureScreenshot(f);
        yield return new WaitForSecondsRealtime(0.5f);
        Line("shot " + f);
    }

    private void LateUpdate()
    {
        // after VanDriveInput.Update (it writes the seated driver's keys, none here): the next physics steps use ours
        if (_van != null && !float.IsNaN(_throttle)) { _van.Handbrake = false; _van.Throttle = _throttle; _van.Steer = 0f; }
        if (Camera.main == null || float.IsNaN(_lockYaw)) return;
        float yaw = _relativeYaw ? V.eulerAngles.y + _lockYaw : _lockYaw;
        Camera.main.transform.rotation = Quaternion.Euler(float.IsNaN(_lockPitch) ? 0f : _lockPitch, yaw, 0f);
    }

    private void FixedUpdate()
    {
        if (_van == null || float.IsNaN(_throttle)) return;
        _van.Handbrake = false;
        _van.Throttle = _throttle;
        _van.Steer = 0f;
    }

    private void Line(string s)
    {
        Debug.Log("[VANTEST] " + s);
        _log.AppendLine(s);
    }

    private void Done()
    {
        _throttle = float.NaN;
        File.WriteAllText(Path.Combine(_out, "log.txt"), _log.ToString());
        File.WriteAllText(Path.Combine(_out, "done.txt"), "done");
    }

    private GreyboxVanSeat Seat => _van.GetComponent<GreyboxVanSeat>();

    private IEnumerator EnterSeat(bool cockpit)
    {
        _lockYaw = float.NaN;
        _pawn.Teleport(V.TransformPoint(Seat.DoorPoint), V.eulerAngles.y + 90f);
        yield return new WaitForSecondsRealtime(0.8f);
        Seat.Enter();
        yield return new WaitForSecondsRealtime(1.5f);
        foreach (var rig in FindObjectsByType<VanCameraRig>(FindObjectsInactive.Exclude))
            if ((rig.CurrentMode == VanCameraRig.Mode.Cockpit) != cockpit) rig.ToggleMode();
        Line($"in the seat: driving {Seat.Driving}, cockpit {cockpit}");
    }

    // ------------------------------------------------------------------ shots
    private IEnumerator Shots()
    {
        _lockYaw = float.NaN;
        yield return Shot("01_start_view", 0.5f);
        // outside 3/4 front-right, 7 m out, looking at the van
        Vector3 p = new Vector3(5.2f, 0f, 5.4f);
        Stand(p, Mathf.Atan2(-p.x, -p.z) * Mathf.Rad2Deg, 8f);
        yield return Shot("02_outside_three_quarter");
        Stand(new Vector3(8.5f, 0f, 0f), -90f, 6f);
        yield return Shot("03_side_right");
        SetDoors(true, false, false);
        Stand(new Vector3(0f, 0f, -4.7f), 0f, 8f);
        yield return Shot("04_bay_from_rear_doors", 2f);
        // walking through the bay: the player stepped 0.45 m at a time from the doors to the bulkhead (flicker check)
        for (int i = 0; i < 6; i++)
        {
            Stand(new Vector3(0f, 0.5566f, -2.6f + i * 0.55f), 0f, 4f);
            yield return Shot($"05_walk_in_bay_{i:00}", 0.35f);
        }
        Stand(new Vector3(0f, 0.5566f, -2.4f), 180f, 4f);
        yield return Shot("06_bay_looking_out");
        SetDoors(false, false, false);
        yield return new WaitForSecondsRealtime(1.5f);
        // walking on the grey floor next to the van
        for (int i = 0; i < 4; i++)
        {
            Stand(new Vector3(3.5f, 0f, -4f + i * 1.5f), -20f, 10f);
            yield return Shot($"07_walk_floor_{i:00}", 0.35f);
        }
        yield return EnterSeat(false);
        _lockYaw = float.NaN;
        yield return Shot("08_driver_chase");
        foreach (var rig in FindObjectsByType<VanCameraRig>(FindObjectsInactive.Exclude)) rig.ToggleMode();
        yield return Shot("09_driver_dashboard");
        _relativeYaw = true; _lockYaw = 150f; _lockPitch = 5f;
        yield return Shot("10_driver_look_back");
        _lockYaw = float.NaN;
        _throttle = 0.6f;
        for (int i = 0; i < 4; i++) yield return Shot($"11_driving_cockpit_{i:00}", 0.7f);
        Line($"driving: {_van.SpeedKmh:F1} km/h");
        foreach (var rig in FindObjectsByType<VanCameraRig>(FindObjectsInactive.Exclude)) rig.ToggleMode();
        for (int i = 0; i < 3; i++) yield return Shot($"12_driving_chase_{i:00}", 0.7f);
        _throttle = -1f;
        yield return new WaitForSecondsRealtime(2f);
        _throttle = float.NaN;
    }

    // ------------------------------------------------------------------ fps
    private IEnumerator Fps()
    {
        var states = new (string name, bool rear, bool slide, bool cab)[]
        {
            ("all shut", false, false, false), ("rear open", true, false, false), ("slide open", false, true, false),
            ("cab doors open", false, false, true), ("all open", true, true, true),
        };
        var spots = new (string name, Vector3 local, float yaw, float pitch)[]
        {
            ("outside behind, at the rear doors", new Vector3(0f, 0f, -7.5f), 0f, 0f),
            ("outside, looking up at the sky", new Vector3(0f, 0f, -7.5f), 0f, -35f),
            ("outside right side", new Vector3(5.5f, 0f, 0.3f), -90f, 0f),
            ("inside the bay, facing the rear doors", new Vector3(0f, 0.5566f, -0.6f), 180f, 0f),
            ("inside the bay, facing the bulkhead", new Vector3(0f, 0.5566f, -2.3f), 0f, 0f),
        };
        foreach (var spot in spots)
        {
            SetDoors(false, false, false);
            yield return new WaitForSecondsRealtime(1.2f);
            Stand(spot.local, spot.yaw, spot.pitch);
            yield return new WaitForSecondsRealtime(0.8f);
            Line("== " + spot.name);
            foreach (var st in states)
            {
                SetDoors(st.rear, st.slide, st.cab);
                yield return new WaitForSecondsRealtime(1.4f);
                yield return Measure(st.name);
            }
        }
        SetDoors(false, false, false);
        yield return EnterSeat(true);
        Line("== driver seat, cockpit");
        yield return Measure("all shut");
        SetDoors(true, false, false);
        yield return new WaitForSecondsRealtime(1.4f);
        yield return Measure("rear open");
    }

    private IEnumerator Measure(string label)
    {
        int frames = 0;
        double sum = 0, max = 0;
        float t0 = Time.realtimeSinceStartup;
        while (Time.realtimeSinceStartup - t0 < 2.5f)
        {
            yield return null;
            frames++;
            double dt = Time.unscaledDeltaTime * 1000.0;
            sum += dt;
            if (dt > max) max = dt;
        }
        Line($"  [{label}] {frames / 2.5f:F0} fps, frame avg {sum / frames:F2} ms, worst {max:F1} ms");
    }

    // ------------------------------------------------------------------ roof
    private IEnumerator Roof()
    {
        var rider = _pawn.Body.GetComponent<GreyboxCargoRider>();
        // 1) what E offers on the roof (GreyboxInteractor resolves the label every frame; E runs that action)
        var interactor = FindFirstObjectByType<GreyboxInteractor>();
        var label = typeof(GreyboxInteractor).GetField("_label", BindingFlags.NonPublic | BindingFlags.Instance);
        Vector3? seatSpot = null;
        foreach (float z in new[] { 2.2f, 1.2f, 0.2f, -0.8f, -1.8f, -2.8f })
        {
            Stand(new Vector3(0f, 2.75f, z), 0f, 10f);
            yield return new WaitForSecondsRealtime(0.8f);
            string offer = interactor != null && label != null ? label.GetValue(interactor) as string : "?";
            Line($"roof z {z:F1}: feet in van space {V.InverseTransformPoint(_pawn.Position)}, CanEnter {Seat.CanEnter}, E offers '{offer ?? "nothing"}'");
            if (Seat.CanEnter && seatSpot == null) seatSpot = new Vector3(0f, 2.75f, z);
        }
        // 2) E there (the interactor's Act.Enter = Seat.Enter), then E again (GreyboxVanSeat.Update -> GetOut)
        if (seatSpot is Vector3 spot)
        {
            Stand(spot, 0f, 10f);
            yield return new WaitForSecondsRealtime(0.8f);
            Line($"E on the roof at {V.InverseTransformPoint(_pawn.Position)}");
            Seat.Enter();
            yield return new WaitForSecondsRealtime(1.5f);
            Line($"  -> driving {Seat.Driving}");
            typeof(GreyboxVanSeat).GetMethod("GetOut", BindingFlags.NonPublic | BindingFlags.Instance)?.Invoke(Seat, null);
            yield return new WaitForSecondsRealtime(1f);
            Line($"  E again -> driving {Seat.Driving}, player now at {V.InverseTransformPoint(_pawn.Position)} (van space: outside the driver door)");
            yield return Shot("roof_after_E_E", 0.3f);
        }
        else
        {
            // E on the front of the roof anyway (Seat.Enter is what the interactor's E calls): must do nothing
            Stand(new Vector3(0f, 2.75f, 1.2f), 0f, 10f);
            yield return new WaitForSecondsRealtime(0.8f);
            Seat.Enter();
            yield return new WaitForSecondsRealtime(1.0f);
            Line($"E on the roof front at {V.InverseTransformPoint(_pawn.Position)} -> driving {Seat.Driving} (expected False)");
        }
        // 2b) beside the driver door on the floor: E seats, E again gets out by the door
        Stand(Seat.DoorPoint, 90f, 5f);
        yield return new WaitForSecondsRealtime(0.8f);
        string doorOffer = interactor != null && label != null ? label.GetValue(interactor) as string : "?";
        Line($"door: feet in van space {V.InverseTransformPoint(_pawn.Position)}, CanEnter {Seat.CanEnter}, E offers '{doorOffer ?? "nothing"}'");
        Seat.Enter();
        yield return new WaitForSecondsRealtime(1.5f);
        Line($"  E at the door -> driving {Seat.Driving} (expected True)");
        typeof(GreyboxVanSeat).GetMethod("GetOut", BindingFlags.NonPublic | BindingFlags.Instance)?.Invoke(Seat, null);
        yield return new WaitForSecondsRealtime(1f);
        Line($"  E again -> driving {Seat.Driving} (expected False), player at {V.InverseTransformPoint(_pawn.Position)} (van space)");
        // HUD: no new-game objective, no F1-F8 teleports
        var trip = _van.GetComponent<GreyboxTripMeter>();
        Line($"HUD: new-game objective '{CaptureDirector.Instance.NewGameObjective}', trip meter teleport spots {(trip ? trip.Spots.Length : -1)}");
        // 3) standing on the roof, parked, driving and braking: does anything move the player?
        Stand(new Vector3(0f, 2.75f, -1.0f), 0f, 10f);
        _lockYaw = float.NaN;
        Vector3 last = _pawn.Position;
        Line($"on the roof: pawn {_pawn.Position}, van {V.position}");
        int jumps = 0;
        float t0 = Time.realtimeSinceStartup;
        float drive = 6f, stop = 13f, end = 18f;
        bool driving = false, braking = false;
        while (Time.realtimeSinceStartup - t0 < end)
        {
            float t = Time.realtimeSinceStartup - t0;
            if (!driving && t >= drive) { driving = true; _throttle = 0.5f; Line("van drives"); }
            if (!braking && t >= stop) { braking = true; _throttle = -1f; Line("van brakes"); }
            yield return null;
            Vector3 p = _pawn.Position;
            float step = (p - last).magnitude;
            float expected = _van.GetComponent<Rigidbody>().linearVelocity.magnitude * Time.deltaTime + 0.3f;
            if (step > expected)
            {
                jumps++;
                Line($"  JUMP at {t:F2} s: {step:F2} m (van {_van.SpeedKmh:F1} km/h) from {V.InverseTransformPoint(last)} to {V.InverseTransformPoint(p)} (van space)");
            }
            last = p;
            if (Time.frameCount % 30 == 0)
                Line($"  t {t:F1}: pawn in van space {V.InverseTransformPoint(p)}, van {_van.SpeedKmh:F1} km/h, cargo rider {(rider && rider.Carrier ? "riding" : "no")}, controlled {_pawn.Controlled}");
        }
        _throttle = float.NaN;
        Line($"roof test: {jumps} jumps; pawn ends in van space {V.InverseTransformPoint(_pawn.Position)}");
    }
}
