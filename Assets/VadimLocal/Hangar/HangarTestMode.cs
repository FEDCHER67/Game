using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.LowLevel;

/// <summary>HangarLab scripted test mode (30.10). Does nothing unless the player is started with <c>-hangarTest &lt;mode&gt;</c>;
/// then it drives the scene itself (keyboard and mouse ignored): poses the player and camera, drives the van out of the
/// gate and back, writes screenshots and a log to <c>-hangarTestOut &lt;folder&gt;</c> and done.txt at the end (the caller
/// stops the process; no Quit, so no settings are saved). Modes: shots, fps, drive, all. Positions are hangar-local.</summary>
[DefaultExecutionOrder(32000)]
public sealed class HangarTestMode : MonoBehaviour
{
    private string _out;
    private readonly StringBuilder _log = new();
    private float _lockYaw = float.NaN, _lockPitch = float.NaN;
    private float _throttle = float.NaN, _steer;
    private VanController _van;
    private GreyboxPawn _pawn;
    private Transform _hangar;

    private static string Arg(string key)
    {
        var a = System.Environment.GetCommandLineArgs();
        int i = System.Array.IndexOf(a, key);
        return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
    }

    private void Awake()
    {
        if (Arg("-hangarTest") == null) return;
        BlockInput();
        CaptureTestHooks.SaveSlot = "capture_hangar_test.json";
        string dir = Path.Combine(Application.persistentDataPath, "OnlyVolunteers");
        if (Directory.Exists(dir))
            foreach (string f in Directory.GetFiles(dir, "capture_hangar_test.json*")) File.Delete(f);
    }

    private IEnumerator Start()
    {
        string mode = Arg("-hangarTest");
        if (mode == null) { enabled = false; yield break; }
        Application.runInBackground = true;
        _out = Arg("-hangarTestOut") ?? Path.Combine(Application.persistentDataPath, "hangartest");
        Directory.CreateDirectory(_out);
        Line($"hangarTest {mode}: screen {Screen.width}x{Screen.height} {Screen.fullScreenMode}");
        float until = Time.realtimeSinceStartup + 40f;
        CaptureDirector d = null;
        while ((d == null || !d.Ready || !d.Loaded || d.Pawn == null || d.Van == null) && Time.realtimeSinceStartup < until)
        {
            yield return null;
            d = CaptureDirector.Instance;
        }
        var root = GameObject.Find("Hangar_Base_v01");
        if (d == null || d.Van == null || root == null) { Line("no director / van / hangar"); Done(); yield break; }
        _hangar = root.transform;
        _van = d.Van;
        _pawn = d.Pawn;
        yield return new WaitForSecondsRealtime(3f);
        var rp = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline as UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset;
        if (rp) Line($"render scale {rp.renderScale:F2}, MSAA {rp.msaaSampleCount}, shadow distance {rp.shadowDistance}");
        Line($"start: pawn {Local(_pawn.Position)}, van {Local(_van.transform.position)} yaw {_van.transform.eulerAngles.y:F0}");
        if (mode == "shots" || mode == "all") yield return Shots();
        if (mode == "drive" || mode == "all") yield return Drive();
        if (mode == "fps" || mode == "all") yield return Fps();
        if (mode == "cargo" || mode == "all") yield return CargoDoors();
        Done();
    }

    private static void BlockInput()
    {
        PlayerLoopSystem loop = PlayerLoop.GetCurrentPlayerLoop();
        for (int i = 0; i < loop.subSystemList.Length; i++)
        {
            System.Type t = loop.subSystemList[i].type;
            if (t != typeof(UnityEngine.PlayerLoop.FixedUpdate) && t != typeof(UnityEngine.PlayerLoop.Update) &&
                t != typeof(UnityEngine.PlayerLoop.PreLateUpdate)) continue;
            var list = new List<PlayerLoopSystem>(loop.subSystemList[i].subSystemList);
            list.Insert(0, new PlayerLoopSystem { type = typeof(HangarTestMode), updateDelegate = Input.ResetInputAxes });
            loop.subSystemList[i].subSystemList = list.ToArray();
        }
        PlayerLoop.SetPlayerLoop(loop);
        if (Keyboard.current != null) InputSystem.DisableDevice(Keyboard.current);
        if (Mouse.current != null) InputSystem.DisableDevice(Mouse.current);
    }

    // ------------------------------------------------------------------ helpers
    private Vector3 World(float x, float z) => _hangar.TransformPoint(new Vector3(x, 0.05f, z));
    private Vector3 Local(Vector3 w) => _hangar.InverseTransformPoint(w);

    private void Stand(float x, float z, float lookX, float lookZ, float pitch)
    {
        float yaw = Mathf.Atan2(lookX - x, lookZ - z) * Mathf.Rad2Deg + _hangar.eulerAngles.y;
        _pawn.Teleport(World(x, z), yaw);
        _lockYaw = yaw;
        _lockPitch = pitch;
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
        if (_van != null && !float.IsNaN(_throttle)) { _van.Handbrake = false; _van.Throttle = _throttle; _van.Steer = _steer; }
        if (Camera.main == null || float.IsNaN(_lockYaw)) return;
        Camera.main.transform.rotation = Quaternion.Euler(float.IsNaN(_lockPitch) ? 0f : _lockPitch, _lockYaw, 0f);
    }

    private void FixedUpdate()
    {
        if (_van == null || float.IsNaN(_throttle)) return;
        _van.Handbrake = false;
        _van.Throttle = _throttle;
        _van.Steer = _steer;
    }

    private void Line(string s)
    {
        Debug.Log("[HANGARTEST] " + s);
        _log.AppendLine(s);
    }

    private void Done()
    {
        _throttle = float.NaN;
        File.WriteAllText(Path.Combine(_out, "log.txt"), _log.ToString());
        File.WriteAllText(Path.Combine(_out, "done.txt"), "done");
    }

    private GreyboxVanSeat Seat => _van.GetComponent<GreyboxVanSeat>();

    // ------------------------------------------------------------------ shots (hangar-local x, z, look-at x, z, pitch)
    private static readonly (string name, float x, float z, float lx, float lz, float pitch)[] Views =
    {
        ("01_spawn_to_van", -15f, -12.5f, 0f, -2f, 4f),
        ("02_van_and_npcs", 7f, -9f, 0f, 0f, 6f),
        ("03_hall_to_rooms", 0f, -14f, 0f, 17f, 2f),
        ("04_bay_front", -16.5f, -1f, -16.5f, 17f, 2f),
        ("05_bay_inside", -16.5f, 8.2f, -16.5f, 17f, 6f),
        ("06_bay_looking_out", -14f, 15.5f, -14f, 0f, 4f),
        ("07_pharmacy_front", -1f, 5f, -1f, 17f, 0f),
        ("08_pharmacy_inside", 1.8f, 16.2f, -1f, 11f, 6f),
        ("09_gear_front", 11.5f, 5f, 11.5f, 17f, 0f),
        ("10_gear_inside", 11.5f, 11.8f, 11.5f, 17f, 2f),
        ("11_lounge", -15.5f, -9.5f, -22f, -14.5f, 8f),
        ("12_gate_from_inside", 6f, -1f, 25f, 0f, 2f),
        ("13_outside_looking_in", 42f, 2f, 0f, 0f, 2f),
        ("14_trusses_up", 0f, -6f, 0f, 6f, -55f),
        ("15_corner_diagonal", -23f, -15f, 25f, 17f, 4f),
        ("16_left_wall", 0f, -4f, -25f, -4f, 2f),
        ("17_front_wall", 2f, 4f, 2f, -17f, 4f),
        ("18_back_right", 10f, -6f, 25f, 17f, 2f),
    };

    private IEnumerator Shots()
    {
        _lockYaw = float.NaN;
        yield return Shot("00_start_view", 0.5f);
        foreach (var v in Views)
        {
            Stand(v.x, v.z, v.lx, v.lz, v.pitch);
            yield return Shot(v.name);
        }
        _lockYaw = float.NaN;
    }

    // ------------------------------------------------------------------ drive: out of the gate, a loop outside, back in
    private IEnumerator Drive()
    {
        Stand(-15f, -12.5f, 0f, -2f, 0f);
        yield return new WaitForSecondsRealtime(0.8f);
        _lockYaw = float.NaN;
        _pawn.Teleport(_van.transform.TransformPoint(Seat.DoorPoint), _van.transform.eulerAngles.y + 90f);
        yield return new WaitForSecondsRealtime(0.8f);
        Seat.Enter();
        yield return new WaitForSecondsRealtime(1.5f);
        foreach (var rig in FindObjectsByType<VanCameraRig>(FindObjectsInactive.Exclude))
            if (rig.CurrentMode != VanCameraRig.Mode.Chase) rig.ToggleMode();
        Line($"in the seat: driving {Seat.Driving}");
        // waypoints (hangar-local x, z): straight out of the gate, a wide loop outside, straight back in to the parking box
        var route = new[] { new Vector2(30f, -2f), new Vector2(46f, -2f), new Vector2(56f, 6f), new Vector2(52f, 16f), new Vector2(42f, 16f),
                            new Vector2(36f, 8f), new Vector2(32f, 1f), new Vector2(20f, 0f), new Vector2(6f, -1f) };
        int wp = 0;
        float steerSign = 1f;
        bool signChecked = false;
        float t0 = Time.realtimeSinceStartup, lastLog = 0f, prevSpeed = 0f;
        int frames = 0, hits = 0;
        double worst = 0, sum = 0;
        bool shotOut = false, shotOutside = false, shotIn = false;
        _throttle = 0f;
        float yawAtSteer = float.NaN;
        while (wp < route.Length && Time.realtimeSinceStartup - t0 < 120f)
        {
            yield return null;
            frames++;
            double dt = Time.unscaledDeltaTime * 1000.0;
            sum += dt; if (dt > worst) worst = dt;
            Vector3 lp = Local(_van.transform.position);
            Vector2 pos = new(lp.x, lp.z);
            Vector2 target = route[wp];
            if ((target - pos).magnitude < (wp == route.Length - 1 ? 1.5f : 4f)) { wp++; continue; }
            Vector3 fwdL = _hangar.InverseTransformDirection(_van.transform.forward);
            float ang = Vector2.SignedAngle(new Vector2(fwdL.x, fwdL.z), target - pos); // + = to the left (counter-clockwise)
            float steer = Mathf.Clamp(-ang / 30f, -1f, 1f) * steerSign;
            // the steer sign is checked once: steering right must turn the van clockwise (yaw increasing)
            if (!signChecked && Mathf.Abs(steer) > 0.5f && _van.SpeedKmh > 5f)
            {
                if (float.IsNaN(yawAtSteer)) yawAtSteer = _van.transform.eulerAngles.y;
                else if (Mathf.Abs(Mathf.DeltaAngle(yawAtSteer, _van.transform.eulerAngles.y)) > 4f)
                {
                    float turned = Mathf.DeltaAngle(yawAtSteer, _van.transform.eulerAngles.y);
                    if (Mathf.Sign(turned) != Mathf.Sign(steer)) { steerSign = -steerSign; Line("steer sign flipped"); }
                    signChecked = true;
                }
            }
            _steer = steer;
            float speed = _van.SpeedKmh;
            float want = wp == route.Length - 1 ? 8f : Mathf.Abs(ang) > 25f ? 12f : 20f;
            _throttle = Mathf.Clamp((want - speed) * 0.15f, -1f, 0.8f);
            if (prevSpeed - speed > 4f && _throttle >= 0f) { hits++; Line($"  sudden stop at {lp} ({prevSpeed:F1} -> {speed:F1} km/h)"); }
            prevSpeed = speed;
            float t = Time.realtimeSinceStartup - t0;
            if (t - lastLog > 1f) { lastLog = t; Line($"  t {t:F1}: van local {lp.x:F1} {lp.y:F2} {lp.z:F1}, {speed:F1} km/h, steer {_steer:F2}, wp {wp}"); }
            if (!shotOut && lp.x > 24f) { shotOut = true; StartCoroutine(Shot("20_drive_through_gate_out", 0f)); }
            if (!shotOutside && wp == 3) { shotOutside = true; StartCoroutine(Shot("21_drive_outside", 0f)); }
            if (!shotIn && wp >= 7 && lp.x < 24f) { shotIn = true; StartCoroutine(Shot("22_drive_back_in", 0f)); }
        }
        _throttle = -1f; _steer = 0f;
        yield return new WaitForSecondsRealtime(2.5f);
        _throttle = float.NaN;
        Vector3 end = Local(_van.transform.position);
        Line($"drive: {(wp >= route.Length ? "route done" : "TIMEOUT at waypoint " + wp)}, van ends at local {end}, yaw {_van.transform.eulerAngles.y:F0}, sudden stops {hits}; " +
             $"frames {frames}, avg {sum / Mathf.Max(1, frames):F2} ms ({1000.0 * frames / Mathf.Max(1f, (float)sum):F0} fps), worst {worst:F1} ms");
        yield return Shot("23_parked_back_inside");
        // out of the seat (E again = GetOut)
        typeof(GreyboxVanSeat).GetMethod("GetOut", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)?.Invoke(Seat, null);
        yield return new WaitForSecondsRealtime(1f);
        Line($"out of the seat: driving {Seat.Driving}, pawn at local {Local(_pawn.Position)}");
    }

    // ------------------------------------------------------------------ cargo doors: E offers them from the floor, not from the roof
    private IEnumerator CargoDoors()
    {
        var cargo = _van.GetComponent<GreyboxVanCargo>();
        if (cargo == null) { Line("cargo: no GreyboxVanCargo"); yield break; }
        foreach (var (name, local) in new[] { ("floor behind the van", new Vector3(0f, 0f, -3.6f)), ("floor at the sliding door", new Vector3(1.9f, 0f, -0.25f)),
                                              ("roof, rear end", new Vector3(0f, 2.75f, -2.6f)), ("roof, over the sliding door", new Vector3(0.7f, 2.75f, -0.3f)) })
        {
            _pawn.Teleport(_van.transform.TransformPoint(local), _van.transform.eulerAngles.y);
            yield return new WaitForSecondsRealtime(0.8f);
            Line($"cargo: {name}: pawn van-local {_van.transform.InverseTransformPoint(_pawn.Position)}, NearestDoor {cargo.NearestDoor(_pawn.Position)}");
        }
    }

    // ------------------------------------------------------------------ fps
    private IEnumerator Fps()
    {
        foreach (var v in Views)
        {
            Stand(v.x, v.z, v.lx, v.lz, v.pitch);
            yield return new WaitForSecondsRealtime(1.0f);
            yield return Measure(v.name);
        }
        _lockYaw = float.NaN;
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
        Line($"  fps [{label}] {frames / 2.5f:F0} fps, frame avg {sum / frames:F2} ms, worst {max:F1} ms");
    }
}
