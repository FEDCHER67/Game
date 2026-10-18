using System.Collections;
using System.Collections.Generic;
using OnlyVolunteers.Network;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    public sealed partial class OperationNetworkProbe
    {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private IEnumerator G35AimStrap(int index)
        {
            var points = new List<Vector3>();
            foreach (var tag in table.GetComponentsInChildren<OperationTargetTag>())
                if (tag.kind == TargetKind.Strap && tag.index == index && tag.TryGetComponent(out Collider collider) && collider.enabled)
                { points.Add(collider.bounds.center); points.AddRange(StrapCandidates(collider.bounds)); }
            yield return AimAt(t => t.kind == TargetKind.Strap && t.index == index, points, "G35 strap " + index);
            Check(aimed, "visible strap " + index + " is targetable by the real cursor");
        }

        private IEnumerator G35Straps()
        {
            yield return TableHome();
            yield return Tap(Key.F10); yield return new WaitForSeconds(0.6f);
            yield return Tap(Key.F9); yield return new WaitForSeconds(0.8f);
            yield return EnterTable(); yield return Straps(true);
            var slots = new[] { ToolSlot.Hands, ToolSlot.Anesthesia, ToolSlot.Blood, ToolSlot.Scalpel };
            var hotkeys = new[] { Key.Digit1, Key.Digit2, Key.Digit3, Key.Digit4 };
            for (int tool = 0; tool < slots.Length; tool++)
            {
                yield return Select(hotkeys[tool], slots[tool]);
                if (view.CameraMode != TableCamera.Prep) yield return Tap(Key.Tab);
                yield return new WaitForSeconds(0.5f);
                bool torso = S.restraints[4], right = S.restraints[1];
                yield return G35AimStrap(1); yield return Click(); yield return new WaitForSeconds(0.35f);
                Check(S.restraints[1] != right && S.restraints[4] == torso, slots[tool] + ": PREP right-arm click toggles only the right arm");
                yield return G35AimStrap(1); yield return Click(); yield return new WaitForSeconds(0.35f);
                Check(S.restraints[1] == right && S.restraints[4] == torso, slots[tool] + ": PREP right arm closes again without toggling torso");
                yield return AimBody(t => t.kind == TargetKind.Body, new[] { BodyPart.ShoulderR }, "bare right shoulder");
                Check(aimed && view.Current.target.kind != TargetKind.Strap, slots[tool] + ": bare shoulder offers no strap action");
                yield return Click(); yield return new WaitForSeconds(0.2f);
                Check(S.restraints[1] == right && S.restraints[4] == torso, slots[tool] + ": body click never changes a strap");
                yield return Tap(Key.Tab); yield return new WaitForSeconds(0.5f);
                var strap = table.StrapTransform(1);
                var renderer = strap.GetComponentInChildren<Renderer>();
                yield return MoveTo(Scr(renderer.bounds.center), 0.15f);
                Check(view.CameraMode == TableCamera.Operation && view.Current.target.kind != TargetKind.Strap, slots[tool] + ": OPERATION never offers a strap target");
                yield return Click(); yield return new WaitForSeconds(0.2f);
                Check(S.restraints[1] == right && S.restraints[4] == torso, slots[tool] + ": OPERATION click cannot unbuckle straps");
                Shot("g35_straps_" + slots[tool]);
                yield return Tap(Key.Tab); yield return new WaitForSeconds(0.45f);
            }
            for (int i = 0; i < 5; i++)
            {
                bool precise = false;
                foreach (var tag in table.GetComponentsInChildren<OperationTargetTag>())
                    if (tag.kind == TargetKind.Strap && tag.index == i && tag.TryGetComponent(out MeshCollider collider) && collider.enabled)
                    {
                        // Rework: the collider uses the baked READABLE copy of the visible strap mesh (same triangles).
                        var visible = collider.transform.parent.GetComponent<MeshFilter>().sharedMesh;
                        precise |= !collider.convex && (collider.sharedMesh == visible ||
                            (collider.sharedMesh.isReadable && collider.sharedMesh.name == visible.name + OperationQueryMeshes.Suffix && collider.sharedMesh.vertexCount == visible.vertexCount));
                    }
                Check(precise, "strap " + i + " collider follows its visible mesh triangles");
            }
            yield return Tap(Key.Escape);
        }

        private IEnumerator G35Brake()
        {
            yield return TableHome(); yield return Tap(Key.F10); yield return new WaitForSeconds(0.8f);
            Vector3 before = table.transform.position;
            yield return CarryPatientOntoTable(); yield return new WaitForSeconds(0.7f);
            Check(Vector3.Distance(before, table.transform.position) < 0.02f, "braked gurney does not roll or kick during physical patient loading");
            var body = table.GetComponent<NetworkPhysicsBody>();
            Check(body.Body.mass >= 160f, "gurney is heavier (at least 160 kg)");
            Teleport(TableFoot(new Vector3(-1.1f, 0f, -0.65f))); yield return new WaitForSeconds(0.4f);
            LookAt(table.transform.position + table.transform.up * 0.45f); yield return Frames(4);
            yield return Button(true); yield return new WaitForSeconds(0.4f);
            Check(body.HasHolder, "deliberate real LMB grab releases the parking brake");
            Vector3 start = table.transform.position;
            for (float t = 0f; t < 1.5f; t += Time.deltaTime)
            {
                LookAt(start + table.transform.right * (-0.4f - 0.4f * t) + table.transform.up * 0.45f);
                yield return null;
            }
            yield return Button(false); yield return new WaitForSeconds(0.4f);
            float moved = Vector3.Distance(start, table.transform.position);
            Check(moved > 0.02f && moved < 1.5f, "the heavy gurney moves with sustained deliberate effort (" + moved.ToString("F3") + " m)");
            Vector3 parked = table.transform.position; yield return new WaitForSeconds(0.6f);
            Check(Vector3.Distance(parked, table.transform.position) < 0.01f, "parking brake holds after release");
            Shot("g35_gurney_braked");
        }
#endif
    }
}
