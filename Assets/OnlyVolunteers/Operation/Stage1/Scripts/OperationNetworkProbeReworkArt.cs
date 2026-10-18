using System.Collections;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Evidence for the v03 art integration (Claude 2026-10-18), real input in the approved dev scene: syringe
    /// v02 mid-draw in the skin, BLOOD-BAG v05 at 0 / ~50 / 100 %, the open belly (Organs_v03 + OperationAbdomen_v03) from
    /// the table camera and in 3/4, and the turned-over patient (closed back: no hole through it).</summary>
    public sealed partial class OperationNetworkProbe
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator ClArtV03()
        {
            Check(table.Tuning.anatomyV03, "v03 anatomy is active in the stage-1 tuning");
            yield return TableHome();
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            yield return CarryPatientOntoTable(); yield return new WaitForSeconds(0.6f);
            yield return EnterTable(); yield return Straps(true);
            yield return Inject(2f, "art v03");
            var up = table.transform.up; var fwd = table.transform.forward; var right = table.transform.right;
            // ---- syringe v02 mid-draw ----
            yield return Select(Key.Digit3, ToolSlot.Blood);
            yield return AimBody(t => t.ArmSide >= 0, new[] { BodyPart.ArmR, BodyPart.ArmL, BodyPart.ShoulderR }, "arm for blood");
            lmb = true; PushMouse();
            float end = Time.time + 2.3f; while (Time.time < end) { PushMouse(); yield return null; }
            var syringe = table.ToolOf(ToolSlot.Blood);
            Shot("art_01_syringe_mid_draw_tablecam");
            if (syringe != null) ClOverview("art_01b_syringe_mid_draw_close", syringe.transform.position + up * 0.16f - fwd * 0.12f + right * 0.1f, syringe.transform.position + syringe.transform.up * 0.05f);
            Check(syringe != null && syringe.Fill > 0.3f && syringe.Fill < 0.7f, "syringe about half full mid-draw (" + (syringe != null ? syringe.Fill.ToString("F2") : "-") + ")");
            end = Time.time + 2.6f; while (Time.time < end) { PushMouse(); yield return null; }
            lmb = false; PushMouse(); yield return Frames(3);
            // ---- bag v05: 0 % (empty slots), ~50 % mid-transfer, 100 % sealed ----
            var bagPose = table.BagPose(0);
            Vector3 trayEye = bagPose.position + up * 0.42f - fwd * 0.05f + right * 0.06f;
            ClOverview("art_02a_bags_empty_0", trayEye, bagPose.position);
            yield return AimAt(t => t.kind == TargetKind.BloodBag && t.index == 0, new[] { bagPose.position + bagPose.up * 0.02f, bagPose.position }, "empty bag 0");
            yield return Click();
            yield return MoveTo(new Vector2(60f, 60f), 0.08f); // off the bag: no hover tint in the evidence
            yield return new WaitForSeconds(table.Tuning.bloodTransferSeconds * 0.5f + 0.05f);
            ClOverview("art_02b_bag_transfer_50", trayEye, bagPose.position);
            Shot("art_02c_bag_transfer_tablecam");
            yield return new WaitForSeconds(table.Tuning.bloodTransferSeconds + 0.6f);
            ClOverview("art_02d_bag_sealed_100", trayEye, bagPose.position);
            // ---- open belly (top camera + 3/4) ----
            yield return Select(Key.Digit4, ToolSlot.Scalpel);
            yield return WaitFor(() => view.CameraMode == TableCamera.Operation, 1f, "scalpel opens the OPERATION view");
            yield return CutShared(OperationAbdomenGeometry.ZoneGuide, false, true);
            yield return MoveTo(new Vector2(40f, 40f), 0.1f); yield return new WaitForSeconds(0.4f);
            Shot("art_03_open_belly_tablecam");
            var zone = table.Abdomen.ZonePose;
            ClOverview("art_03b_open_belly_34", zone.position + up * 0.45f + right * 0.35f + fwd * 0.25f, zone.position);
            Check(S.zoneOpened, "the belly is open");
            for (int i = 0; i < 3; i++)
            {
                var organ = OrganInBody(i);
                Check(organ != null, "organ " + i + " (" + OperationText.Organs[i] + ") shown in the body at its socket, " + (organ != null ? (LargestSide(organ) * 100f).ToString("F1") : "-") + " cm");
            }
            yield return Tap(Key.Escape); yield return new WaitForSeconds(0.6f);
            // ---- turned over: the back must be solid (render-only fixture: the patient rotated 180 deg about his length) ----
            var patient = table.PatientObject.transform;
            Quaternion keep = patient.rotation; Vector3 keepPos = patient.position;
            patient.rotation = Quaternion.AngleAxis(180f, patient.forward) * patient.rotation;
            patient.position = keepPos + up * 0.25f;
            ClOverview("art_04_turned_over_back", zone.position + up * 0.75f + right * 0.15f, zone.position);
            ClOverview("art_04b_turned_over_back_34", zone.position + up * 0.55f + right * 0.45f - fwd * 0.3f, zone.position);
            patient.SetPositionAndRotation(keepPos, keep);
            yield return Frames(2);
        }
#endif
    }
}
