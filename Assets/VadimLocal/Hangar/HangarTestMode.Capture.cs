using System.Collections;
using System.IO;
using System.Linq;
using KinematicCharacterController.Examples;
using OnlyVolunteers.Capture.V2;
using OnlyVolunteers.Characters.Npc;
using OnlyVolunteers.Map;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using Kind = OnlyVolunteers.Characters.Npc.NpcRagdollProfile.Kind;

/// <summary>HangarTestMode "capture" (V2 capture phase 1, 31.10): a short scripted run of the slap, the out-cold face, the
/// six grab points, a drag, waking in the hands, the re-slap, the E throw into the van (rear doors and sliding door), the
/// seat and the belt, then the cling: slow mouse must fail, fast flicks must tear him off, Q on the hands lets go, and
/// the escape meter. Witness-camera shots (960 x 540) and "CHECK ... PASS/FAIL" lines in log.txt.</summary>
public sealed partial class HangarTestMode
{
    private CaptureV2Hands _v2;
    private Vector3 _walkTo;
    private bool _walking;
    private float _walkPitch = 30f;
    private Camera _witness;
    private RenderTexture _wrt;
    private int _pass, _fail;
    private static float _collarLift = 0.8f;

    private void Update()
    {
        if (!_walking || _v2 == null || _v2.Kcc == null) return;
        Vector3 flat = _walkTo - _pawn.Position;
        flat.y = 0f;
        float yaw = Mathf.Atan2(flat.x, flat.z) * Mathf.Rad2Deg;
        if (_v2.HeldNpc == null || _v2.HeldNpc.Current != CaptureV2Npc.Mode.Clinging) _v2.SetView(yaw, _walkPitch);
        float camYaw = _v2.ViewYaw;
        Vector3 local = Quaternion.Euler(0f, -camYaw, 0f) * (flat.sqrMagnitude > 1e-4f ? flat.normalized : Vector3.zero);
        var inputs = new PlayerCharacterInputs
        {
            MoveAxisForward = Mathf.Clamp(local.z, -1f, 1f),
            MoveAxisRight = Mathf.Clamp(local.x, -1f, 1f),
            CameraRotation = Quaternion.Euler(0f, camYaw, 0f),
            CrouchUp = true,
        };
        if (flat.magnitude < 0.3f)
        {
            inputs.MoveAxisForward = 0f;
            inputs.MoveAxisRight = 0f;
            _walking = false;
        }
        _v2.Kcc.Character.SetInputs(ref inputs);
    }

    private void Check(string what, bool ok, string detail = "")
    {
        if (ok) _pass++; else _fail++;
        Line($"CHECK {(ok ? "PASS" : "FAIL")} {what}{(detail.Length > 0 ? " (" + detail + ")" : "")}");
    }

    private IEnumerator WShot(string name, Vector3 from, Vector3 at)
    {
        if (_witness == null)
        {
            var go = new GameObject("capture test witness camera");
            _witness = go.AddComponent<Camera>();
            if (Camera.main != null)
            {
                _witness.CopyFrom(Camera.main);
                var src = Camera.main.GetUniversalAdditionalCameraData();
                var dst = _witness.GetUniversalAdditionalCameraData();
                dst.renderPostProcessing = src.renderPostProcessing;
                dst.antialiasing = src.antialiasing;
            }
            _witness.fieldOfView = 55f;
            _witness.enabled = false;
            _wrt = new RenderTexture(960, 540, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 };
            _wrt.Create();
        }
        yield return null; // no WaitForEndOfFrame: it may never resume in -batchmode
        _witness.transform.SetPositionAndRotation(from, Quaternion.LookRotation(at - from));
        _witness.targetTexture = _wrt;
        _witness.aspect = 16f / 9f;
        _witness.Render();
        var active = RenderTexture.active;
        RenderTexture.active = _wrt;
        var tex = new Texture2D(960, 540, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, 960, 540), 0, 0);
        tex.Apply();
        RenderTexture.active = active;
        File.WriteAllBytes(Path.Combine(_out, "cap_" + name + ".png"), tex.EncodeToPNG());
        Destroy(tex);
        Line("shot cap_" + name);
    }

    private static IEnumerator Until(System.Func<bool> done, float seconds)
    {
        float end = Time.realtimeSinceStartup + seconds;
        while (!done() && Time.realtimeSinceStartup < end) yield return null;
    }

    private IEnumerator WalkTo(Vector3 world, float seconds)
    {
        yield return TurnTo(world, _walkPitch);
        _walkTo = world;
        _walking = true;
        float end = Time.realtimeSinceStartup + seconds;
        while (_walking && Time.realtimeSinceStartup < end) yield return null;
        _walking = false;
    }

    // ------------------------------------------------------------------ the run
    private IEnumerator CaptureTest()
    {
        _lockYaw = float.NaN;
        yield return Until(() => CaptureV2Rig.Instance != null && CaptureV2Rig.Instance.Hands != null && CaptureV2Rig.Instance.Van != null, 15f);
        var rig = CaptureV2Rig.Instance;
        Check("V2 rig installed at runtime (hands, van)", rig != null && rig.Hands != null && rig.Van != null);
        if (rig == null || rig.Hands == null || rig.Van == null) yield break;
        _v2 = rig.Hands;
        _v2.ScriptDriven = true;
        _v2.Grabber.ScriptDriven = true;
        rig.Tuning.AutoCling = false;
        CaptureV2Van van = rig.Van;
        GreyboxVanCargo cargo = van.Cargo;
        if (!cargo.DoorOpen(0)) cargo.ToggleDoor(0);
        if (!cargo.DoorOpen(1)) cargo.ToggleDoor(1);
        yield return new WaitForSecondsRealtime(1.5f);
        Line($"van: {van.Seats} seats, slide door {cargo.Slide?.Openness:0.00}, rear {cargo.RearLeft?.Openness:0.00}");
        var npcs = GreyboxNpc.All.Where(n => n != null && n.isActiveAndEnabled).OrderBy(n => n.name).ToList();
        if (npcs.Count < 3) { Line("need 3 NPCs, found " + npcs.Count); yield break; }

        // ===== A: slap, out cold, the six grab points, drag by the collar, wake, re-slap, throw through the rear doors
        CaptureV2Npc a = rig.Ensure(npcs[0]);
        yield return Slap(a, new Vector3(-14f, 0f, -2f), true);
        yield return GrabTypes(a);
        yield return DragAndThrow(a, GrabPointV2.Collar, World(-4.7f, -2f), 1, true, "A");

        // ===== B: the left leg, through the sliding door (hammer throw)
        CaptureV2Npc b = rig.Ensure(npcs[1]);
        yield return Slap(b, new Vector3(-0.25f, 0f, -12.5f), false, 1f);
        yield return DragAndThrow(b, GrabPointV2.LegLeft, World(-0.25f, -5.0f), 0, false, "B");
        Line($"seats now {van.Occupied}/{van.Seats}");

        // ===== C: the cling (slow fails, fast tears off), Q on the hands, the escape meter
        CaptureV2Npc c = rig.Ensure(npcs[2]);
        yield return Slap(c, new Vector3(8f, 0f, -10f), false);
        yield return ClingRound(c);

        if (_witness != null) Destroy(_witness.gameObject);
        Line($"CAPTURE RESULT: {_pass} pass, {_fail} fail; sounds played {CaptureV2Sounds.Played}");
    }

    // Puts 'npc' standing at hangar-local 'spot', the player 1.3 m in front, Q: the wind-up, the spin, the sack drop.
    private IEnumerator Slap(CaptureV2Npc npc, Vector3 spot, bool shots, float charge = 0f)
    {
        yield return Until(() => npc.Npc.State == NpcState.Free, 8f);
        Vector3 at = World(spot.x, spot.z);
        npc.TestPlaceStanding(at, 0f);
        npc.TestHold(true);
        Vector3 front = npc.transform.forward;
        _pawn.Teleport(at + front * 1.3f, Quaternion.LookRotation(-front).eulerAngles.y);
        yield return null;
        yield return null;
        _v2.Aim(at + Vector3.up * 1.3f);
        yield return null;
        _v2.ScriptSlap(charge);
        Check($"{npc.name}: LMB wind-up started (charge {charge:0.0}), he freezes", _v2.WindingUp && npc.Current == CaptureV2Npc.Mode.Frozen, npc.Current.ToString());
        float pressAt = Time.time;
        yield return Until(() => npc.Current == CaptureV2Npc.Mode.Spinning, 3f);
        Check($"{npc.name}: smack lands {Time.time - pressAt:0.00} s after the press (spin)", npc.Current == CaptureV2Npc.Mode.Spinning);
        if (shots)
        {
            yield return new WaitForSecondsRealtime(0.12f);
            Vector3 side = Vector3.Cross(Vector3.up, front);
            yield return WShot("01_slap_spin", at + side * 3.2f + front * 1.0f + Vector3.up * 1.6f, at + Vector3.up * 1.0f + front * 0.5f);
        }
        yield return Until(() => npc.Current == CaptureV2Npc.Mode.KnockedOut, 2f);
        float wantKo = 2.5f * (1f + CaptureV2Rig.Instance.Tuning.ChargeKnockOutGain * charge);
        Check($"{npc.name}: down as the ragdoll, out cold {npc.LastKnockOut:0.00} s (want {wantKo:0.00})", npc.Current == CaptureV2Npc.Mode.KnockedOut && npc.Npc.Ragdoll != null && npc.Npc.Ragdoll.Active && Mathf.Abs(npc.LastKnockOut - wantKo) < 0.01f);
        if (charge > 0.5f)
        {
            Vector3 v = npc.Npc.Ragdoll.MainBody != null ? npc.Npc.Ragdoll.MainBody.linearVelocity : Vector3.zero;
            Check($"{npc.name}: full charge: he flies a little ({new Vector2(v.x, v.z).magnitude:0.0} m/s along, {v.y:0.0} up)", new Vector2(v.x, v.z).magnitude > 2f);
            yield return new WaitForSecondsRealtime(0.15f);
            Vector3 c = npc.Center;
            yield return WShot("01b_charged_fly", c + Vector3.Cross(Vector3.up, front) * 3.5f + Vector3.up * 1.4f, c);
        }
        npc.Npc.StunLeft = 8f; // the test grabs at leisure; the drag below sets the wake-up
        yield return new WaitForSecondsRealtime(1.0f);
        if (shots)
        {
            // from where his face looks (his belly side), else low from the side when he lies face down
            NpcRagdoll rd = npc.Npc.Ragdoll;
            Vector3 head = rd.Landmark(NpcLandmark.Head);
            Vector3 look = rd.Front;
            if (look.y < -0.35f) look = Vector3.Cross(Vector3.up, rd.Landmark(NpcLandmark.Head) - rd.Landmark(NpcLandmark.Pelvis)).normalized + Vector3.up * 0.15f;
            yield return WShot("02_ko_face", head + look.normalized * 0.85f + Vector3.up * 0.3f, head);
            yield return WShot("02b_ko_wide", head + look.normalized * 2.2f + Vector3.up * 1.2f, head);
        }
    }

    // A grab point's aim target on the lying ragdoll.
    private static Vector3 AimPoint(NpcRagdoll r, GrabPointV2 g)
    {
        NpcRagdollProfile p = r.Profile;
        int head = p.IndexOf(Kind.Head), chest = p.IndexOf(Kind.Chest);
        return g switch
        {
            GrabPointV2.Head => r.PartCenter(head),
            GrabPointV2.Collar => CollarPoint(r, chest, head),
            GrabPointV2.ArmLeft => r.PartCenter(p.IndexOf(Kind.ForeArm, NpcSide.Left)),
            GrabPointV2.ArmRight => r.PartCenter(p.IndexOf(Kind.ForeArm, NpcSide.Right)),
            GrabPointV2.LegLeft => r.PartCenter(p.IndexOf(Kind.Calf, NpcSide.Left)),
            GrabPointV2.LegRight => r.PartCenter(p.IndexOf(Kind.Calf, NpcSide.Right)),
            _ => r.CenterOfMass,
        };
    }

    // The chest's top band along the spine (NpcRagdoll's collar handle; lower on the chest is the belly).
    private static Vector3 CollarPoint(NpcRagdoll r, int chest, int head)
    {
        Vector3 c = r.PartCenter(chest);
        Vector3 up = (r.PartCenter(head) - c).normalized;
        r.CapsuleSegment(chest, out Vector3 a, out Vector3 b, out float radius);
        float top = Mathf.Max(Vector3.Dot(a - c, up), Vector3.Dot(b - c, up)) + radius;
        return c + up * top * _collarLift;
    }

    // Turns the view the way a hand would (about 140 deg/s), so a held body follows instead of the hold snapping.
    private IEnumerator TurnTo(Vector3 world, float pitch)
    {
        Vector3 flat = world - _pawn.Position;
        flat.y = 0f;
        if (flat.sqrMagnitude < 1e-4f) yield break;
        float yaw0 = _v2.ViewYaw, pitch0 = _v2.ViewPitch;
        float yaw1 = Mathf.Atan2(flat.x, flat.z) * Mathf.Rad2Deg;
        float turn = Mathf.DeltaAngle(yaw0, yaw1);
        float seconds = Mathf.Max(0.3f, Mathf.Abs(turn) / 140f);
        for (float t = 0f; t < seconds; t += Time.deltaTime)
        {
            float u = Mathf.SmoothStep(0f, 1f, t / seconds);
            _v2.SetView(yaw0 + turn * u, Mathf.Lerp(pitch0, pitch, u));
            yield return null;
        }
        _v2.SetView(yaw1, pitch);
    }

    // Stand 1 m off the point (several directions), look at it, grab; true when the hold classifies as 'want'.
    private IEnumerator TryGrab(CaptureV2Npc npc, GrabPointV2 want, System.Action<bool> result)
    {
        NpcRagdoll r = npc.Npc.Ragdoll;
        bool ok = false;
        for (int attempt = 0; attempt < 6 && !ok; attempt++)
        {
            if (_v2.Grabber.IsHolding) _v2.Grabber.ScriptRelease();
            yield return null;
            Vector3 point = AimPoint(r, want);
            Vector3 pelvis = r.Landmark(NpcLandmark.Pelvis);
            Vector3 out0 = point - pelvis;
            out0.y = 0f;
            if (want == GrabPointV2.Collar || out0.sqrMagnitude < 0.01f) out0 = Vector3.Cross(Vector3.up, r.Landmark(NpcLandmark.Head) - pelvis);
            out0 = Quaternion.Euler(0f, attempt * (want == GrabPointV2.Collar ? 25f : 60f) * (attempt % 2 == 0 ? 1f : -1f), 0f) * out0.normalized;
            _collarLift = 0.8f + 0.07f * attempt;
            Vector3 feet = new Vector3(point.x, _hangar.position.y + 0.05f, point.z) + out0 * 1.0f;
            _pawn.Teleport(feet, Quaternion.LookRotation(-out0).eulerAngles.y);
            yield return null;
            yield return null;
            _v2.Aim(AimPoint(r, want));
            yield return new WaitForFixedUpdate();
            _v2.Aim(AimPoint(r, want));
            bool held = _v2.ScriptLmbGrab();
            yield return null;
            ok = held && _v2.HeldNpc == npc && _v2.HeldPoint == want;
            if (!ok) Line($"  grab try {attempt} for {want}: holding {held}, classified {_v2.HeldPoint}");
        }
        result(ok);
    }

    private IEnumerator GrabTypes(CaptureV2Npc npc)
    {
        foreach (GrabPointV2 g in new[] { GrabPointV2.Head, GrabPointV2.Collar, GrabPointV2.ArmLeft, GrabPointV2.ArmRight, GrabPointV2.LegLeft, GrabPointV2.LegRight })
        {
            bool ok = false;
            yield return TryGrab(npc, g, v => ok = v);
            yield return new WaitForSecondsRealtime(0.25f);
            Check($"grab point {g}: classified, speed x{_v2.SpeedScale:0.00}", ok && Mathf.Approximately(_v2.SpeedScale, CaptureV2Rules.SpeedScale(CaptureV2Rig.Instance.Tuning, g)), _v2.HeldPoint.ToString());
            _v2.Grabber.ScriptRelease();
            npc.Npc.StunLeft = Mathf.Max(npc.Npc.StunLeft, 4f);
            yield return new WaitForSecondsRealtime(0.15f);
        }
    }

    private IEnumerator DragAndThrow(CaptureV2Npc npc, GrabPointV2 grab, Vector3 door, int doorIndex, bool reslap, string tag)
    {
        bool ok = false;
        npc.Npc.StunLeft = Mathf.Max(npc.Npc.StunLeft, 4f);
        yield return TryGrab(npc, grab, v => ok = v);
        Check($"{tag}: grabbed by {grab}", ok);
        if (!ok) yield break;
        Vector3 start = _pawn.Position;
        yield return TurnTo(door, _walkPitch);
        Check($"{tag}: still held after turning toward the door", _v2.HeldNpc == npc);
        if (reslap) npc.Npc.StunLeft = 1.3f; // wakes in the hands on the way
        float t0 = Time.time;
        _walkTo = door;
        _walking = true;
        bool carryShot = false;
        float endAt = Time.realtimeSinceStartup + 9f;
        while (_walking && Time.realtimeSinceStartup < endAt && _v2.HeldNpc == npc)
        {
            if (!carryShot && Time.time - t0 > 1.0f)
            {
                carryShot = true;
                Vector3 c = npc.Center;
                Vector3 dir = door - _pawn.Position;
                dir.y = 0f;
                Vector3 side = Vector3.Cross(Vector3.up, dir.normalized);
                yield return WShot($"03_carry_{grab}_{tag}", c + side * 3.4f + Vector3.up * 1.5f - dir.normalized * 0.8f, c + Vector3.up * 0.3f);
            }
            yield return null;
        }
        _walking = false;
        float metres = Vector3.Distance(start, _pawn.Position);
        float speed = metres / Mathf.Max(0.1f, Time.time - t0) / 4.7025f;
        Check($"{tag}: dragged {metres:0.0} m at x{speed:0.00} walk, still held", _v2.HeldNpc == npc && metres > 6f, $"state {npc.Current}, meter {npc.Meter:0.00}");
        if (reslap)
            Check($"{tag}: woke up in the hands, meter rising", npc.Current == CaptureV2Npc.Mode.Awake && npc.Meter > 0.01f, $"{npc.Current}, meter {npc.Meter:0.00}");
        yield return new WaitForSecondsRealtime(0.2f);
        Check($"{tag}: E offered at the {(doorIndex == 0 ? "sliding door" : "rear doors")}", _v2.ThrowOffered);
        if (reslap && npc.Current == CaptureV2Npc.Mode.Awake)
        {
            _v2.ScriptSlap();
            yield return Until(() => npc.Current == CaptureV2Npc.Mode.KnockedOut, 1.5f);
            Check($"{tag}: re-slap while dragging: out cold {npc.LastKnockOut:0.0} s (ladder 2nd)", npc.Current == CaptureV2Npc.Mode.KnockedOut && Mathf.Approximately(npc.LastKnockOut, 1.5f));
            yield return new WaitForSecondsRealtime(0.3f);
        }
        bool thrown = _v2.ScriptThrow();
        Check($"{tag}: E throw starts ({npc.ThrowStyle})", thrown);
        if (!thrown) yield break;
        yield return new WaitForSecondsRealtime(0.32f);
        Vector3 side2 = Vector3.Cross(Vector3.up, (door - _pawn.Position).normalized);
        if (tag == "A" || tag == "B")
            yield return WShot($"04_swing_{npc.ThrowStyle}_{tag}", _pawn.Position + side2 * 4.2f + Vector3.up * 1.8f - (door - _pawn.Position).normalized * 1.5f, _pawn.Position + Vector3.up * 1.3f);
        yield return Until(() => npc.Current == CaptureV2Npc.Mode.Seated || npc.Current == CaptureV2Npc.Mode.KnockedOut && npc.LastBounced, 4f);
        Check($"{tag}: landed in a seat (seat {npc.ReservedSeat}, landing {npc.LandingVariant}, face {npc.LastFace})",
            npc.Current == CaptureV2Npc.Mode.Seated && npc.Npc.State == NpcState.CargoSeated && npc.Npc.InCargo && npc.Npc.SeatBelted, $"{npc.Current} / {npc.Npc.State}");
        yield return new WaitForSecondsRealtime(0.9f);
        Check($"{tag}: belt clack", npc.BeltOn);
        // the shot into the bay through that door
        Vector3 seat = CaptureV2Rig.Instance.Van.SeatWorld(Mathf.Max(0, npc.ReservedSeat));
        Vector3 outside = CaptureV2Rig.Instance.Van.DoorwayWorld(doorIndex, 1.3f) + CaptureV2Rig.Instance.Van.Outward(doorIndex) * 1.6f;
        yield return WShot($"05_seated_belt_{tag}", outside, seat + Vector3.up * 0.6f);
        yield return new WaitForSecondsRealtime(1.5f);
        Check($"{tag}: still seated, no escape through the open door", npc.Npc.State == NpcState.CargoSeated);
    }

    private IEnumerator ClingRound(CaptureV2Npc npc)
    {
        bool ok = false;
        yield return TryGrab(npc, GrabPointV2.ArmRight, v => ok = v);
        Check("C: grabbed by the right arm", ok);
        if (!ok) yield break;
        npc.Npc.StunLeft = 0.25f;
        yield return Until(() => npc.Current == CaptureV2Npc.Mode.Awake, 2f);
        Check("C: awake in the hands", npc.Current == CaptureV2Npc.Mode.Awake);
        // a post next to his free (left) hand
        NpcRagdoll r = npc.Npc.Ragdoll;
        int fore = r.Profile.IndexOf(Kind.ForeArm, NpcSide.Left);
        r.CapsuleSegment(fore, out Vector3 e1, out Vector3 e2, out _);
        Vector3 pel = r.Landmark(NpcLandmark.Pelvis);
        Vector3 hand = Vector3.Distance(e1, pel) > Vector3.Distance(e2, pel) ? e1 : e2;
        Vector3 outDir = hand - pel;
        outDir.y = 0f;
        outDir = outDir.sqrMagnitude > 1e-4f ? outDir.normalized : Vector3.right;
        var post = new GameObject("capture test post");
        float floor = _hangar.position.y;
        post.transform.position = new Vector3(hand.x, floor + 0.75f, hand.z) + outDir * 0.18f;
        post.transform.localScale = new Vector3(0.12f, 1.5f, 0.12f);
        var box = post.AddComponent<BoxCollider>();
        post.AddComponent<MeshFilter>().sharedMesh = CaptureV2Rig.Instance.Box;
        post.AddComponent<MeshRenderer>().sharedMaterial = CaptureV2Rig.Instance.Buckle;
        yield return new WaitForFixedUpdate();
        bool clung = npc.TryCling(box);
        yield return new WaitForSecondsRealtime(0.3f);
        Check("C: clings to the post", clung && npc.Current == CaptureV2Npc.Mode.Clinging);
        Vector3 side = Vector3.Cross(Vector3.up, outDir);
        yield return WShot("08_cling_post", npc.Center + side * 3f + Vector3.up * 1.6f - outDir * 1.2f, npc.Center);
        float Off()
        {
            Vector3 f = _v2.View.transform.forward, to = npc.ClingAnchor - _v2.View.transform.position;
            f.y = 0f;
            to.y = 0f;
            return Vector3.Angle(f, to);
        }
        // look away from the post first, so the pull back shows
        _v2.SetView(_v2.ViewYaw + 40f, 20f);
        yield return null;
        float before = Off();
        // slow mouse along the arrow: must fail, and the view is dragged back toward the post
        float slowEnd = Time.realtimeSinceStartup + 2f;
        float maxBar = 0f;
        while (Time.realtimeSinceStartup < slowEnd && npc.Current == CaptureV2Npc.Mode.Clinging)
        {
            _v2.ScriptMouse = _v2.Arrow * 60f;
            maxBar = Mathf.Max(maxBar, npc.YankBar);
            yield return null;
        }
        _v2.ScriptMouse = Vector2.zero;
        float after = Off();
        Check($"C: slow mouse does nothing (bar max {maxBar:0.00}), still clinging", npc.Current == CaptureV2Npc.Mode.Clinging && maxBar < 0.3f);
        Check($"C: the view is dragged back toward the post ({before:0}° -> {after:0}° off it)", after < before - 5f);
        // fast flicks along the arrow: must tear him off
        float fastStart = Time.realtimeSinceStartup;
        int pops = npc.Pops;
        while (Time.realtimeSinceStartup - fastStart < 5f && npc.Pops == pops)
        {
            float ph = Mathf.Repeat(Time.realtimeSinceStartup - fastStart, 0.25f);
            _v2.ScriptMouse = ph < 0.1f ? _v2.Arrow * 1300f : -_v2.Arrow * 350f;
            yield return null;
        }
        _v2.ScriptMouse = Vector2.zero;
        Check($"C: fast flicks tear him off (POP after {Time.realtimeSinceStartup - fastStart:0.0} s)", npc.Pops == pops + 1 && npc.Current == CaptureV2Npc.Mode.Awake);
        yield return WShot("09_pop", npc.Center + side * 3f + Vector3.up * 1.6f - outDir * 1.2f, npc.Center);
        // LMB on his hands while he clings: he lets go, out cold for the next step of the ladder. Forced cling only after
        // the POP stumble has settled (the game's own clings wait ClingCooldown 3 s).
        yield return new WaitForSecondsRealtime(1.5f);
        if (_v2.HeldNpc == npc && npc.Current == CaptureV2Npc.Mode.Awake && npc.TryCling(box))
        {
            yield return new WaitForSecondsRealtime(0.2f);
            int before2 = npc.SlapCount;
            _v2.ScriptSlap();
            yield return Until(() => npc.Current == CaptureV2Npc.Mode.KnockedOut, 1.5f);
            Check($"C: LMB on the hands: lets go, out cold {npc.LastKnockOut:0.0} s", npc.Current == CaptureV2Npc.Mode.KnockedOut && npc.ClingCollider == null &&
                Mathf.Approximately(npc.LastKnockOut, CaptureV2Rules.KnockOut(CaptureV2Rig.Instance.Tuning, before2)));
        }
        else Check("C: LMB on the hands (second cling)", false, $"held {_v2.HeldNpc == npc}, {npc.Current}");
        Destroy(post);
        // the escape meter: keep dragging him awake until he breaks free
        npc.Npc.StunLeft = 0.2f;
        yield return Until(() => npc.Current == CaptureV2Npc.Mode.Awake, 2f);
        float escStart = Time.time;
        Vector3 p0 = _pawn.Position, p1 = p0 + (Quaternion.Euler(0f, 90f, 0f) * outDir) * 5f;
        int escapes = npc.Escapes;
        for (int leg = 0; leg < 8 && npc.Escapes == escapes && _v2.HeldNpc == npc; leg++)
            yield return WalkTo(leg % 2 == 0 ? p1 : p0, 2.5f);
        yield return null;
        Check($"C: escape meter full: breaks free after {Time.time - escStart:0.0} s awake", npc.Escapes == escapes + 1 && _v2.HeldNpc == null, $"meter {npc.Meter:0.00}, {npc.Current}, {npc.Npc.State}");
        _walking = false;
        if (_v2.Grabber.IsHolding) _v2.Grabber.ScriptRelease();
        yield return new WaitForSecondsRealtime(1.2f);
        yield return WShot("10_breaks_free", npc.transform.position + Vector3.up * 2f - outDir * 3.5f, npc.transform.position + Vector3.up * 0.8f);
    }
}
