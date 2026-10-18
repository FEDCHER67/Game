using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>Zip-tie presentation shared by the crowd NPC and the table patient (same 65-bone Buddy rig): a dark
    /// plastic band on each tied wrist / ankle, a short strap between the pair, and the procedural "hands behind the
    /// back" pose for a tied NPC the Animator drives (standing, running, sitting). Never touches meshes or the skeleton
    /// asset; the pose is applied after the Animator every frame.</summary>
    public static class CaptureTieVisuals
    {
        private static Material plastic;
        public static Material Plastic
        {
            get
            {
                if (plastic != null) return plastic;
                var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
                plastic = new Material(shader) { name = "Capture_ZipTie (runtime)", hideFlags = HideFlags.DontSave };
                Color c = new Color(0.07f, 0.07f, 0.08f);
                plastic.color = c;
                if (plastic.HasProperty("_BaseColor")) plastic.SetColor("_BaseColor", c);
                if (plastic.HasProperty("_Smoothness")) plastic.SetFloat("_Smoothness", 0.55f);
                return plastic;
            }
        }

        /// <summary>(Re)builds the bands and links for the current ties under the given bones.</summary>
        public static void Ensure(ref GameObject[] bands, ref LineRenderer handLink, ref LineRenderer footLink,
            Transform[] wrist, Transform[] ankle, Restraints r, Transform owner)
        {
            bands ??= new GameObject[4];
            for (int i = 0; i < 2; i++)
            {
                SetBand(ref bands[i], wrist[i], r.hands, 0.085f);
                SetBand(ref bands[2 + i], ankle[i], r.feet, 0.105f);
            }
            if (r.hands && handLink == null) handLink = Link(owner, "ZipTie_HandsLink");
            if (r.feet && footLink == null) footLink = Link(owner, "ZipTie_FeetLink");
            if (handLink != null) handLink.enabled = r.hands;
            if (footLink != null) footLink.enabled = r.feet;
        }

        public static void UpdateLinks(LineRenderer handLink, LineRenderer footLink, Transform[] wrist, Transform[] ankle, Restraints r)
        {
            if (handLink != null && r.hands && wrist[0] != null && wrist[1] != null)
            {
                handLink.SetPosition(0, wrist[0].position);
                handLink.SetPosition(1, wrist[1].position);
            }
            if (footLink != null && r.feet && ankle[0] != null && ankle[1] != null)
            {
                footLink.SetPosition(0, ankle[0].position + Vector3.up * 0.03f);
                footLink.SetPosition(1, ankle[1].position + Vector3.up * 0.03f);
            }
        }

        private static void SetBand(ref GameObject band, Transform bone, bool on, float diameter)
        {
            if (!on)
            {
                if (band != null) Object.Destroy(band);
                band = null;
                return;
            }
            if (band != null || bone == null) return;
            band = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            band.name = "ZipTie_Band";
            Object.Destroy(band.GetComponent<Collider>());
            band.GetComponent<Renderer>().sharedMaterial = Plastic;
            band.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            band.transform.SetParent(bone, false);
            // Along the limb: the bone's own direction to its first child (hand -> fingers, foot -> toes), else its up.
            Vector3 along = bone.childCount > 0 ? (bone.GetChild(0).position - bone.position) : bone.up;
            if (along.sqrMagnitude < 1e-6f) along = bone.up;
            band.transform.rotation = Quaternion.FromToRotation(Vector3.up, along.normalized);
            band.transform.position = bone.position - along.normalized * 0.01f;
            Vector3 s = bone.lossyScale;
            float k = Mathf.Max(1e-4f, (Mathf.Abs(s.x) + Mathf.Abs(s.y) + Mathf.Abs(s.z)) / 3f);
            band.transform.localScale = new Vector3(diameter, 0.012f, diameter) / k;
        }

        private static LineRenderer Link(Transform owner, string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(owner, false);
            var line = go.AddComponent<LineRenderer>();
            line.positionCount = 2;
            line.useWorldSpace = true;
            line.startWidth = line.endWidth = 0.014f;
            line.sharedMaterial = Plastic;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            line.numCapVertices = 2;
            return line;
        }

        public static void Remove(ref GameObject[] bands, ref LineRenderer handLink, ref LineRenderer footLink)
        {
            if (bands != null) foreach (var b in bands) if (b != null) Object.Destroy(b);
            bands = null;
            if (handLink != null) Object.Destroy(handLink.gameObject);
            if (footLink != null) Object.Destroy(footLink.gameObject);
            handLink = footLink = null;
        }

        /// <summary>After the Animator: upper arms down and back, forearms across the lower back, so the wrists meet
        /// behind him. weight 0..1 blends from the animated pose.</summary>
        public static void ArmsBehindBack(Transform hips, Transform spine2, Transform[] upperArm, Transform[] foreArm, Transform[] wrist, float weight)
        {
            if (spine2 == null || upperArm[0] == null || upperArm[1] == null || foreArm[0] == null || foreArm[1] == null || wrist[0] == null || wrist[1] == null) return;
            Vector3 up = (spine2.position - hips.position).normalized;
            Vector3 right = upperArm[1].position - upperArm[0].position;
            right = Vector3.ProjectOnPlane(right, up).normalized;
            if (right.sqrMagnitude < 0.5f) return;
            Vector3 forward = Vector3.Cross(right, up).normalized;
            for (int side = 0; side < 2; side++)
            {
                float s = side == 0 ? -1f : 1f;
                Vector3 upperWant = (-up * 0.82f - forward * 0.42f + right * s * 0.2f).normalized;
                Aim(upperArm[side], foreArm[side].position - upperArm[side].position, upperWant, weight);
                Vector3 foreWant = (-right * s * 0.86f - forward * 0.32f + up * 0.28f).normalized;
                Aim(foreArm[side], wrist[side].position - foreArm[side].position, foreWant, weight);
            }
        }

        private static void Aim(Transform bone, Vector3 current, Vector3 want, float weight)
        {
            if (current.sqrMagnitude < 1e-6f) return;
            Quaternion turn = Quaternion.FromToRotation(current.normalized, want);
            bone.rotation = Quaternion.Slerp(Quaternion.identity, turn, weight) * bone.rotation;
        }
    }
}
