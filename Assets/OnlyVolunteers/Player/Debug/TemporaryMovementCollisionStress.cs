using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using TheFirstPerson;
using UnityEngine;
using UnityEngine.SceneManagement;

// Temporary, bounded runtime diagnostic for the rejected crouch/ledge behavior.
// Delete after the ControllerTest stress pass.
public sealed class TemporaryMovementCollisionStress : MonoBehaviour
{
    const float Dt = 1f / 60f;
    const BindingFlags PrivateInstance = BindingFlags.Instance | BindingFlags.NonPublic;

    readonly List<string> failures = new List<string>();
    readonly Collider[] nearby = new Collider[64];

    FPSController controller;
    CapsuleCollider capsule;
    Transform cameraTransform;
    MethodInfo updateMovement;
    MethodInfo applyCapsule;
    float maxHorizontalSpeed;
    float maxVerticalSpeed;
    float maxPenetration;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Install()
    {
        if (SceneManager.GetActiveScene().path != "Assets/OnlyVolunteers/Scenes/ControllerTest.unity")
        {
            return;
        }

        new GameObject("[TEMP] Movement Collision Stress")
            .AddComponent<TemporaryMovementCollisionStress>();
    }

    IEnumerator Start()
    {
        // Allow the production controller's Start to build its motor before taking over.
        yield return null;
        yield return null;

        controller = FindFirstObjectByType<FPSController>();
        if (controller == null)
        {
            Debug.LogError("MOVEMENT_STRESS_FAIL: FPSController not found.");
            yield break;
        }

        capsule = controller.GetComponent<CapsuleCollider>();
        cameraTransform = controller.cam;
        updateMovement = typeof(FPSController).GetMethod("UpdateMovement", PrivateInstance);
        applyCapsule = typeof(FPSController).GetMethod("ApplyCapsule", PrivateInstance);
        if (capsule == null || cameraTransform == null || updateMovement == null || applyCapsule == null)
        {
            Debug.LogError("MOVEMENT_STRESS_FAIL: required runtime state/reflection hook missing.");
            yield break;
        }

        controller.enabled = false;
        yield return RunNormalCrouchCamera();
        yield return RunTallSideMiss();
        yield return RunBareLipMiss();
        yield return RunBareLipMake(false);
        yield return RunCornerSlide(false);
        yield return RunCornerSlide(true);
        yield return RunLowCeiling();
        yield return RunBareLipMake(true);
        yield return RunTightContactStress();

        string metrics = $"maxH={maxHorizontalSpeed:F3}, maxV={maxVerticalSpeed:F3}, maxPen={maxPenetration:F5}";
        if (failures.Count == 0)
        {
            Debug.Log("MOVEMENT_STRESS_PASS: side/lip misses fell, lip makes landed once, corners slid, " +
                "low ceiling blocked stand then released, crouch-jump preserved eye continuity; " + metrics);
        }
        else
        {
            Debug.LogError("MOVEMENT_STRESS_FAIL: " + string.Join(" | ", failures) + "; " + metrics);
        }
    }

    IEnumerator RunNormalCrouchCamera()
    {
        ResetController(new Vector3(0f, 0f, 8f), Vector3.forward);
        float previousY = cameraTransform.localPosition.y;
        float largestFrameDelta = 0f;

        for (int i = 0; i < 18; i++)
        {
            SetInput(0f, 0f, true, false);
            Step("grounded crouch");
            largestFrameDelta = Mathf.Max(largestFrameDelta,
                Mathf.Abs(cameraTransform.localPosition.y - previousY));
            previousY = cameraTransform.localPosition.y;
            yield return null;
        }

        if (!controller.IsCrouched || Mathf.Abs(cameraTransform.localPosition.y - controller.crouchedEyeHeight) > 0.02f)
        {
            Fail("grounded crouch did not reach discrete crouched body/eye state");
        }

        for (int i = 0; i < 24; i++)
        {
            SetInput(0f, 0f, false, false);
            Step("grounded stand");
            largestFrameDelta = Mathf.Max(largestFrameDelta,
                Mathf.Abs(cameraTransform.localPosition.y - previousY));
            previousY = cameraTransform.localPosition.y;
            yield return null;
        }

        if (controller.IsCrouched || Mathf.Abs(cameraTransform.localPosition.y - controller.standingEyeHeight) > 0.02f)
        {
            Fail("grounded uncrouch did not complete");
        }
        if (largestFrameDelta > 0.12f)
        {
            Fail($"camera stance transition snapped {largestFrameDelta:F3}m in one 60 Hz frame");
        }
    }

    IEnumerator RunTallSideMiss()
    {
        ResetController(new Vector3(-4f, 0f, 0.3f), Vector3.forward);
        yield return RunUp(20, false);
        SetInput(0f, 1f, false, true);
        Step("tall side jump");
        yield return null;

        bool falseHighSupport = false;
        int airborneStillFrames = 0;
        for (int i = 0; i < 150; i++)
        {
            SetInput(0f, 1f, false, false);
            Step("tall vertical side");
            if (controller.HasValidGroundSupport && controller.transform.position.y > 0.2f)
            {
                falseHighSupport = true;
            }
            if (!controller.HasValidGroundSupport && Mathf.Abs(controller.MeasuredVelocity.y) < 0.2f)
            {
                airborneStillFrames++;
            }
            yield return null;
        }

        if (falseHighSupport)
        {
            Fail("vertical side contact became high support");
        }
        if (!controller.HasValidGroundSupport || controller.transform.position.y > 0.08f)
        {
            Fail("tall side miss did not return ballistically to floor");
        }
        if (airborneStillFrames > 12)
        {
            Fail("tall side miss accumulated an edge hang");
        }
    }

    IEnumerator RunBareLipMiss()
    {
        ResetController(new Vector3(4f, 0f, -11f), Vector3.forward);
        yield return RunUp(20, false);
        SetInput(0f, 1f, false, true);
        Step("lip miss jump");
        yield return null;

        bool landedOnTop = false;
        int consecutiveAirStill = 0;
        int worstAirStill = 0;
        for (int i = 0; i < 150; i++)
        {
            SetInput(0f, 1f, false, false);
            Step("lip miss");
            landedOnTop |= controller.HasValidGroundSupport && controller.transform.position.y > 1f;
            if (!controller.HasValidGroundSupport && controller.MeasuredVelocity.sqrMagnitude < 0.04f)
            {
                consecutiveAirStill++;
                worstAirStill = Mathf.Max(worstAirStill, consecutiveAirStill);
            }
            else
            {
                consecutiveAirStill = 0;
            }
            yield return null;
        }

        if (landedOnTop)
        {
            Fail("1.25m lip miss incorrectly became support");
        }
        if (!controller.HasValidGroundSupport || worstAirStill > 12)
        {
            Fail("bare lip miss hung instead of falling");
        }
    }

    IEnumerator RunBareLipMake(bool crouchInAir)
    {
        ResetController(new Vector3(1f, 0f, -11f), Vector3.forward);
        yield return RunUp(20, false);
        SetInput(0f, 1f, false, true);
        Step(crouchInAir ? "crouch-jump launch" : "lip make launch");
        yield return null;

        float airborneEyeY = cameraTransform.localPosition.y;
        int landingEvents = 0;
        bool previousGrounded = controller.HasValidGroundSupport;
        bool landedOnTop = false;
        bool resizedInAir = false;
        float touchdownEyeY = airborneEyeY;

        for (int i = 0; i < 120; i++)
        {
            bool holdCrouch = crouchInAir && i >= 6;
            SetInput(0f, 1f, holdCrouch, false);
            Step(crouchInAir ? "crouch-jump lip make" : "lip make");

            bool nowGrounded = controller.HasValidGroundSupport;
            if (!nowGrounded && holdCrouch && Mathf.Abs(capsule.height - 2f) > 0.001f)
            {
                resizedInAir = true;
            }
            if (!previousGrounded && nowGrounded)
            {
                landingEvents++;
                touchdownEyeY = cameraTransform.localPosition.y;
                landedOnTop |= controller.transform.position.y > 0.8f;
            }
            previousGrounded = nowGrounded;
            yield return null;

            if (landedOnTop && i > 70)
            {
                break;
            }
        }

        if (!landedOnTop || landingEvents != 1)
        {
            Fail($"{(crouchInAir ? "crouch-jump" : "lip make")} did not produce exactly one top landing ({landingEvents})");
            yield break;
        }

        if (crouchInAir)
        {
            if (resizedInAir)
            {
                Fail("air Ctrl resized the standing capsule");
            }
            if (!controller.IsCrouched || Mathf.Abs(capsule.height - 1.2f) > 0.001f)
            {
                Fail("valid crouch-intent landing did not select the crouched body");
            }
            if (airborneEyeY - touchdownEyeY > 0.09f)
            {
                Fail($"crouch-intent touchdown dropped camera {airborneEyeY - touchdownEyeY:F3}m");
            }

            float holdStart = cameraTransform.localPosition.y;
            for (int i = 0; i < 30; i++)
            {
                SetInput(0f, 0f, true, false);
                Step("crouch landing hold");
                yield return null;
            }
            if (Mathf.Abs(cameraTransform.localPosition.y - holdStart) > 0.08f)
            {
                Fail("held crouch landing started a second eye-height transition");
            }

            for (int i = 0; i < 24; i++)
            {
                SetInput(0f, 0f, false, false);
                Step("crouch landing release");
                yield return null;
            }
            if (controller.IsCrouched || Mathf.Abs(cameraTransform.localPosition.y - controller.standingEyeHeight) > 0.02f)
            {
                Fail("crouch-jump release did not complete one safe stand recovery");
            }
        }
    }

    IEnumerator RunCornerSlide(bool crouched)
    {
        ResetController(new Vector3(-5.9f, 0f, 1.1f), new Vector3(0.45f, 0f, 1f));
        float startX = controller.transform.position.x;
        for (int i = 0; i < 100; i++)
        {
            SetInput(0f, 1f, crouched, false);
            Step(crouched ? "crouched corner" : "standing corner");
            yield return null;
        }

        if (controller.transform.position.x <= startX + 0.25f)
        {
            Fail($"{(crouched ? "crouched" : "standing")} corner contact did not slide tangentially");
        }
        if (!controller.HasValidGroundSupport)
        {
            Fail("grounded corner slide lost floor support");
        }
    }

    IEnumerator RunLowCeiling()
    {
        ResetController(new Vector3(-13.5f, 0f, 3f), Vector3.right);
        for (int i = 0; i < 8; i++)
        {
            SetInput(0f, 0f, true, false);
            Step("enter crouch before overhead");
            yield return null;
        }
        for (int i = 0; i < 32; i++)
        {
            SetInput(0f, 1f, true, false);
            Step("move under overhead");
            yield return null;
        }

        for (int i = 0; i < 20; i++)
        {
            SetInput(0f, 0f, false, false);
            Step("blocked stand");
            yield return null;
        }
        if (!controller.IsCrouched || !controller.IsStandingBlocked || Mathf.Abs(capsule.height - 1.2f) > 0.001f)
        {
            Fail("low ceiling did not retain the complete crouched capsule");
        }

        int firstClearFrame = -1;
        int stoodFrame = -1;
        for (int i = 0; i < 120; i++)
        {
            SetInput(0f, 1f, false, false);
            Step("exit overhead");
            if (firstClearFrame < 0 && controller.transform.position.x > -7.15f)
            {
                firstClearFrame = i;
            }
            if (!controller.IsCrouched)
            {
                stoodFrame = i;
                break;
            }
            yield return null;
        }

        if (stoodFrame < 0)
        {
            Fail("open space never allowed standing after low ceiling");
        }
        else if (firstClearFrame >= 0 && stoodFrame - firstClearFrame > 2)
        {
            Fail($"standing remained delayed {stoodFrame - firstClearFrame} frames after full clearance");
        }
    }

    IEnumerator RunTightContactStress()
    {
        ResetController(new Vector3(-15.2f, 0f, -5.2f), new Vector3(1f, 0f, 0.65f));
        for (int i = 0; i < 240; i++)
        {
            if (i == 60)
            {
                controller.transform.rotation = Quaternion.LookRotation(new Vector3(1f, 0f, -0.5f));
            }
            else if (i == 120)
            {
                controller.transform.rotation = Quaternion.LookRotation(new Vector3(-0.6f, 0f, 1f));
            }
            else if (i == 180)
            {
                controller.transform.rotation = Quaternion.LookRotation(new Vector3(-1f, 0f, -0.4f));
            }

            SetInput(0f, 1f, (i / 30) % 2 == 1, i == 75 || i == 165);
            Step("tight contact stress");
            yield return null;
        }

        if (controller.MeasuredVelocity.magnitude > 55f)
        {
            Fail("tight contact stress ended with a velocity spike");
        }
    }

    IEnumerator RunUp(int frames, bool crouched)
    {
        for (int i = 0; i < frames; i++)
        {
            SetInput(0f, 1f, crouched, false);
            Step("run-up");
            yield return null;
        }
    }

    void ResetController(Vector3 position, Vector3 forward)
    {
        controller.transform.position = new Vector3(0f, 0f, 15f);
        controller.transform.rotation = Quaternion.LookRotation(forward.normalized, Vector3.up);
        Physics.SyncTransforms();
        applyCapsule.Invoke(controller, new object[] { 2f, new Vector3(0f, 1f, 0f) });

        controller.transform.position = position;
        cameraTransform.localPosition = new Vector3(
            cameraTransform.localPosition.x,
            controller.standingEyeHeight,
            cameraTransform.localPosition.z);
        Physics.SyncTransforms();

        SetField("crouching", false);
        SetField("moving", false);
        SetField("running", false);
        SetField("jumpHeld", false);
        SetField("jumpPressed", 0f);
        SetField("xIn", 0f);
        SetField("yIn", 0f);
        SetField("jumping", false);
        SetField("grounded", true);
        SetField("wasGrounded", true);
        SetField("timeSinceGrounded", 0f);
        SetField("yVel", 0f);
        SetField("gravMult", 1f);
        SetField("lastMove", Vector3.zero);
        SetField("currentMove", Vector3.zero);
        SetField("moveDelta", Vector3.zero);
        SetField("lastSaneVelocity", Vector3.zero);
        SetField("physicalCrouched", false);
        SetField("standingBlocked", false);
        SetField("airCrouchLandingIntent", false);
        SetField("crouchLandingVisualHold", false);
        SetField("crouchLandingVisualHoldReleased", false);
        SetField("cameraTransitionInitialized", true);
        SetField("cameraTransitionStartY", controller.standingEyeHeight);
        SetField("cameraTransitionTargetY", controller.standingEyeHeight);
        SetField("cameraTransitionElapsed", 0f);
        SetField("cameraTransitionDuration", 0f);
        SetField("visualStanceCameraY", controller.standingEyeHeight);
        SetField("landingCameraOffset", 0f);
        SetField("landingPhaseStartOffset", 0f);
        SetField("landingPhaseTargetOffset", 0f);
        SetField("landingRecoveryTargetOffset", 0f);
        SetField("landingPhaseElapsed", 0f);
        SetField("landingPhaseDuration", 0f);
        FieldInfo landingPhase = typeof(FPSController).GetField("landingPresentationPhase", PrivateInstance);
        landingPhase.SetValue(controller, Enum.ToObject(landingPhase.FieldType, 0));
    }

    void SetInput(float x, float y, bool crouch, bool jump)
    {
        SetField("xIn", x);
        SetField("yIn", y);
        SetField("moving", new Vector2(x, y).sqrMagnitude > 0.0001f);
        SetField("crouching", crouch);
        SetField("jumpHeld", jump);
        if (jump)
        {
            SetField("jumpPressed", 1f);
        }
    }

    void Step(string context)
    {
        updateMovement.Invoke(controller, new object[] { Dt });
        Physics.SyncTransforms();

        Vector3 velocity = controller.MeasuredVelocity;
        float horizontalSpeed = new Vector2(velocity.x, velocity.z).magnitude;
        maxHorizontalSpeed = Mathf.Max(maxHorizontalSpeed, horizontalSpeed);
        maxVerticalSpeed = Mathf.Max(maxVerticalSpeed, Mathf.Abs(velocity.y));
        if (horizontalSpeed > 9f)
        {
            Fail($"{context} produced {horizontalSpeed:F2}m/s horizontal velocity");
        }
        if (Mathf.Abs(velocity.y) > 50.1f)
        {
            Fail($"{context} produced {velocity.y:F2}m/s vertical velocity");
        }

        CheckPenetration(context);
    }

    void CheckPenetration(string context)
    {
        GetCapsuleWorld(out Vector3 top, out Vector3 bottom, out float radius);
        int count = Physics.OverlapCapsuleNonAlloc(
            top,
            bottom,
            radius + 0.01f,
            nearby,
            Physics.AllLayers,
            QueryTriggerInteraction.Ignore);
        for (int i = 0; i < count; i++)
        {
            Collider other = nearby[i];
            if (other == null || other == capsule || other.transform.IsChildOf(controller.transform))
            {
                continue;
            }
            if (Physics.ComputePenetration(
                capsule, controller.transform.position, controller.transform.rotation,
                other, other.transform.position, other.transform.rotation,
                out _, out float distance))
            {
                maxPenetration = Mathf.Max(maxPenetration, distance);
                if (distance > 0.003f)
                {
                    Fail($"{context} penetrated {other.name} by {distance:F5}m");
                }
            }
        }
    }

    void GetCapsuleWorld(out Vector3 top, out Vector3 bottom, out float radius)
    {
        Vector3 scale = controller.transform.lossyScale;
        radius = capsule.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
        float height = Mathf.Max(capsule.height * Mathf.Abs(scale.y), radius * 2f);
        Vector3 center = controller.transform.position +
            controller.transform.rotation * Vector3.Scale(capsule.center, scale);
        float centerToSphere = Mathf.Max(0f, height * 0.5f - radius);
        top = center + controller.transform.up * centerToSphere;
        bottom = center - controller.transform.up * centerToSphere;
    }

    void SetField(string name, object value)
    {
        FieldInfo field = typeof(FPSController).GetField(name, PrivateInstance);
        if (field == null)
        {
            throw new MissingFieldException(typeof(FPSController).FullName, name);
        }
        field.SetValue(controller, value);
    }

    void Fail(string message)
    {
        if (!failures.Contains(message))
        {
            failures.Add(message);
        }
    }
}
