using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Operation
{
    /// <summary>
    /// Kidney removal in three short steps on the strapped patient, driven by OperationSession:
    /// 1) Cut: hold LMB at the start of the dotted line and drag the scalpel along it.
    /// 2) Pull: grab the kidney and drag the mouse up until it pops; a sudden yank tears it (one grade lower).
    /// 3) Tape: three strips of duct tape across the slit.
    /// Forgiving by design (canon 42): drifting off the line only pauses the cut; only a mostly sloppy cut or a yank
    /// lowers the grade, by one step each. All geometry is placeholder primitives under the patient's visual.
    /// </summary>
    public sealed class KidneyMiniGame
    {
        public enum Step
        {
            Cut,
            Pull,
            Tape,
            Done,
        }

        // Tolerances in metres on the body surface.
        private const float GrabRadius = 0.07f;
        private const float NeatDistance = 0.045f;
        private const float SlipDistance = 0.13f;
        private const float PopHeight = 0.16f;
        private const float YankSeconds = 0.08f;
        private const int TapeNeeded = 3;

        private readonly OperationPatient patient;
        private readonly Camera camera;
        private readonly AudioSource sfx;
        private readonly System.Action<string, Vector3, Color> comic;
        private readonly Transform space;
        private readonly Vector3 start;
        private readonly Vector3 end;
        private readonly float length;
        private readonly Vector3 direction;
        private readonly Vector3 normal = Vector3.up;
        private readonly List<GameObject> spawned = new List<GameObject>();
        private readonly List<float> tapeAlong = new List<float>();
        private readonly Material skinCut;
        private readonly Material organ;
        private readonly Material steel;
        private readonly Material tape;

        private Transform scalpel;
        private Transform tapeRoll;
        private Transform cutVisual;
        private Transform kidney;
        private Transform vessel;
        private bool cutting;
        private float progress;
        private float neatLength;
        private float tickAt;
        private bool pulling;
        private float grabMouseY;
        private float raise;
        private float lowTensionTime;

        /// <param name="mirrored">Second kidney: the incision is mirrored to the other side of the body.</param>
        public KidneyMiniGame(OperationPatient patient, bool mirrored, Camera camera, AudioSource sfx,
            System.Action<string, Vector3, Color> comic)
        {
            this.patient = patient;
            this.camera = camera;
            this.sfx = sfx;
            this.comic = comic;
            space = patient.Visual;
            start = space.InverseTransformPoint(patient.KidneyIncisionStart.position);
            end = space.InverseTransformPoint(patient.KidneyIncisionEnd.position);
            start.y = end.y = Mathf.Max(start.y, end.y);
            if (mirrored)
            {
                start.z = -start.z;
                end.z = -end.z;
            }
            length = Vector3.Distance(start, end);
            direction = (end - start) / length;
            skinCut = MakeMaterial(new Color(0.55f, 0.08f, 0.16f));
            organ = MakeMaterial(new Color(0.78f, 0.25f, 0.33f));
            steel = MakeMaterial(new Color(0.82f, 0.85f, 0.9f));
            tape = MakeMaterial(new Color(0.62f, 0.63f, 0.6f));
            BuildGuide();
            scalpel = BuildScalpel();
            tapeRoll = BuildTapeRoll();
        }

        public Step Current { get; private set; } = Step.Cut;
        public float CutProgress => progress;
        public float Neatness => progress > 0f ? neatLength / (progress * length) : 1f;
        public float Tension => raise / PopHeight;
        public int TapeCount => tapeAlong.Count;
        public int Slips { get; private set; }
        public bool Yanked { get; private set; }

        /// <summary>The kidney object once it has popped out (handed to OrganPop by the session).</summary>
        public Transform PoppedKidney { get; private set; }

        /// <summary>The session took the popped kidney over.</summary>
        public void ClearPoppedKidney() => PoppedKidney = null;

        /// <summary>Grade steps lost: one for a mostly sloppy cut, one for a yank (canon 42: hard to ruin by accident).</summary>
        public int Penalty => (Neatness < 0.5f ? 1 : 0) + (Yanked ? 1 : 0);

        public string Instruction
        {
            get
            {
                switch (Current)
                {
                    case Step.Cut:
                        if (cutting) return $"Режь по пунктиру…  {Mathf.RoundToInt(progress * 100f)}%";
                        return progress > 0f
                            ? "Зажми ЛКМ там, где закончил, и веди дальше"
                            : "1/3  РАЗРЕЗ: зажми ЛКМ у начала пунктира и веди скальпель. [Пробел] — прижать пациента";
                    case Step.Pull:
                        return pulling
                            ? "Тяни вверх… плавно!"
                            : "2/3  ДОСТАТЬ: схвати почку ЛКМ и тяни мышь вверх, пока не выскочит. Не дёргай!";
                    case Step.Tape:
                        return $"3/3  ЗАКЛЕИТЬ: кликай по разрезу скотчем ({TapeCount}/{TapeNeeded})";
                    default:
                        return "Готово!";
                }
            }
        }

        /// <summary>Advances the step under the current mouse state. Returns true when the operation is finished.</summary>
        public bool Tick(Mouse mouse, Keyboard keyboard)
        {
            if (keyboard.spaceKey.isPressed) patient.HeldDown = 1f;
            bool onBody = TryMouseOnBody(mouse, out Vector3 local);
            switch (Current)
            {
                case Step.Cut:
                    TickCut(mouse, onBody, local);
                    break;
                case Step.Pull:
                    TickPull(mouse, onBody, local);
                    break;
                case Step.Tape:
                    TickTape(mouse, onBody, local);
                    break;
            }
            return Current == Step.Done;
        }

        /// <summary>Removes everything this mini-game spawned except the popped kidney (owned by OrganPop) and the tape.</summary>
        public void Cleanup(bool keepScar)
        {
            foreach (GameObject go in spawned)
                if (go != null && (!keepScar || !go.name.StartsWith("Scar")))
                    Object.Destroy(go);
            spawned.Clear();
            patient.Scream = 0f;
        }

        private void TickCut(Mouse mouse, bool onBody, Vector3 local)
        {
            scalpel.gameObject.SetActive(onBody);
            if (onBody) scalpel.localPosition = local + normal * 0.03f;
            Vector3 resumeAt = start + direction * (progress * length);
            if (!cutting)
            {
                patient.Scream = Mathf.MoveTowards(patient.Scream, 0f, Time.deltaTime);
                if (onBody && mouse.leftButton.wasPressedThisFrame && Flat(local - resumeAt).magnitude <= GrabRadius) cutting = true;
                return;
            }
            if (!mouse.leftButton.isPressed || !onBody)
            {
                cutting = false;
                return;
            }

            Vector3 offset = Flat(local - start);
            float along = Vector3.Dot(offset, direction) / length;
            float off = (offset - direction * (along * length)).magnitude;
            if (off > SlipDistance)
            {
                cutting = false;
                Slips++;
                patient.Jolt();
                OperationSfx.Play(sfx, OperationCue.Yelp);
                comic("АЙ!", space.TransformPoint(local), new Color(1f, 0.85f, 0.3f));
                return;
            }
            // Only forward progress counts, and only in small steps (no teleporting the blade to the end).
            if (along > progress && along - progress < 0.2f)
            {
                float delta = Mathf.Min(along, 1f) - progress;
                if (off <= NeatDistance) neatLength += delta * length;
                progress = Mathf.Min(along, 1f);
                patient.Scream = 0.6f;
                UpdateCutVisual(0.006f);
                if (progress >= tickAt)
                {
                    tickAt = progress + 0.12f;
                    OperationSfx.Play(sfx, OperationCue.Tick, 0.35f);
                }
            }
            if (progress < 0.97f) return;

            progress = 1f;
            cutting = false;
            scalpel.gameObject.SetActive(false);
            UpdateCutVisual(0.035f);
            OperationSfx.Play(sfx, OperationCue.Slit);
            comic("ВЖУХ!", space.TransformPoint((start + end) * 0.5f), Color.white);
            kidney = BuildKidney();
            vessel = BuildVessel();
            Begin(Step.Pull);
        }

        private void TickPull(Mouse mouse, bool onBody, Vector3 local)
        {
            Vector3 mid = (start + end) * 0.5f;
            if (!pulling)
            {
                // Released: the kidney springs back into the slit.
                float before = raise;
                raise = Mathf.MoveTowards(raise, 0f, Time.deltaTime * 0.8f);
                if (before > PopHeight * 0.5f && raise <= PopHeight * 0.5f) OperationSfx.Play(sfx, OperationCue.Boing, 0.4f);
                if (onBody && mouse.leftButton.wasPressedThisFrame && Flat(local - mid).magnitude <= GrabRadius * 1.3f)
                {
                    pulling = true;
                    grabMouseY = mouse.position.ReadValue().y - raise / PopHeight * Screen.height * 0.18f;
                    lowTensionTime = Time.time;
                }
            }
            else if (!mouse.leftButton.isPressed)
            {
                pulling = false;
            }
            else
            {
                // About 18% of the screen height of mouse travel pops it.
                float travel = (mouse.position.ReadValue().y - grabMouseY) / (Screen.height * 0.18f);
                raise = Mathf.Clamp(travel, 0f, 1.05f) * PopHeight;
                if (Tension < 0.35f) lowTensionTime = Time.time;
            }

            patient.Scream = Tension;
            float stretch = 1f + Tension * 0.5f;
            kidney.localPosition = mid + normal * (0.01f + raise);
            kidney.localScale = new Vector3(0.12f / stretch, 0.065f * stretch, 0.075f / stretch);
            PlaceBetween(vessel, mid - normal * 0.02f, kidney.localPosition, 0.012f / stretch);
            if (Tension < 1f) return;

            Yanked = Time.time - lowTensionTime < YankSeconds;
            pulling = false;
            Object.Destroy(vessel.gameObject);
            PoppedKidney = kidney;
            spawned.Remove(kidney.gameObject);
            kidney.SetParent(null, true);
            kidney.localScale = new Vector3(0.12f, Yanked ? 0.045f : 0.065f, 0.075f);
            Vector3 world = kidney.position;
            Splash(world, Yanked ? 9 : 3);
            if (Yanked)
            {
                kidney.GetComponent<Renderer>().sharedMaterial = MakeMaterial(new Color(0.52f, 0.2f, 0.25f));
                OperationSfx.Play(sfx, OperationCue.Rip);
                comic("ХРЯСЬ! Рывок — почка помята", world, new Color(1f, 0.5f, 0.4f));
            }
            else
            {
                OperationSfx.Play(sfx, OperationCue.Pop, 0.8f);
                comic("ПЛОП!", world, new Color(0.6f, 1f, 0.6f));
            }
            patient.Jolt();
            Begin(Step.Tape);
        }

        private void TickTape(Mouse mouse, bool onBody, Vector3 local)
        {
            patient.Scream = Mathf.MoveTowards(patient.Scream, 0.2f, Time.deltaTime);
            tapeRoll.gameObject.SetActive(onBody);
            if (onBody) tapeRoll.localPosition = local + normal * 0.04f;
            if (!onBody || !mouse.leftButton.wasPressedThisFrame) return;

            Vector3 offset = Flat(local - start);
            float along = Vector3.Dot(offset, direction) / length;
            float off = (offset - direction * (along * length)).magnitude;
            if (along < -0.05f || along > 1.05f || off > 0.08f) return;
            along = Mathf.Clamp01(along);
            foreach (float placed in tapeAlong)
                if (Mathf.Abs(placed - along) * length < 0.05f)
                    return;

            tapeAlong.Add(along);
            Vector3 at = start + direction * (along * length) + normal * 0.004f;
            GameObject strip = Primitive(PrimitiveType.Cube, "Scar_Tape", tape);
            strip.transform.localPosition = at;
            strip.transform.localRotation = Quaternion.LookRotation(direction, normal) * Quaternion.Euler(0f, Random.Range(-12f, 12f), 0f);
            strip.transform.localScale = new Vector3(0.11f, 0.006f, 0.035f);
            OperationSfx.Play(sfx, OperationCue.Tape);
            comic("ШРРК!", space.TransformPoint(at), new Color(0.85f, 0.85f, 0.85f));
            if (tapeAlong.Count < TapeNeeded) return;
            tapeRoll.gameObject.SetActive(false);
            Begin(Step.Done);
        }

        private void Begin(Step step)
        {
            Current = step;
        }

        private bool TryMouseOnBody(Mouse mouse, out Vector3 local)
        {
            local = default;
            Ray ray = camera.ScreenPointToRay(mouse.position.ReadValue());
            Vector3 planePoint = space.TransformPoint(start);
            var plane = new Plane(space.TransformDirection(normal), planePoint);
            if (!plane.Raycast(ray, out float distance)) return false;
            local = space.InverseTransformPoint(ray.GetPoint(distance));
            // Only the patient's torso area counts as "on the body".
            return Flat(local - (start + end) * 0.5f).magnitude < 0.45f;
        }

        private Vector3 Flat(Vector3 v) => v - normal * Vector3.Dot(v, normal);

        private void BuildGuide()
        {
            const int dashes = 7;
            Material ink = MakeMaterial(new Color(0.15f, 0.15f, 0.5f));
            for (int i = 0; i < dashes; i++)
            {
                float t = (i + 0.5f) / dashes;
                GameObject dash = Primitive(PrimitiveType.Cube, "Guide", ink);
                dash.transform.localPosition = Vector3.Lerp(start, end, t) + normal * 0.002f;
                dash.transform.localRotation = Quaternion.LookRotation(direction, normal);
                dash.transform.localScale = new Vector3(0.008f, 0.003f, length / dashes * 0.55f);
            }
            GameObject startMark = Primitive(PrimitiveType.Sphere, "Guide_Start", MakeMaterial(new Color(0.2f, 0.8f, 0.3f)));
            startMark.transform.localPosition = start + normal * 0.004f;
            startMark.transform.localScale = new Vector3(0.03f, 0.006f, 0.03f);
        }

        private void UpdateCutVisual(float width)
        {
            if (cutVisual == null) cutVisual = Primitive(PrimitiveType.Cube, "Scar_Cut", skinCut).transform;
            PlaceAlong(cutVisual, start, start + direction * (progress * length), width);
        }

        private void PlaceAlong(Transform t, Vector3 from, Vector3 to, float width)
        {
            Vector3 d = to - from;
            float len = Mathf.Max(0.001f, d.magnitude);
            t.localPosition = (from + to) * 0.5f + normal * 0.003f;
            t.localRotation = Quaternion.LookRotation(d / len, normal);
            t.localScale = new Vector3(width, 0.004f, len);
        }

        private static void PlaceBetween(Transform t, Vector3 from, Vector3 to, float width)
        {
            Vector3 d = to - from;
            t.localPosition = (from + to) * 0.5f;
            t.localRotation = Quaternion.FromToRotation(Vector3.up, d.sqrMagnitude > 1e-6f ? d.normalized : Vector3.up);
            t.localScale = new Vector3(width, d.magnitude * 0.5f, width);
        }

        private Transform BuildScalpel()
        {
            var root = new GameObject("Scalpel").transform;
            root.SetParent(space, false);
            spawned.Add(root.gameObject);
            GameObject blade = Primitive(PrimitiveType.Cube, "Blade", steel);
            blade.transform.SetParent(root, false);
            blade.transform.localPosition = new Vector3(0f, 0f, 0f);
            blade.transform.localScale = new Vector3(0.012f, 0.03f, 0.04f);
            GameObject handle = Primitive(PrimitiveType.Cube, "Handle", MakeMaterial(new Color(0.3f, 0.32f, 0.36f)));
            handle.transform.SetParent(root, false);
            handle.transform.localPosition = new Vector3(0f, 0.05f, -0.06f);
            handle.transform.localRotation = Quaternion.Euler(-35f, 0f, 0f);
            handle.transform.localScale = new Vector3(0.018f, 0.018f, 0.11f);
            root.gameObject.SetActive(false);
            return root;
        }

        private Transform BuildTapeRoll()
        {
            GameObject roll = Primitive(PrimitiveType.Cylinder, "TapeRoll", tape);
            roll.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            roll.transform.localScale = new Vector3(0.08f, 0.02f, 0.08f);
            roll.SetActive(false);
            return roll.transform;
        }

        private Transform BuildKidney()
        {
            GameObject bean = Primitive(PrimitiveType.Sphere, "Kidney", organ);
            bean.transform.localPosition = (start + end) * 0.5f;
            bean.transform.localRotation = Quaternion.LookRotation(direction, normal);
            bean.transform.localScale = new Vector3(0.12f, 0.065f, 0.075f);
            return bean.transform;
        }

        private Transform BuildVessel() => Primitive(PrimitiveType.Cylinder, "Vessel", organ).transform;

        /// <summary>Cartoon droplets: a few bouncy pink blobs that shrink away (stylised, no realistic gore).</summary>
        private void Splash(Vector3 world, int count)
        {
            for (int i = 0; i < count; i++)
            {
                var drop = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                drop.name = "Droplet";
                Object.Destroy(drop.GetComponent<Collider>());
                drop.GetComponent<Renderer>().sharedMaterial = organ;
                drop.transform.position = world;
                drop.transform.localScale = Vector3.one * Random.Range(0.02f, 0.04f);
                drop.AddComponent<OrganDroplet>().Launch(new Vector3(Random.Range(-1f, 1f), Random.Range(1.5f, 2.6f), Random.Range(-1f, 1f)));
            }
        }

        private GameObject Primitive(PrimitiveType type, string name, Material material)
        {
            GameObject go = GameObject.CreatePrimitive(type);
            go.name = name;
            Object.Destroy(go.GetComponent<Collider>());
            go.GetComponent<Renderer>().sharedMaterial = material;
            go.transform.SetParent(space, false);
            spawned.Add(go);
            return go;
        }

        private static Material MakeMaterial(Color color)
        {
            Shader shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var material = new Material(shader);
            material.SetColor("_BaseColor", color);
            material.color = color;
            material.SetFloat("_Smoothness", 0.35f);
            return material;
        }
    }
}
