using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
        Line($"offscreen {Offscreen} (3840x2160 RenderTexture), camera vertical fov {(Camera.main ? Camera.main.fieldOfView : -1f):F1}");
        Line($"start: pawn {Local(_pawn.Position)}, van {Local(_van.transform.position)} yaw {_van.transform.eulerAngles.y:F0}");
        if (mode == "shots" || mode == "all") yield return Shots();
        if (mode == "drive" || mode == "all") yield return Drive();
        if (mode == "fps" || mode == "all") yield return Fps();
        if (mode == "cargo" || mode == "all") yield return CargoDoors();
        if (mode == "shimmer") yield return Shimmer();
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

    // offscreen (Vadim 30.10: tests must not open a window): started with -batchmode the player has no window; the main
    // camera is rendered into a 3840 x 2160 RenderTexture (MSAA 2) and read back. FPS in this mode is offscreen and
    // conservative (each frame waits for the GPU through a 1-pixel read-back).
    private static bool Offscreen => Application.isBatchMode;
    private RenderTexture _rt;
    private Texture2D _px;

    private RenderTexture Rt()
    {
        if (_rt == null) { _rt = new RenderTexture(3840, 2160, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 }; _rt.Create(); }
        return _rt;
    }

    private void RenderOffscreen(Camera cam)
    {
        var prev = cam.targetTexture;
        cam.targetTexture = Rt();
        cam.aspect = 16f / 9f;
        cam.Render();
        cam.targetTexture = prev;
        cam.ResetAspect();
    }

    private IEnumerator Shot(string name, float wait = 1.2f)
    {
        yield return new WaitForSecondsRealtime(wait);
        string f = Path.Combine(_out, name + ".png");
        if (Offscreen)
        {
            yield return null;
            var cam = Camera.main;
            if (cam == null) { Line("no camera for " + name); yield break; }
            RenderOffscreen(cam);
            var active = RenderTexture.active;
            RenderTexture.active = _rt;
            var tex = new Texture2D(_rt.width, _rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, _rt.width, _rt.height), 0, 0);
            tex.Apply();
            RenderTexture.active = active;
            File.WriteAllBytes(f, tex.EncodeToPNG());
            Destroy(tex);
        }
        else
        {
            ScreenCapture.CaptureScreenshot(f);
            yield return new WaitForSecondsRealtime(0.5f);
        }
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
        // texture checks (package 45): floor close, crates, the signs close, the parked gate leaf from outside
        ("19_floor_close", -8f, -6f, -8f, 4f, 40f),
        ("20_crates_left_wall", -20f, -6f, -24.5f, -8f, 15f),
        ("21_pharmacy_sign", -0.6f, 6.5f, -0.6f, 11f, -15f),
        ("22_bay_sign_roller", -16.5f, 1.5f, -16.5f, 7f, -25f),
        ("23_gate_leaf_outside", 33f, -15f, 25.6f, -9f, 2f),
        ("24_pharmacy_shelves", -1f, 13.2f, -1f, 17f, 8f),
        ("25_crate_close", -22.4f, -8.6f, -24.2f, -9.5f, 28f),
        // Vadim's review 30.10: wall close-up (~1 m, the wall fills the screen), wall at 5 m and 15 m, cladding close-up,
        // floor markings close and at eye height
        ("26_wall_close_1m", -12.5f, -16f, -12.5f, -17f, 0f),
        ("27_wall_5m", -12.5f, -12f, -12.5f, -17f, 0f),
        ("28_wall_15m", -12.5f, -2f, -12.5f, -17f, 0f),
        ("29_cladding_close", -10f, 6f, -10f, 7f, 0f),
        ("30_spawn_close", -15f, -10.2f, -15f, -12.7f, 40f),
        ("31_arrow_close", -3f, -6.6f, -3f, -8.5f, 45f),
        ("32_markings_eye", -8f, -4f, -15f, -12.5f, 10f),
    };

    // the room prefabs (30.10): views from the hall and inside at eye height, found from their walls at run time
    private (string name, float x, float z, float lx, float lz, float pitch)[] RoomViews()
    {
        var list = new System.Collections.Generic.List<(string, float, float, float, float, float)>();
        foreach (var n in new[] { "Workshop", "Pharmacy", "Gear" })
        {
            var b = RoomBounds(n, out _);
            if (b.size == Vector3.zero) { Line("room " + n + " not found"); continue; }
            float cx = b.center.x, f = b.min.z, w = b.size.x;
            list.Add(($"40_{n}_from_hall", cx, f - (n == "Workshop" ? 11f : 8f), cx, f + 2f, n == "Workshop" ? 6f : 4f));
            list.Add(($"41_{n}_inside", cx + w * .32f, f + .9f, cx - w * .25f, b.max.z - .4f, 8f));
            list.Add(($"42_{n}_inside_back", cx - w * .3f, b.max.z - 1.2f, cx + w * .2f, f + .5f, 6f));
        }
        return list.ToArray();
    }

    private Bounds RoomBounds(string n, out Transform room)
    {
        room = _hangar.Find("Room_" + n);
        var b = new Bounds();
        if (room == null) return b;
        bool any = false;
        foreach (var r in room.GetComponentsInChildren<Renderer>())
        {
            if (r.bounds.size.y <= 2.5f) continue;
            var lb = new Bounds(Local(r.bounds.center), r.bounds.size); // the hangar is not rotated in the scene (yaw 0)
            if (!any) { b = lb; any = true; } else b.Encapsulate(lb);
        }
        return b;
    }

    private IEnumerator Shots()
    {
        _lockYaw = float.NaN;
        yield return Shot("00_start_view", 0.5f);
        foreach (var v in Views.Concat(RoomViews()))
        {
            Stand(v.x, v.z, v.lx, v.lz, v.pitch);
            yield return Shot(v.name);
        }
        // the van on the workshop lift: put it on the carriages (as if driven in), shoot, put it back
        var wb = RoomBounds("Workshop", out var ws);
        if (ws != null)
        {
            var lift = ws.GetComponentsInChildren<Renderer>().Where(r => r.name.Contains("Lift_Carriage")).Select(r => r.bounds).ToList();
            var rb = _van.GetComponent<Rigidbody>();
            Vector3 p0 = _van.transform.position; Quaternion q0 = _van.transform.rotation;
            Vector3 c = lift.Count > 0 ? lift.Aggregate((a, x) => { a.Encapsulate(x); return a; }).center : _hangar.TransformPoint(wb.center);
            float top = lift.Count > 0 ? lift.Max(x => x.max.y) : _hangar.position.y;
            Line($"lift carriages {lift.Count}, centre {Local(c)}, top {top - _hangar.position.y:F2}");
            rb.linearVelocity = Vector3.zero; rb.angularVelocity = Vector3.zero;
            rb.position = new Vector3(c.x, top + .6f, c.z); rb.rotation = _hangar.rotation;
            _van.transform.SetPositionAndRotation(rb.position, rb.rotation);
            yield return new WaitForSecondsRealtime(2.5f);
            Line($"van on the lift: {Local(_van.transform.position)}, up {_van.transform.up.y:F3}");
            float cx = wb.center.x, f = wb.min.z;
            Stand(cx - 3.5f, f - 6f, cx, f + 4f, 6f);
            yield return Shot("43_van_on_lift_from_hall");
            Stand(cx + wb.size.x * .38f, f + 1.2f, cx, f + 5f, 10f);
            yield return Shot("44_van_on_lift_inside");
            rb.linearVelocity = Vector3.zero; rb.angularVelocity = Vector3.zero;
            rb.position = p0; rb.rotation = q0;
            _van.transform.SetPositionAndRotation(p0, q0);
            yield return new WaitForSecondsRealtime(1f);
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

    // ------------------------------------------------------------------ shimmer: the camera strafes 2 cm per frame in front of a
    // wall / the gate leaf (3, 8, 15 m); consecutive frames are compared offline for crawling or flickering rib lines
    private static readonly (string name, float x, float z, float lx, float lz, float dx, float dz)[] Strafes =
    {
        ("wall_03m", -14f, -14f, -14f, -17f, .02f, 0f),
        ("wall_08m", -14f, -9f, -14f, -17f, .02f, 0f),
        ("wall_15m", -14f, -2f, -14f, -17f, .02f, 0f),
        ("gate_03m", 28.8f, -10.8f, 25.8f, -10.8f, 0f, .02f),
        ("gate_08m", 33.8f, -10.8f, 25.8f, -10.8f, 0f, .02f),
        ("gate_15m", 40.8f, -10.8f, 25.8f, -10.8f, 0f, .02f),
    };

    private IEnumerator Shimmer()
    {
        foreach (var s in Strafes)
            for (int i = 0; i < 7; i++)
            {
                Stand(s.x + s.dx * i, s.z + s.dz * i, s.lx + s.dx * i, s.lz + s.dz * i, 2f);
                yield return Shot($"sh_{s.name}_{i}", i == 0 ? 1.2f : .4f);
            }
        _lockYaw = float.NaN;
    }

    // ------------------------------------------------------------------ fps
    private IEnumerator Fps()
    {
        foreach (var v in Views.Concat(RoomViews()))
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
            if (Offscreen && Camera.main != null)
            {
                RenderOffscreen(Camera.main);
                if (_px == null) _px = new Texture2D(1, 1, TextureFormat.RGB24, false);
                var active = RenderTexture.active;
                RenderTexture.active = _rt;
                _px.ReadPixels(new Rect(0, 0, 1, 1), 0, 0);
                RenderTexture.active = active;
            }
            frames++;
            double dt = Time.unscaledDeltaTime * 1000.0;
            sum += dt;
            if (dt > max) max = dt;
        }
        Line($"  fps{(Offscreen ? " (offscreen 4K)" : "")} [{label}] {frames / 2.5f:F0} fps, frame avg {sum / frames:F2} ms, worst {max:F1} ms");
    }
}
