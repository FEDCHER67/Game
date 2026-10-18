using System.Collections;
using System.IO;
using System.Linq;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Audio;
using OnlyVolunteers.Characters.Npc;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Claude rework of G35, item 3 (Fedya 2026-10-18): the body bag is the corpse's own ragdoll, wrapped.
    /// Real virtual Mouse/Keyboard: a dead patient stays on the table until a player takes him (review M1), LMB takes him
    /// off with the normal grab, hold R packs him where he lies, E lifts and carries the bag, E puts it down, LMB drags it
    /// like a ragdoll, E + LMB throws it, K saves it, and thrown into the river it sinks and is disposed.</summary>
    public sealed partial class OperationNetworkProbe
    {
        public static string LastBagId;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        private Camera overviewCam;
        private RenderTexture overviewRt;
        private bool overviewRecording;

        private void ClOverview(string name, Vector3 eye, Vector3 at)
        {
            if (output == null) return;
            if (overviewCam == null)
            {
                overviewCam = new GameObject("ClOverviewCam").AddComponent<Camera>(); overviewCam.enabled = false;
                overviewCam.fieldOfView = 50f; overviewCam.nearClipPlane = 0.05f; overviewCam.farClipPlane = 400f;
                overviewRt = new RenderTexture(1280, 720, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 }; overviewCam.targetTexture = overviewRt;
            }
            overviewCam.transform.SetPositionAndRotation(eye, Quaternion.LookRotation(at - eye));
            overviewCam.Render();
            var prev = RenderTexture.active; RenderTexture.active = overviewRt;
            var tex = new Texture2D(1280, 720, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 1280, 720), 0, 0); tex.Apply();
            RenderTexture.active = prev;
            File.WriteAllBytes(Path.Combine(output, name + ".png"), tex.EncodeToPNG()); Destroy(tex);
            Line("SHOT " + name + " (overview)");
        }

        private IEnumerator ClRecordOverview(System.Func<(Vector3 eye, Vector3 at)> pose, string folderName)
        {
            string folder = Path.Combine(output, folderName); Directory.CreateDirectory(folder);
            var cam = new GameObject("ClOverviewRecorder").AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = 50f; cam.nearClipPlane = 0.05f; cam.farClipPlane = 400f;
            var target = new RenderTexture(960, 540, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2 }; cam.targetTexture = target;
            var tex = new Texture2D(960, 540, TextureFormat.RGB24, false); int frame = 0;
            overviewRecording = true;
            while (overviewRecording)
            {
                var p = pose(); cam.transform.SetPositionAndRotation(p.eye, Quaternion.LookRotation(p.at - p.eye)); cam.Render();
                var prev = RenderTexture.active; RenderTexture.active = target; tex.ReadPixels(new Rect(0, 0, 960, 540), 0, 0); tex.Apply(); RenderTexture.active = prev;
                File.WriteAllBytes(Path.Combine(folder, "o" + (frame++).ToString("D5") + ".jpg"), tex.EncodeToJPG(82));
                yield return new WaitForSeconds(0.1f);
            }
            Destroy(tex); cam.targetTexture = null; target.Release(); Destroy(target); Destroy(cam.gameObject);
        }

        /// <summary>Looks at the table patient until the corpse aim (the one R/LMB use) reports him.</summary>
        private IEnumerator ClAimTablePatient(CaptureDirector director)
        {
            aimed = false;
            var ragdoll = table.PatientObject != null ? table.PatientObject.GetComponent<NpcRagdoll>() : null;
            if (ragdoll == null) yield break;
            foreach (var landmark in new[] { NpcLandmark.Pelvis, NpcLandmark.Collar, NpcLandmark.Head })
            {
                LookAt(ragdoll.Landmark(landmark)); yield return Frames(3);
                director.Disposal.Aim(new Ray(Cam.transform.position, Cam.transform.forward), out _, out bool tablePatient);
                if (tablePatient) { aimed = true; yield break; }
            }
        }

        private static bool Wrapped(CaptureCorpse corpse, out string why)
        {
            why = "";
            var wrap = corpse != null ? corpse.GetComponent<OperationBodyBagWrap>() : null;
            if (wrap == null || !wrap.Applied || !wrap.Skin.enabled) { why = "no bag skin"; return false; }
            foreach (var r in corpse.GetComponentsInChildren<Renderer>())
                if (r.enabled && r != wrap.Skin && r.gameObject.activeInHierarchy && !(r is LineRenderer)) { why = "visible " + r.name; return false; }
            return true;
        }

        private IEnumerator ClBag()
        {
            var director = CaptureDirector.Instance; var disposal = director.Disposal; var hands = disposal.Hands;
            Check(table.AdmissionMode && table.HasPatient, "a captured patient lies on the base table");
            string id = S.patientId; var state = S;
            yield return EnterTable(); yield return Straps(true);
            yield return Inject(5.1f, "rework corpse fixture overdose");
            Check(!state.alive, "the patient died on the table (unchanged overdose rule, real syringe input)");
            yield return Select(Key.Digit1, ToolSlot.Hands);
            yield return Tap(Key.Escape); yield return new WaitForSeconds(1.2f);
            Check(table.HasPatient && table.State == state, "M1: a dead, still strapped patient stays on the table");
            Vector3 outward = -table.transform.right; outward.y = 0f; outward.Normalize();
            Vector3 foot = table.transform.position + outward * 1.05f; foot.y = table.transform.position.y + 0.02f;
            Teleport(foot); yield return Frames(4);
            yield return ClAimTablePatient(director); Check(aimed, "first-person aim finds the dead patient on the table");
            Line("HINT «" + disposal.Hint + "»");
            yield return Button(true); yield return new WaitForSeconds(0.3f); yield return Button(false); yield return new WaitForSeconds(0.3f);
            Check(table.HasPatient, "LMB on a STRAPPED corpse does not take it off the table");
            yield return EnterTable();
            for (int i = 0; i < 5; i++)
            {
                if (!state.restraints[i]) continue;
                yield return G35AimStrap(i); yield return Click(); yield return new WaitForSeconds(0.32f);
            }
            Check(state.restraints.All(r => !r), "all five straps opened with PREP clicks");
            yield return Tap(Key.Escape); yield return new WaitForSeconds(1.5f);
            Check(table.HasPatient, "M1: the unstrapped corpse still stays on the table until a player takes it");
            // ---- LMB takes him off the table with the normal grab ----
            Teleport(foot); yield return Frames(4);
            yield return ClAimTablePatient(director);
            Line("HINT «" + disposal.Hint + "»");
            yield return Button(true); yield return new WaitForSeconds(0.4f);
            var corpse = disposal.Corpses.FirstOrDefault(x => x != null && x.PatientId == id);
            if (!Check(corpse != null && !table.HasPatient && corpse.Held, "LMB takes the corpse off the table and the normal grab holds it")) { yield return Button(false); yield break; }
            Vector3 start = corpse.Center;
            for (float t = 0f; t < 1.2f; t += Time.deltaTime) { Teleport(foot + outward * t); LookAt(start + outward * 0.4f + Vector3.up * 0.7f); yield return null; }
            yield return Button(false); yield return new WaitForSeconds(1.0f);
            Check(Vector3.Distance(start, corpse.Center) > 0.6f && corpse.Center.y < table.transform.position.y + 0.45f, "the corpse is carried off and lies on the floor");
            // ---- R: pack into a bag where he lies ----
            Vector3 lie = corpse.Center; foot = lie + outward * 0.9f; foot.y = table.transform.position.y + 0.02f; Teleport(foot); yield return Frames(4);
            yield return G35AimCorpse(corpse); Check(aimed, "R targets the corpse in first person");
            int stock = disposal.Stock;
            yield return HoldKey(Key.R, 1.25f); yield return new WaitForSeconds(0.4f);
            Check(corpse != null && corpse.Bagged && corpse.PatientId == id, "hold R packs the SAME corpse into a body bag where it lies");
            Check(disposal.Stock == stock - 1 && !director.Registry.IsCompleted(id), "packing consumes exactly one bag and does not dispose the identity");
            var ragdoll = corpse.Ragdoll; var npcRagdoll = corpse.GetComponent<NpcRagdoll>();
            Check(ragdoll.Active && ragdoll.DynamicBodies == 11, "the bag IS the NPC ragdoll: 11 dynamic bodies, the same bones");
            Check(Wrapped(corpse, out string why), "the bag art is skinned onto the ragdoll and the body itself is hidden (" + (why == "" ? "ok" : why) + ")");
            var wrapSkin = corpse.GetComponent<OperationBodyBagWrap>().Skin;
            Check(wrapSkin.bones.Length == 7 && wrapSkin.bones.All(b => b != null), "the bag follows the trunk and leg bones (7)");
            bool armsLocked = true;
            for (int i = 0; i < npcRagdoll.PartCount; i++)
            {
                var kind = npcRagdoll.Profile.Parts[i].Kind;
                if (kind == NpcRagdollProfile.Kind.UpperArm || kind == NpcRagdollProfile.Kind.ForeArm)
                    armsLocked &= npcRagdoll.JointOf(i) != null && npcRagdoll.JointOf(i).angularXMotion == ConfigurableJointMotion.Locked;
            }
            Check(armsLocked, "no flailing limbs: the arms are locked inside the bag");
            Check(corpse.GetComponentsInChildren<Collider>().Count(c => c.enabled && !c.isTrigger) >= 11, "the bag keeps the ragdoll's own colliders (it cannot pass walls or doors)");
            Shot("bag_01_packed_fp");
            ClOverview("bag_01_packed", corpse.Center + outward * 1.6f + Vector3.up * 1.4f + table.transform.forward * 0.8f, corpse.Center);
            var follow = corpse;
            StartCoroutine(ClRecordOverview(() => ((follow != null ? follow.Center : table.transform.position) + outward * 2.6f + Vector3.up * 1.7f + table.transform.forward * 1.2f,
                follow != null ? follow.Center : table.transform.position), "overview_shed"));
            // ---- E: lift and carry ----
            yield return G35AimCorpse(corpse); yield return Tap(Key.E); yield return new WaitForSeconds(0.9f);
            Check(hands.Carrying == corpse && corpse.Held, "E lifts the body bag (carried with the server hold)");
            Check(!view.Active, "E at the bag never opens the table view");
            float lifted = corpse.Center.y - table.transform.position.y;
            Check(lifted > 0.7f, "the bag is carried in the arms, off the ground (centre " + lifted.ToString("F2") + " m up)");
            Shot("bag_02_carried_fp");
            Vector3 carryStart = corpse.Center, from = foot;
            for (float t = 0f; t < 1.6f; t += Time.deltaTime) { Teleport(from + outward * t * 1.1f); LookAt(Cam.transform.position + outward * 2f + Vector3.down * 0.4f); yield return null; }
            yield return new WaitForSeconds(0.4f);
            Check(hands.Carrying == corpse && Vector3.Distance(carryStart, corpse.Center) > 1.0f, "the carried bag follows the player (" + Vector3.Distance(carryStart, corpse.Center).ToString("F2") + " m)");
            ClOverview("bag_02_carried", Cam.transform.position + outward * 2.4f + Vector3.up * 0.6f + table.transform.forward * 1.5f, corpse.Center);
            Check(corpse.GetComponentsInChildren<Collider>().Where(c => c.enabled).All(c => !OnlyVolunteers.Player.Physics.PlayerPushPolicy.Allows(c)), "the carried bag can never push or lift the player");
            yield return Tap(Key.E); yield return new WaitForSeconds(1.2f);
            Check(hands.Carrying == null && !corpse.Held && corpse.Center.y < table.transform.position.y + 0.45f, "E again puts the bag down");
            // ---- LMB: drag it like a ragdoll ----
            foot = corpse.Center + outward * 0.9f; foot.y = table.transform.position.y + 0.02f; Teleport(foot); yield return Frames(4);
            yield return G35AimCorpse(corpse);
            yield return Button(true); yield return new WaitForSeconds(0.35f);
            Check(corpse.Held && hands.Carrying == null, "LMB grabs the bag with the normal ragdoll grab");
            Vector3 dragStart = corpse.Center;
            for (float t = 0f; t < 1.4f; t += Time.deltaTime) { Teleport(foot + outward * t); LookAt(dragStart + outward * (0.3f + t * 0.9f) + Vector3.up * 0.2f); yield return null; }
            Shot("bag_03_dragged_fp");
            yield return Button(false); yield return new WaitForSeconds(0.8f);
            Check(Vector3.Distance(dragStart, corpse.Center) > 0.5f, "LMB drags the bag along the floor (" + Vector3.Distance(dragStart, corpse.Center).ToString("F2") + " m)");
            // ---- E + LMB: throw ----
            foot = corpse.Center + outward * 0.9f; foot.y = table.transform.position.y + 0.02f; Teleport(foot); yield return Frames(4);
            yield return G35AimCorpse(corpse); yield return Tap(Key.E); yield return new WaitForSeconds(0.8f);
            Check(hands.Carrying == corpse, "E lifts it again");
            LookAt(Cam.transform.position + outward * 3f + Vector3.up * 0.3f); yield return new WaitForSeconds(1.0f); // the bag swings round in front
            yield return Button(true); yield return Frames(2); yield return Button(false); yield return new WaitForSeconds(0.08f);
            Check(hands.Carrying == null && npcRagdoll.MainBody != null && npcRagdoll.MainBody.linearVelocity.magnitude > 1f, "LMB throws the carried bag");
            yield return new WaitForSeconds(1.2f);
            Check(Wrapped(corpse, out why), "still one wrapped bag after the throw (" + (why == "" ? "ok" : why) + ")");
            yield return Tap(Key.K); yield return new WaitForSeconds(0.3f);
            var save = JsonUtility.FromJson<CaptureSaveData>(File.ReadAllText(director.SavePath));
            Check(save.corpses.Any(x => x.bagged && x.facts.patientId == id && x.bonePositions != null && x.bonePositions.Length == 11) && save.bodyBags == stock - 1, "K saves the bagged ragdoll (identity, bone pose) and the bag stock");
            LastBagId = id;
            overviewRecording = false; yield return Frames(2);
            // ---- water: on the river bank, lift it and throw it in ----
            // A narrow stance over the water's edge: he stands 0.85 m short of a deep point, the bag beside him; E lifts
            // it into his hands (over the water), E again lets go of it there.
            Vector3 water = G35WaterPoint(WaterKind.River);
            Vector3 stand = water + Vector3.up * 0.55f - Vector3.forward * CaptureCorpseHands.CarryForward;
            var platform = GameObject.CreatePrimitive(PrimitiveType.Cube); platform.name = "Rework water test stance";
            platform.transform.position = stand - Vector3.up * 0.1f - Vector3.right * 0.9f; platform.transform.localScale = new Vector3(3.0f, 0.2f, 0.6f);
            Teleport(stand + Vector3.up * 0.02f); SetYawPitch(0f, 30f); yield return new WaitForSeconds(0.3f);
            // Fixture: the bag is moved onto the stance beside him (walking it all the way is not what is tested here).
            npcRagdoll.PlaceLying(stand - Vector3.right * 1.3f, Vector3.right, true);
            yield return new WaitForSeconds(0.8f);
            Vector3 riverEye = water + Vector3.right * 6f + Vector3.up * 3f + Vector3.forward * 4f;
            StartCoroutine(ClRecordOverview(() => (riverEye, water + Vector3.right * 0.8f), "overview_river"));
            yield return G35AimCorpse(corpse); yield return Tap(Key.E); yield return new WaitForSeconds(0.8f);
            Check(hands.Carrying == corpse, "E lifts the bag at the river");
            SetYawPitch(0f, 35f); yield return new WaitForSeconds(1.0f);
            Shot("bag_04_riverbank_fp");
            yield return Tap(Key.E);
            yield return new WaitForSeconds(0.5f); Destroy(platform);
            yield return new WaitForSeconds(0.2f); ClOverview("bag_05_river_splash", riverEye, water + Vector3.right * 0.8f);
            yield return WaitFor(() => disposal.LastDisposed == id, 8f, "let go over the river, the bagged ragdoll splashes, sinks and is disposed");
            Check(director.Registry.IsCompleted(id) && !director.Facts.ContainsKey(id), "only the water resolves the identity and clears the evidence");
            Check(disposal.WitnessHooks.Any(x => x.patientId == id && x.bagged && x.points == 2) && disposal.WitnessHooks.Any(x => x.patientId == id && !x.bagged && x.points == 10), "witness hooks: +10 carrying the corpse, +2 carrying the bag");
            overviewRecording = false; yield return Frames(2);
        }
#endif
    }
}
