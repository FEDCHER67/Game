using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Claude rework of G35, item 5 (Fedya 2026-10-18): an organ is the same size in the body, in the hand and on
    /// the tray (and dropped). Measures the largest side (world metres, along the model's own axes) of the visible organ
    /// in the open belly and of the physical item that comes out of it, with real input in the approved v02 dev scene.</summary>
    public sealed partial class OperationNetworkProbe
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public static float LargestSide(Transform root) => OperationOrganSize.LargestSide(root);

        private Transform OrganInBody(int organ)
        {
            int k = 0;
            foreach (var t in table.PatientObject.GetComponentsInChildren<Transform>(true))
                if (t.name == "Organ" && t.gameObject.activeInHierarchy)
                {
                    // OperationPresentation builds the sites in organ order (0 left kidney, 1 right kidney, 2 liver).
                    if (Vector3.Distance(t.position, table.OrganPosition(organ)) < 0.05f) return t;
                    k++;
                }
            return null;
        }

        private OperationPhysicalItem ItemOf(int organ)
        {
            foreach (var item in table.ServerItems) if (item != null && item.IsOrgan && item.OrganIndex == organ) return item;
            return null;
        }

        private IEnumerator ClOrganScale()
        {
            yield return TableHome();
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            yield return CarryPatientOntoTable(); yield return new WaitForSeconds(0.6f);
            yield return EnterTable(); yield return Straps(true);
            yield return Inject(2f, "organ scale");
            yield return Select(Key.Digit4, ToolSlot.Scalpel);
            yield return WaitFor(() => view.CameraMode == TableCamera.Operation, 1f, "the scalpel opens the OPERATION view");
            yield return CutShared(OperationAbdomenGeometry.ZoneGuide, false, true);
            var body = new float[3];
            for (int i = 0; i < 3; i++)
            {
                var organ = OrganInBody(i);
                body[i] = organ != null ? LargestSide(organ) : 0f;
                Check(body[i] > 0.03f, "organ " + i + " (" + OperationText.Organs[i] + ") in the body: " + (body[i] * 100f).ToString("F1") + " cm");
            }
            Shot("organ_scale_01_in_body");
            foreach (int i in new[] { 0, 2 })
            {
                if (i == 2) yield return CutShared(2, false, true); else yield return Snip(i, true);
                yield return Pull(i, 0.9f, true);
                yield return new WaitForSeconds(0.6f);
                var item = ItemOf(i);
                if (i == 0) Check(S.alive && S.organs[0].deathChance < 0.5f, "the first kidney keeps its chance roll (" + (S.organs[0].deathChance * 100f).ToString("F0") + " %, survived)");
                if (i == 2) { Check(!S.alive && S.deathCause == DeathCause.Extraction && S.organs[2].deathChance >= 1f, "lead decision 2026-10-18: removing the liver kills him at once (chance 100 %)"); Shot("organ_scale_04_dead_after_liver"); }
                if (!Check(item != null, "organ " + i + " came out as a physical item")) continue;
                float tray = LargestSide(item.transform);
                Shot("organ_scale_02_" + i + "_on_tray");
                Check(Mathf.Abs(tray - body[i]) <= body[i] * 0.05f, OperationText.Organs[i] + " on the tray " + (tray * 100f).ToString("F1") + " cm = in the body " + (body[i] * 100f).ToString("F1") + " cm (±5%)");
                // Into the hand: a real click on it.
                yield return Select(Key.Digit1, ToolSlot.Hands);
                yield return AimAt(t => t.kind == TargetKind.Item, new[] { item.transform.position + table.transform.up * 0.02f, item.transform.position }, "organ item " + i);
                yield return Click(); yield return new WaitForSeconds(0.5f);
                bool inHand = item.Holder != null;
                float hand = LargestSide(item.transform);
                Shot("organ_scale_03_" + i + "_in_hand");
                Check(inHand && Mathf.Abs(hand - body[i]) <= body[i] * 0.05f, OperationText.Organs[i] + " in the hand " + (hand * 100f).ToString("F1") + " cm = in the body (±5%)" + (inHand ? "" : " [not picked]"));
                float definition = item.World.Definition != null ? item.World.Definition.WorldModelSize : 0f;
                Check(Mathf.Abs(definition - body[i]) <= body[i] * 0.05f, "its inventory/drop size (ItemDefinition " + item.World.Definition?.name + " " + (definition * 100f).ToString("F1") + " cm) = in the body (±5%)");
                yield return RightClick(); yield return new WaitForSeconds(0.6f); // back onto the tray
            }
            yield return Tap(Key.Escape); yield return new WaitForSeconds(0.4f);
        }
#endif
    }
}
