using System.Collections;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Capture → delivery stage A: the table part of the map loop, driven by this same real-input driver (virtual
    /// Mouse/Keyboard into the real OperationTableView): a captured NPC already lies on the table (admitted by the
    /// capture bridge); step up with E (PREP view), close the straps by clicks (they also cut his zip ties), take the
    /// scalpel (OPERATION view), one belly cut, snip the left kidney's cords, pull it out with the hands and lay it on the
    /// tray, then look at its card. The capture scenario driver (Capture/CaptureScenarioDriver) starts it and reads the
    /// result.</summary>
    public sealed partial class OperationNetworkProbe
    {
        /// <summary>Evidence folder override for runs started by another driver (null: the default stage1_v4 folder).</summary>
        public static string EvidenceRoot;
        /// <summary>Grade shown on the organ card of the kidney laid on the tray (capture-kidney), -1 if not seen.</summary>
        public static int LastCardGrade = -1;

#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator CaptureKidney()
        {
            LastCardGrade = -1;
            Check(table.AdmissionMode && table.HasPatient && S.onTable, "a captured patient lies on the base table (admission mode)");
            yield return WaitFor(() => S.aligned, 3f, "the magnet snap has aligned him");
            yield return EnterTable(); Shot("cd_09a_prep_view");
            for (int i = 0; i < OperationStraps.Count(table.Tuning); i++) Check(StrapOnScreen(i), "PREP view: strap " + i + " (" + OperationText.Straps[i] + ") on screen");
            yield return Straps(true); Shot("cd_09b_straps_closed");
            Check(view.CameraMode == TableCamera.Prep, "straps were clicked in the PREP view");
            Check(OperationStraps.AllClosed(S, table.Tuning), "all straps closed by clicks");
            yield return CutShared(OperationAbdomenGeometry.ZoneGuide, false, true);
            Check(view.CameraMode == TableCamera.Operation, "the cut was made in the OPERATION view");
            yield return Snip(0, true);
            yield return Pull(0, 0.9f, true);
            yield return new WaitForSeconds(0.4f);
            var organ = S.organs[0];
            Check(organ.removed, "left kidney extracted with real input");
            // Hover it on the tray: its card shows the final grade.
            OperationPhysicalItem kidney = null;
            foreach (var item in table.ServerItems) if (item != null && item.IsOrgan && item.OrganIndex == 0) kidney = item;
            if (kidney != null)
            {
                yield return AimAt(t => t.kind == TargetKind.Item, new[] { kidney.transform.position + table.transform.up * 0.02f, kidney.transform.position }, "kidney on the tray");
                yield return new WaitForSeconds(0.3f);
                Shot("cd_09c_organ_card");
                if (view.Current.item != null && view.Current.item.IsOrgan) LastCardGrade = view.Current.item.Grade;
                Check(LastCardGrade >= 0, "the kidney's card is shown (grade " + (LastCardGrade >= 0 ? OperationText.Tier(LastCardGrade) : "-") + ")");
            }
            else Check(false, "the extracted kidney exists as an item");
            yield return Tap(Key.Escape);
            yield return new WaitForSeconds(table.Tuning.cameraBlendSeconds + 0.1f);
        }
#endif
    }
}
