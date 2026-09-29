#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Props.TableAstra
{
    /// <summary>Run in an isolated project with the FBX at Assets/TABLE-ASTRA-001.fbx.</summary>
    public static class TableAstraCasterValidation
    {
        private static readonly StringBuilder Report = new StringBuilder();
        private const BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;

        public static void Run()
        {
            try
            {
                CheckKernel();
                CheckImportedRig();
                Report.AppendLine("PASS: isolated Unity import, compile and caster motion checks.");
                File.WriteAllText("caster-validation.txt", Report.ToString());
                Debug.Log(Report.ToString());
            }
            catch (Exception error)
            {
                Report.AppendLine("FAIL: " + error);
                File.WriteAllText("caster-validation.txt", Report.ToString());
                Debug.LogError(error);
                EditorApplication.Exit(1);
            }
        }

        private static void CheckKernel()
        {
            double heading = 0, spin = 0;
            bool reverse = false;
            CasterKinematics.Advance(ref heading, ref spin, ref reverse, 1, 0, 0, 1, .035, .105, -1);
            Near(spin, -1 / .105, 1e-10, "one metre / radius, negative axle sign");
            Near(heading, 0, 1e-12, "straight heading");
            double slowHeading = .7, slowSpin = 0, fastHeading = .7, fastSpin = 0;
            bool slowReverse = false, fastReverse = false;
            CasterKinematics.Advance(ref slowHeading, ref slowSpin, ref slowReverse, .00001, 0, 0, 1000, .035, .105, 1);
            CasterKinematics.Advance(ref fastHeading, ref fastSpin, ref fastReverse, 1, 0, 0, .01, .035, .105, 1);
            Near(slowHeading, fastHeading, 1e-12, "steering scales with distance down to 10 micrometres/sec");
            Near(slowSpin, fastSpin, 1e-12, "rolling scales with distance");
            double oldHeading = slowHeading, oldSpin = slowSpin;
            CasterKinematics.Advance(ref slowHeading, ref slowSpin, ref slowReverse, 0, 0, 0, 1000, .035, .105, 1);
            Near(slowHeading, oldHeading, 0, "stationary heading has no drift");
            Near(slowSpin, oldSpin, 0, "stationary spin has no drift");
            heading = spin = 0; reverse = false;
            CasterKinematics.Advance(ref heading, ref spin, ref reverse, -1, 0, 0, .001, .035, .105, 1);
            Require(spin < 0, "reverse begins with signed backwards roll");
            CasterKinematics.Advance(ref heading, ref spin, ref reverse, -1, 0, 0, .8, .035, .105, 1);
            Near(heading, Math.PI, 1e-5, "reverse fork settles to 180 degrees");
            heading = spin = 0; reverse = false;
            CasterKinematics.Advance(ref heading, ref spin, ref reverse, 0, 0, .5, 1, .035, .105, 1);
            Near(heading, -.5, 1e-12, "stationary pivot cancels body yaw");
            Near(spin, 0, 0, "stationary pivot has no spin during body yaw");
            // Analytic straight-path solution tan(theta/2) = tan(theta0/2) exp(-distance/trail).
            heading = .8; spin = 0; reverse = false;
            CasterKinematics.Advance(ref heading, ref spin, ref reverse, .25, 0, 0, .4, .035, .105, 1);
            Near(heading, 2 * Math.Atan(Math.Tan(.4) * Math.Exp(-.1 / .035)), .0003, "analytic trail steering solution");
            Report.AppendLine("Kernel: PASS straight distance/sign, speed scaling, very slow travel, zero drift, reverse, body yaw, analytic steering.");
        }

        private static void CheckImportedRig()
        {
            GameObject asset = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/TABLE-ASTRA-001.fbx");
            Require(asset != null, "validation FBX is present");
            GameObject instance = Object.Instantiate(asset);
            instance.name = asset.name;
            foreach (Transform item in instance.GetComponentsInChildren<Transform>())
                if (item.name.StartsWith("RIG_")) Report.AppendLine("Import " + item.name + " parent=" + item.parent?.name + " scale=" + item.localScale.ToString("F6"));
            var component = instance.AddComponent<TableAstraCasterMotion>();
            Invoke(component, "Awake");
            Require((bool)Get(component, "ready"), "actual imported hierarchy passes runtime rest validation");
            Vector3 up = (Vector3)Get(component, "groundUp");
            var entries = (Array)Get(component, "casters");
            object first = entries.GetValue(0);
            Transform firstSteer = (Transform)GetPublic(first, "steer");
            Transform firstRoll = (Transform)GetPublic(first, "roll");
            Vector3 forward = -Vector3.ProjectOnPlane(firstRoll.position - firstSteer.position, up).normalized;
            float scale = (float)Get(component, "worldScale");
            Report.AppendLine("Actual FBX: up=" + up.ToString("F6") + ", heading=" + forward.ToString("F6") + ", root scale=" + scale);
            foreach (object entry in entries)
            {
                Transform steer = (Transform)GetPublic(entry, "steer");
                Transform roll = (Transform)GetPublic(entry, "roll");
                Report.AppendLine(steer.name + ": trail=" + Vector3.ProjectOnPlane(roll.position-steer.position, up).magnitude.ToString("F6") +
                    ", axle sign=" + GetPublic(entry, "axleSign"));
            }
            for (int i = 0; i < 100; i++)
            {
                instance.transform.position += forward * .01f;
                Invoke(component, "Advance", .01f);
            }
            foreach (object entry in entries)
                Near((double)GetPublic(entry, "spin") * (double)GetPublic(entry, "axleSign") * .105 * scale,
                    1, .00001, "actual imported wheel travels one metre");
            double stationarySpin = (double)GetPublic(first, "spin");
            for (int i = 0; i < 100; i++) Invoke(component, "Advance", .01f);
            Near((double)GetPublic(first, "spin"), stationarySpin, 0, "actual transforms stationary/no drift");
            instance.transform.position += forward * 10;
            Invoke(component, "Advance", .01f);
            Near((double)GetPublic(first, "spin"), stationarySpin, 0, "teleport suppresses phantom travel");
            for (int i = 0; i < 400; i++)
            {
                instance.transform.position -= forward * .002f;
                Invoke(component, "Advance", .01f);
            }
            Near((double)GetPublic(first, "heading"), Math.PI, .0001, "actual imported reverse turns fork 180 degrees");
            Object.DestroyImmediate(instance);

            instance = Object.Instantiate(asset);
            instance.name = asset.name;
            component = instance.AddComponent<TableAstraCasterMotion>();
            Invoke(component, "Awake");
            entries = (Array)Get(component, "casters");
            for (int i = 0; i < 200; i++)
            {
                instance.transform.position += forward * .005f;
                instance.transform.rotation = Quaternion.AngleAxis(.25f, up) * instance.transform.rotation;
                Invoke(component, "Advance", .01f);
            }
            double[] spins = entries.Cast<object>().Select(e => (double)GetPublic(e, "spin")).ToArray();
            Require(spins.Max() - spins.Min() > 1, "turning produces different corner point speeds");
            Require((bool)Get(component, "ready"), "turning keeps valid rig enabled");
            Report.AppendLine("Imported component: PASS one-metre signed roll, stationary hold, teleport, reverse, moving turn with distinct corner speeds.");
            Object.DestroyImmediate(instance);

            instance = Object.Instantiate(asset);
            instance.name = asset.name;
            Rigidbody body = instance.AddComponent<Rigidbody>();
            body.useGravity = false;
            component = instance.AddComponent<TableAstraCasterMotion>();
            Invoke(component, "Awake");
            body.linearVelocity = forward * .5f;
            Physics.SyncTransforms();
            for (int i = 0; i < 10; i++) Invoke(component, "Advance", .01f);
            entries = (Array)Get(component, "casters");
            foreach (object entry in entries)
                Near((double)GetPublic(entry, "spin") * (double)GetPublic(entry, "axleSign") * .105 * scale,
                    .05, .00001, "dynamic Rigidbody point velocity supplies signed travel");
            body.linearVelocity = Vector3.zero;
            body.angularVelocity = up;
            double[] before = entries.Cast<object>().Select(e => (double)GetPublic(e, "spin")).ToArray();
            Invoke(component, "Advance", .001f);
            double[] delta = entries.Cast<object>().Select((e, i) => (double)GetPublic(e, "spin") - before[i]).ToArray();
            Require(delta.Max() - delta.Min() > .001, "Rigidbody angular velocity produces corner-specific rolling");
            Report.AppendLine("Rigidbody: PASS linear and angular GetPointVelocity inputs.");
            Object.DestroyImmediate(instance);
        }

        private static object Get(object value, string name) => value.GetType().GetField(name, PrivateInstance).GetValue(value);
        private static object GetPublic(object value, string name) => value.GetType().GetField(name).GetValue(value);
        private static void Invoke(object value, string name, params object[] args) => value.GetType().GetMethod(name, PrivateInstance).Invoke(value, args);
        private static void Require(bool condition, string reason) { if (!condition) throw new Exception(reason); }
        private static void Near(double actual, double expected, double tolerance, string reason) =>
            Require(!double.IsNaN(actual) && Math.Abs(actual - expected) <= tolerance, reason + ": " + actual + " expected " + expected);
    }
}
#endif
