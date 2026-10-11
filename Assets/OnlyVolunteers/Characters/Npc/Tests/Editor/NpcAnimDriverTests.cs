using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text.RegularExpressions;
using NUnit.Framework;
using OnlyVolunteers.Map;
using OnlyVolunteers.Map.Crowd;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using C = OnlyVolunteers.Characters.Npc.NpcAnimContract;
using Params = OnlyVolunteers.Characters.Npc.NpcAnimDriver.Params;
using Inputs = OnlyVolunteers.Characters.Npc.NpcAnimDriver.Inputs;
using Speeds = OnlyVolunteers.Characters.Npc.NpcAnimDriver.Speeds;

namespace OnlyVolunteers.Characters.Npc.Tests
{
    // Stage 9 step 5 (design §5.4, §6): the Animator contract. EditMode, a few seconds, on the real Buddy controller in a
    // preview scene (Animator.Update by hand):
    // - ComposeMapsEveryState: NpcAnimDriver.Compose gives the contract's parameters for every NPC situation (free
    //   standing / walking / fleeing / running to report, police and fat police runs, crowd activities, lying Out / Groggy /
    //   carried, sitting in a van, escaping, aiming).
    // - ControllerPlaysEveryState: those parameters, written to the generated controller, land in the state each situation
    //   should show (and the get-up started by PlayGetUp plays from its first frame, then hands over by itself).
    // - NoWritesWhileHeld: with the Animator off (the ragdoll) or while NpcGetUp owns it (a get-up, the hop out of a van)
    //   the driver writes nothing and refuses one-shots; afterwards it takes over again.
    // - OnlyTheDriverWritesNpcAnimators: no NPC script but NpcAnimDriver plays clips or writes parameters.
    public sealed class NpcAnimDriverTests
    {
        private static readonly Speeds S = new() { Walk = 1.5f, Run = 3.2f, RunCop = 3.0f, RunCopFat = 1.8f, Scramble = 1.2f };

        private static Inputs Free(float speed = 0f, bool fleeing = false) =>
            new() { State = NpcState.Free, Phase = StunPhase.None, Speed = speed, Fleeing = fleeing, Activity = -1, Rate = 1f, IdleRate = 1f };

        [Test]
        public void ComposeMapsEveryState()
        {
            Params p = NpcAnimDriver.Compose(Free(), S);
            Expect(p, "free, standing", speed: 0f, mul: 1f, panic: false, stun: 0, cargo: false, activity: -1, carried: false);
            Assert.IsTrue(p.Driven && !p.Ragdoll && p.GetUp == 0 && !p.Aim, "free, standing: driven, no ragdoll, no get-up, no aim");

            Expect(NpcAnimDriver.Compose(Free(1.2f), S), "walking 1.2 m/s", speed: 1.2f, mul: 1.2f / 1.5f, panic: false, stun: 0);
            Expect(NpcAnimDriver.Compose(Free(4.5f, true), S), "fleeing 4.5 m/s", speed: 4.5f, mul: 4.5f / 3.2f, panic: true, stun: 0);
            Expect(NpcAnimDriver.Compose(Free(3.6f), S), "running to report 3.6 m/s", speed: 3.6f, mul: 3.6f / 3.2f, panic: false);
            Expect(NpcAnimDriver.Compose(Free(9f, true), S), "fleeing too fast for the clip", mul: 2f);

            Inputs cop = Free(5f);
            cop.Gait = NpcGait.Police;
            p = NpcAnimDriver.Compose(cop, S);
            Expect(p, "police run 5 m/s", mul: 5f / 3.0f, panic: false);
            Assert.AreEqual((float)NpcGait.Police, p.Gait, "police gait");
            Inputs fat = Free(5.6f);
            fat.Gait = NpcGait.PoliceFat;
            Expect(NpcAnimDriver.Compose(fat, S), "fat police run (own clip, x3 cap)", mul: 3f);
            fat.Rate = 1.35f;
            Expect(NpcAnimDriver.Compose(fat, new Speeds { Walk = 1.5f, Run = 3.2f, RunCop = 3.2f, RunCopFat = 3.2f, Scramble = 3.2f }),
                "fat police run without his clip (the civilian run x FatAnimFactor)", mul: 5.6f / 3.2f * 1.35f);

            Inputs bench = Free();
            bench.Activity = (int)CrowdActivity.BenchSit;
            Expect(NpcAnimDriver.Compose(bench, S), "on a bench", activity: (int)CrowdActivity.BenchSit, mul: 1f);
            Inputs scared = Free(4f, true);
            scared.Activity = (int)CrowdActivity.BenchSit;
            Expect(NpcAnimDriver.Compose(scared, S), "fleeing from the bench", activity: -1, panic: true);
            Inputs smoker = Free();
            smoker.Activity = (int)CrowdActivity.SmokeCorner;
            smoker.IdleRate = 0.6f;
            Expect(NpcAnimDriver.Compose(smoker, S), "smoking without its clips (the slow idle)", mul: 0.6f, activity: (int)CrowdActivity.SmokeCorner);

            var down = new Inputs { State = NpcState.Down, Phase = StunPhase.Out, Speed = 3f, Activity = 2, Aim = true, Rate = 1f, IdleRate = 1f };
            p = NpcAnimDriver.Compose(down, S);
            Expect(p, "lying, out", speed: 0f, mul: 1f, panic: false, stun: 1, cargo: false, activity: -1, carried: false);
            Assert.IsFalse(p.Aim, "lying: no aim");
            down.Phase = StunPhase.Groggy;
            down.Held = true;
            Expect(NpcAnimDriver.Compose(down, S), "lying, groggy, held", stun: 2, carried: true);

            var seated = new Inputs { State = NpcState.CargoSeated, Phase = StunPhase.Awake, Rate = 1f, IdleRate = 1f, Activity = -1 };
            Expect(NpcAnimDriver.Compose(seated, S), "sitting in the van", speed: 0f, panic: false, stun: 3, cargo: true, activity: -1);
            var escaping = new Inputs { State = NpcState.Escaping, Phase = StunPhase.Awake, Speed = 2f, Rate = 1f, IdleRate = 1f, Activity = -1 };
            Expect(NpcAnimDriver.Compose(escaping, S), "escaping", speed: 2f, mul: 2f / 1.2f, panic: true, stun: 3, cargo: true);

            Inputs aiming = Free();
            aiming.Aim = true;
            Assert.IsTrue(NpcAnimDriver.Compose(aiming, S).Aim, "a free officer aims");
        }

        private static void Expect(in Params p, string what, float? speed = null, float? mul = null, bool? panic = null, int? stun = null,
            bool? cargo = null, int? activity = null, bool? carried = null)
        {
            if (speed.HasValue) Assert.AreEqual(speed.Value, p.Speed, 1e-3f, what + ": Speed");
            if (mul.HasValue) Assert.AreEqual(mul.Value, p.SpeedMul, 1e-3f, what + ": SpeedMul");
            if (panic.HasValue) Assert.AreEqual(panic.Value, p.Panic, what + ": Panic");
            if (stun.HasValue) Assert.AreEqual(stun.Value, p.StunPhase, what + ": StunPhase");
            if (cargo.HasValue) Assert.AreEqual(cargo.Value, p.InCargo, what + ": InCargo");
            if (activity.HasValue) Assert.AreEqual(activity.Value, p.Activity, what + ": Activity");
            if (carried.HasValue) Assert.AreEqual(carried.Value, p.Carried, what + ": Carried");
        }

        // ---------- The controller ----------

        [Test]
        public void ControllerPlaysEveryState()
        {
            NpcRagdollProfile profile = AssetDatabase.LoadAssetAtPath<NpcRagdollProfile>(NpcRagdollBuilder.ProfilePath);
            Assert.IsNotNull(profile, NpcRagdollBuilder.ProfilePath);
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                Animator a = Buddy(scene, out _);
                var controller = (AnimatorController)a.runtimeAnimatorController;
                var states = BaseStates(controller);
                string sit = Installed(profile.SitIdle.State, states) ?? C.CargoFallbackState;
                string escape = Installed(profile.Role(C.RoleScrambleStart)?.State, states) ?? Installed(profile.Role(C.RoleScramble)?.State, states) ?? C.EscapeFallbackState;

                var cases = new List<(string what, Inputs input, string[] states)>
                {
                    ("free, standing", Free(), new[] { C.IdleState }),
                    ("walking", Free(1.3f), new[] { C.WalkState }),
                    ("running to report", Free(3.6f), new[] { C.RunState }),
                    ("fleeing", Free(4.5f, true), new[] { C.RunState }),
                    ("fleeing, slowed down", Free(0.5f, true), new[] { C.RunState }),
                    ("lying (the capsule), out", new Inputs { State = NpcState.Down, Phase = StunPhase.Out, Activity = -1, Rate = 1f, IdleRate = 1f }, new[] { C.DownState }),
                    ("lying, groggy", new Inputs { State = NpcState.Down, Phase = StunPhase.Groggy, Activity = -1, Rate = 1f, IdleRate = 1f }, new[] { C.DownState }),
                    ("sitting in the van", new Inputs { State = NpcState.CargoSeated, Phase = StunPhase.Awake, Activity = -1, Rate = 1f, IdleRate = 1f }, new[] { sit }),
                    ("escaping", new Inputs { State = NpcState.Escaping, Phase = StunPhase.Awake, Speed = 2f, Activity = -1, Rate = 1f, IdleRate = 1f },
                        new[] { escape, Installed(profile.Role(C.RoleScramble)?.State, states) ?? escape }),
                };
                Inputs police = Free(6f);
                police.Gait = NpcGait.Police;
                cases.Add(("police run", police, new[] { C.RunState }));
                foreach (CrowdActivity activity in (CrowdActivity[])Enum.GetValues(typeof(CrowdActivity)))
                {
                    Inputs input = Free();
                    input.Activity = (int)activity;
                    string loop = Installed(profile.Role(C.ActivityRole(activity.ToString(), C.LoopPhase))?.State, states);
                    string enter = Installed(profile.Role(C.ActivityRole(activity.ToString(), C.EnterPhase))?.State, states);
                    cases.Add(($"activity {activity}", input, loop != null ? new[] { enter ?? loop, loop } : new[] { C.IdleState }));
                }

                foreach ((string what, Inputs input, string[] want) in cases)
                {
                    // From standing still, the situation's parameters, 0.6 s.
                    Write(a, NpcAnimDriver.Compose(Free(), S));
                    Run(a, 0.6f);
                    Write(a, NpcAnimDriver.Compose(input, S));
                    Run(a, 0.6f);
                    string now = Current(a, states);
                    // Standing long enough, the idle variety takes turns with the Idle (clips.json links).
                    bool idleVariety = Array.IndexOf(want, C.IdleState) >= 0 && now.StartsWith(C.IdleState, StringComparison.Ordinal);
                    Assert.IsTrue(Array.IndexOf(want, now) >= 0 || idleVariety,
                        $"{what}: {NpcAnimDriver.Compose(input, S)} plays {now}, expected {string.Join(" or ", want)}");
                }

                // The get-up NpcGetUp starts: its first frame at once, then out by itself into the run.
                if (Installed(profile.GetUpBack.State, states) != null)
                {
                    Write(a, NpcAnimDriver.Compose(Free(), S));
                    Run(a, 0.6f);
                    a.Play(profile.GetUpBack.State, 0, 0f);
                    a.Update(0f);
                    AnimatorStateInfo first = a.GetCurrentAnimatorStateInfo(0);
                    Assert.IsTrue(first.IsName(profile.GetUpBack.State), "the get-up plays at once");
                    Assert.AreEqual(0f, first.normalizedTime, 0.01f, "from its first frame");
                    Write(a, new Params { Driven = true, StunPhase = 3, Activity = -1, SpeedMul = 1f, GetUp = 1 });
                    Run(a, profile.GetUpBack.Seconds * 0.5f);
                    Assert.IsTrue(a.GetCurrentAnimatorStateInfo(0).IsName(profile.GetUpBack.State), "the get-up is not cut short");
                    Write(a, NpcAnimDriver.Compose(Free(4.5f, true), S));
                    Run(a, profile.GetUpBack.Seconds * 0.5f + 0.5f);
                    Assert.AreEqual(C.RunState, Current(a, states), "after the get-up, fleeing: the run");
                }

                // Driven off (the player's Buddy): a state asked for by name stays, whatever the parameters.
                Write(a, new Params { Driven = false, Activity = -1, SpeedMul = 1f });
                a.Play(C.WalkState, 0, 0f);
                Run(a, 1f);
                Assert.AreEqual(C.WalkState, Current(a, states), "not driven: Walk by name stays at speed 0");
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        // ---------- Held ----------

        private static readonly MethodInfo DriverUpdate = typeof(NpcAnimDriver).GetMethod("Update", BindingFlags.NonPublic | BindingFlags.Instance);

        [Test]
        public void NoWritesWhileHeld()
        {
            Assert.IsNotNull(DriverUpdate, "NpcAnimDriver.Update");
            Scene scene = EditorSceneManager.NewPreviewScene();
            try
            {
                Animator a = Buddy(scene, out GameObject buddy);
                Assert.IsTrue(buddy.AddComponent<NpcRagdoll>().Ready, "the Buddy's ragdoll profile");
                NpcGetUp getUp = buddy.AddComponent<NpcGetUp>();
                NpcAnimDriver driver = buddy.AddComponent<NpcAnimDriver>();
                Assert.IsTrue(driver.HasContract, "the Buddy controller has the contract");

                // Driving: it writes (the free NPC's parameters over the defaults).
                DriverUpdate.Invoke(driver, null);
                Assert.Greater(driver.Writes, 0, "free: the driver writes");
                Assert.IsTrue(a.GetBool(C.Driven), "Driven");

                // The ragdoll: the Animator is off, nothing is written, one-shots are refused.
                int writes = driver.Writes;
                a.enabled = false;
                for (int i = 0; i < 3; i++) DriverUpdate.Invoke(driver, null);
                Assert.AreEqual(writes, driver.Writes, "Animator off (ragdoll): no writes");
                Assert.AreEqual(3, driver.HeldFrames, "held frames");
                Assert.IsFalse(driver.Trigger(NpcAnimTrigger.HitFront), "Animator off: no one-shot");
                a.enabled = true;
                a.Update(0f);

                // NpcGetUp's hop out of a van: its start writes (OwnerWrites), then nothing until it ends.
                int owner = driver.OwnerWrites;
                getUp.JumpOut(buddy.transform.position + Vector3.up * 0.55f, Vector3.right, 4.5f, out _);
                Assert.IsTrue(getUp.Owns, "the hop owns the Animator");
                Assert.Greater(driver.OwnerWrites, owner, "PlayGetUp wrote the hop's parameters");
                Assert.AreEqual((int)GetUpKind.JumpOut, a.GetInteger(C.GetUp), "GetUp = JumpOut");
                Assert.IsTrue(a.GetBool(C.Panic) && !a.GetBool(C.InCargo), "the hop: panicking, out of the van");
                writes = driver.Writes;
                var before = Snapshot(a);
                for (int i = 0; i < 5; i++)
                {
                    DriverUpdate.Invoke(driver, null);
                    a.Update(0.05f);
                }
                Assert.AreEqual(writes, driver.Writes, "while NpcGetUp owns the Animator: no driver writes");
                Assert.AreEqual(before, Snapshot(a), "while NpcGetUp owns the Animator: the parameters stay");
                Assert.IsFalse(driver.Trigger(NpcAnimTrigger.Beat), "while NpcGetUp owns the Animator: no one-shot");

                // Over: the driver takes over again (GetUp back to 0).
                getUp.Cancel();
                DriverUpdate.Invoke(driver, null);
                Assert.Greater(driver.Writes, writes, "after the get-up the driver writes again");
                Assert.AreEqual(0, a.GetInteger(C.GetUp), "GetUp cleared");
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(scene);
            }
        }

        // ---------- One writer ----------

        // Animator writes (playing clips, parameters, speed, manual updates) on an Animator variable.
        private static readonly Regex AnimatorWrite = new(
            @"\b_?[Aa]nimator\w*\s*\.\s*(Play|PlayInFixedTime|CrossFade\w*|Set(Float|Bool|Integer|Trigger)|ResetTrigger|Update|speed\s*=[^=])",
            RegexOptions.Compiled);

        [Test]
        public void OnlyTheDriverWritesNpcAnimators()
        {
            var offenders = new List<string>();
            foreach (string folder in new[] { "Assets/OnlyVolunteers/Map/Scripts", "Assets/OnlyVolunteers/Characters/Npc/Scripts", "Assets/OnlyVolunteers/Police/Scripts" })
                foreach (string file in Directory.GetFiles(folder, "*.cs", SearchOption.AllDirectories))
                {
                    string name = Path.GetFileName(file);
                    // The driver itself; the player's own Buddy pawn (GreyboxWalker) and the locomotion preview are not NPCs.
                    if (name == "NpcAnimDriver.cs" || name == "GreyboxWalker.cs" || name == "BuddyLocomotionPreview.cs") continue;
                    string[] lines = File.ReadAllLines(file);
                    for (int i = 0; i < lines.Length; i++)
                        if (AnimatorWrite.IsMatch(lines[i])) offenders.Add($"{file}:{i + 1}: {lines[i].Trim()}");
                }
            Assert.IsEmpty(offenders, "Animator writes outside NpcAnimDriver:\n" + string.Join("\n", offenders));
        }

        // ---------- Helpers ----------

        // Buddy A from its prefab (the generated controller), its Animator ready to update by hand.
        private static Animator Buddy(Scene scene, out GameObject buddy)
        {
            buddy = NpcRagdollBuilder.InstantiateSampled(NpcRagdollBuilder.BuddyPrefabs[0], scene);
            Animator a = buddy.GetComponent<Animator>();
            Assert.IsNotNull(a.runtimeAnimatorController, "Buddy A has no controller");
            a.Rebind();
            a.Update(0f);
            NpcAnimDriver.ClearCache();
            return a;
        }

        private static HashSet<string> BaseStates(AnimatorController controller)
        {
            var names = new HashSet<string>();
            foreach (ChildAnimatorState child in controller.layers[0].stateMachine.states) names.Add(child.state.name);
            return names;
        }

        private static string Installed(string state, HashSet<string> states) => !string.IsNullOrEmpty(state) && states.Contains(state) ? state : null;

        private static string Current(Animator a, HashSet<string> states)
        {
            AnimatorStateInfo info = a.GetCurrentAnimatorStateInfo(0);
            foreach (string s in states)
                if (info.IsName(s)) return s;
            return "?";
        }

        private static void Run(Animator a, float seconds)
        {
            for (float t = 0f; t < seconds; t += 0.05f) a.Update(0.05f);
        }

        // What NpcAnimDriver.Write does, without the driver (the controller alone).
        private static void Write(Animator a, Params p)
        {
            a.SetBool(C.Driven, p.Driven);
            a.SetBool(C.Ragdoll, p.Ragdoll);
            a.SetInteger(C.StunPhase, p.StunPhase);
            a.SetBool(C.InCargo, p.InCargo);
            a.SetBool(C.Panic, p.Panic);
            a.SetInteger(C.Activity, p.Activity);
            a.SetBool(C.Carried, p.Carried);
            a.SetBool(C.Aim, p.Aim);
            a.SetInteger(C.GetUp, p.GetUp);
            a.SetFloat(C.Gait, p.Gait);
            a.SetFloat(C.Speed, p.Speed);
            a.SetFloat(C.SpeedMul, p.SpeedMul);
        }

        private static string Snapshot(Animator a) =>
            $"{a.GetBool(C.Driven)} {a.GetBool(C.Ragdoll)} {a.GetInteger(C.StunPhase)} {a.GetBool(C.InCargo)} {a.GetBool(C.Panic)} " +
            $"{a.GetInteger(C.Activity)} {a.GetBool(C.Carried)} {a.GetBool(C.Aim)} {a.GetInteger(C.GetUp)} {a.GetFloat(C.Gait)} " +
            $"{a.GetFloat(C.Speed)} {a.GetFloat(C.SpeedMul)}";
    }
}
