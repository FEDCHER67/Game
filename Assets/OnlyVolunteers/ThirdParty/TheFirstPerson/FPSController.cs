using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TheFirstPerson.Helper;
using OnlyVolunteers.ThirdParty.OpenKCCAdapted;

namespace TheFirstPerson
{
    public enum ExtFunc
    {
        Start,
        PreUpdate,
        PostUpdate,
        PreFixedUpdate,
        PostFixedUpdate,
        PreMoveCalc,
        PreMove,
        PostMove,
        PostInput
    }

    [RequireComponent(typeof(CharacterController), typeof(CapsuleCollider))]
    public class FPSController : MonoBehaviour
    {

        CharacterController controller;
        CapsuleCollider kinematicCapsule;
        OnlyVolunteersCapsuleMotor capsuleMotor;


        [Header("Options")]
        public bool movementEnabled = true;
        public bool extensionsEnabled = false;
        public bool slopeSlideEnabled = true;
        public bool sprintEnabled = true;
        public bool momentumEnabled = true;
        public bool crouchEnabled = true;
        public bool jumpEnabled = true;
        public bool thirdPersonMode = false;
        [ConditionalHide("thirdPersonMode", true, true)]
        public bool mouseLookEnabled = true;
        [ConditionalHide("thirdPersonMode", true, true)]
        public bool verticalLookEnabled = true;
        public bool customCameraTransform = false;
        public bool customInputNames = false;
        [Range(0f, 1f)]
        [Tooltip("1 is full air control exactly how you control on the ground. 0 is none, you will have no control in the air.")]
        public float airControl = 0.5f;
        public bool airSprintEnabled = true;
        [Tooltip("Legacy compatibility flag. Horizontal movement input is always clamped to magnitude 1.")]
        public bool normaliseMoveInput = false;
        public bool moveInFixedUpdate = false;
        [ConditionalHide(new string[] { "customCameraTransform" , "thirdPersonMode"}, false, false, true)]
        public Transform cam;

        [Header("Jump Settings")]
        [ConditionalHide("jumpEnabled", true)]
        public bool definedByHeight = false;
        [ConditionalHide("jumpEnabled", true)]
        public bool variableHeight = true;
        [ConditionalHide("jumpEnabled", true)]
        [Tooltip("Time in seconds after you leave an edge that you can still jump.")]
        public float coyoteTime = 0.1f;
        [ConditionalHide("jumpEnabled", true)]
        [Tooltip("Time in seconds before you hit the ground where you can press jump to jump when you land.")]
        public float bunnyhopTolerance = 0.1f;
        [ConditionalHide(new string[] { "jumpEnabled", "definedByHeight" }, new bool[] { false, true }, true, false)]
        [Tooltip("Initial in units per second upward velocity of your jump.")]
        public float jumpSpeed = 9;
        [ConditionalHide(new string[] { "jumpEnabled", "definedByHeight" }, new bool[] { false, true }, true, false)]
        [Tooltip("Gravity that is applied on the upward section of your jump. This multiplies the base gravity variable.")]
        public float jumpGravityMult = 0.6f;
        [ConditionalHide(new string[] { "jumpEnabled", "definedByHeight" }, true, false)]
        [Tooltip("Maximum height in units that your jump will reach.")]
        public float maxJumpHeight = 4;
        [ConditionalHide(new string[] { "jumpEnabled", "definedByHeight" }, true, false)]
        [Tooltip("Maximum length of time in seconds your jump will last.")]
        public float maxJumpTime = 1;
        [ConditionalHide(new string[] { "jumpEnabled", "variableHeight", "definedByHeight" }, new bool[]{ false, false, true }, true, false)]
        [Tooltip("Gravity that is applied while you are traveling upwards after you have let go of the jump button. This multiplies the base gravity variable.")]
        public float postJumpGravityMult = 3;
        [ConditionalHide(new string[] { "jumpEnabled", "variableHeight", "definedByHeight" }, new bool[] { false, false, false }, true, false)]
        [Tooltip("Maximum height in units that your jump will reach if you let go of the jump button early.")]
        public float minJumpHeight = 1;
        [ConditionalHide(new string[] { "jumpEnabled", "slopeSlideEnabled" }, true, false)]
        public bool jumpWhileSliding = false;
        [ConditionalHide(new string[] { "jumpEnabled", "slopeSlideEnabled", "jumpWhileSliding" }, true, false)]
        [Tooltip("Force in units per second to be applied to the controller away from the surface of a slope too steep to traverse.")]
        public float slopeJumpKickbackSpeed = 10;

        [Header("Gravity Settings")]
        [Tooltip("Gravity variable this is the change in units per second that will be applied to your y velocity.")]
        public float gravity = 15;
        [Tooltip("Minimum force in units per second pushing you downwards while grounded. This applies on flat ground.")]
        public float baseGroundForce = 3;
        [Tooltip("Maximum force in units per second pushing you downwards while grounded. This applies on steep slopes.")]
        public float maxGroundForce = 30;
        [Tooltip("Maximum downwards velocity in units per second.")]
        public float gravityCap = 50;
        [Tooltip("Base downward velocity applied after walking off an edge in units per second.")]
        public float baseFallVelocity = 5;

        [Header("Air Control Settings")]
        [Tooltip("Speed in units per second that your horizontal velocity returns to 0 in air without any input.")]
        public float airResistance = 4;
        [Tooltip("Speed in units per second that you move forward in the air.")]
        public float airMoveSpeed = 6;
        [Tooltip("Legacy directional multiplier. Air input steers without changing magnitude.")]
        public float airStrafeMult = 1.0f;
        [Tooltip("Legacy directional multiplier. Air input steers without changing magnitude.")]
        public float airBackwardMult = 1.0f;
        [ConditionalHide("airSprintEnabled", true)]
        [Tooltip("Speed that you sprint in the air relative to Air Move Speed.")]
        public float airSprintMult = 2;

        [Header("Speed Settings")]
        [Tooltip("Base forward speed in units per second.")]
        public float moveSpeed = 4.5f;
        [ConditionalHide("slopeSlideEnabled", true)]
        [Tooltip("Horizontal speed while sliding in units per second.")]
        public float slopeSlideSpeed = 10;
        [ConditionalHide("momentumEnabled", true)]
        [Tooltip("Horizontal acceleration in units per second towards target horizontal speed if it is greater than current speed.")]
        public float acceleration = 50;
        [ConditionalHide("momentumEnabled", true)]
        [Tooltip("Horizontal deceleration in units per second towards target horizontal speed if it is less than current speed.")]
        public float deceleration = 40;
        [ConditionalHide("sprintEnabled", true)]
        public bool sprintToggleStyle = false;
        [ConditionalHide("sprintEnabled", true)]
        public bool sprintByDefault = false;
        [ConditionalHide("sprintEnabled", true)]
        [Tooltip("Speed that you sprint relative to Move Speed.")]
        public float sprintMult = 1.75f;
        [Tooltip("Legacy directional multiplier. Cardinal ground movement is kept at equal speed.")]
        public float strafeMult = 1.0f;
        [Tooltip("Legacy directional multiplier. Cardinal ground movement is kept at equal speed.")]
        public float backwardMult = 1.0f;

        [Header("Mouse Look Settings")]
        [Tooltip("Mouse sensitivity.")]
        public float sensitivity = 10;
        [Tooltip("In editor this may not work correctly but it will in build")]
        public bool mouseLockToggleEnabled = true;
        public bool startMouseLock = true;
        [ConditionalHide("verticalLookEnabled", true)]
        [Tooltip("Maximum upward or downward angle of the mouselook camera.")]
        public float verticalLookLimit = 80;

        [Header("CrouchSettings")]
        [ConditionalHide("crouchEnabled", true)]
        public bool crouchToggleStyle = false;
        [ConditionalHide("crouchEnabled", true)]
        [Tooltip("Height of the crouched physical capsule. Kept independent from eye height.")]
        public float crouchColliderHeight = 1.2f;
        [ConditionalHide("crouchEnabled", true)]
        [Tooltip("Horizontal speed when crouched relative to Move Speed.")]
        public float crouchMult = 0.4f;
        [ConditionalHide("crouchEnabled", true)]
        [Tooltip("Speed of transition when crouching down in units per second.")]
        public float crouchTransitionSpeed = 6;
        [ConditionalHide("crouchEnabled", true)]
        [Tooltip("Speed of transition when standing back up on the ground in units per second.")]
        public float standUpTransitionSpeed = 4.2f;
        [ConditionalHide("crouchEnabled", true)]
        public LayerMask crouchHeadHitLayerMask;
        [ConditionalHide("crouchEnabled", true)]
        [Tooltip("Standing first-person eye height. Independent from collider height.")]
        public float standingEyeHeight = 1.8f;
        [ConditionalHide("crouchEnabled", true)]
        [Tooltip("Grounded crouched first-person eye height. Independent from collider height.")]
        public float crouchedEyeHeight = 1.1f;

        [Header("Third Person Options")]
        [ConditionalHide("thirdPersonMode")]
        [Tooltip("Is it possible to walk backwards or should the player turn")]
        public bool walkBackwards = false;
        [ConditionalHide(new string[] { "thirdPersonMode", "walkBackwards" }, true, false)]
        [Tooltip("Is it possible to strafe or should the player turn")]
        public bool strafe = false;
        [ConditionalHide("thirdPersonMode")]
        [Tooltip("Speed of character turning in degrees per second. Set to 0 for instant turning")]
        public float turnSpeed = 360f;
        [ConditionalHide(new string[]{ "thirdPersonMode", "sprintEnabled" },true,false)]
        [Tooltip("Speed that you turn when sprinting relative to Turn Speed.")]
        public float sprintTurnMult = 2.0f;
        [ConditionalHide("thirdPersonMode")]
        [Tooltip("Speed of character aligning to the canera direction in degrees per second. Set to 0 for instant turning")]
        public float cameraAlignSpeed = 0;

        [Header("Input Settings")]
        [Tooltip("If left empty TFP will use its default input system, if you put a TFPInput object in it will use the input functions from that")]
        public TFPInput customInputSystem;
        [ConditionalHide("customInputNames", true)]
        public string jumpBtnCustom = "Jump";
        [ConditionalHide("customInputNames", true)]
        public string crouchBtnCustom = "Fire1";
        [ConditionalHide("customInputNames", true)]
        public string runBtnCustom = "Fire3";
        [ConditionalHide("customInputNames", true)]
        public string unlockMouseBtnCustom = "Cancel";
        [ConditionalHide("customInputNames", true)]
        public string xInNameCustom = "Horizontal";
        [ConditionalHide("customInputNames", true)]
        public string yInNameCustom = "Vertical";
        [ConditionalHide("customInputNames", true)]
        public string xMouseNameCustom = "Mouse X";
        [ConditionalHide("customInputNames", true)]
        public string yMouseNameCustom = "Mouse Y";

        public TFPExtension[] Extensions;

        //Input
        bool moving;
        bool jumpHeld;
        bool crouching;
        bool running;
        bool mouseLocked;
        float jumpPressed;
        float xIn;
        float yIn;
        float xMouse;
        float yMouse;

        //Vertical Movement
        bool jumping;
        bool grounded;
        float timeSinceGrounded;
        float yVel;
        float gravMult = 1;
        float originalMaxJH;
        float originalMinJH;
        float originalJT;
        float minJumpTime;

        //General movement
        Vector3 lastMove;
        Vector3 currentMove;
        Vector3 forward;
        Vector3 side;
        Vector3 moveDelta;
        float currentStrafeMult;
        float currentBackwardMult;
        float currentMoveSpeed;
        bool wasGrounded;
        Vector3 lastSaneVelocity;
        float groundAngle;
        bool instantMomentumChange = false;

        const float CapsuleHeightEpsilon = 0.01f;
        const float MaximumSaneHorizontalSpeed = 50.0f;
        const float MaximumSaneVerticalSpeed = 75.0f;
        float nextVelocityWarningTime;

        //sliding
        bool slide;
        Vector3 hitNormal;
        Vector3 hitPoint;
        Vector3 slideMove;
        RaycastHit ledgeCheck;

        //crouching
        float standingHeight;
        Vector3 standingCenter;
        float capsuleBottomLocalY;
        float cameraOffset;
        bool standingBlocked;
        bool physicalCrouched;
        bool airCrouchLandingIntent;
        bool crouchLandingVisualHold;
        bool crouchLandingVisualHoldReleased;
        bool cameraTransitionInitialized;
        float cameraTransitionStartY;
        float cameraTransitionTargetY;
        float cameraTransitionElapsed;
        float cameraTransitionDuration;
        float visualStanceCameraY;
        float landingCameraOffset;
        float landingPhaseStartOffset;
        float landingPhaseTargetOffset;
        float landingPhaseElapsed;
        float landingPhaseDuration;
        float landingRecoveryTargetOffset;
        LandingPresentationPhase landingPresentationPhase;

        enum LandingPresentationPhase
        {
            None,
            Compression,
            Recovery,
            HoldRelease
        }

        const float GroundProbeDistance = 0.08f;
        const float CrouchCameraDuration = 0.18f;
        const float StandCameraDuration = 0.26f;
        const float LandingCompressionDuration = 0.07f;
        const float LandingRecoveryDuration = 0.24f;
        const float CrouchLandingHoldOffset = 0.045f;

        //third person
        float currentTurnMult;
        float cameraAngle;

        //Input Name Defaults (assuming default unity axes are set up)
        string jumpBtn = "Jump";
        string crouchBtn = "Fire1";
        string runBtn = "Fire3";
        string unlockMouseBtn = "Cancel";
        string xInName = "Horizontal";
        string yInName = "Vertical";
        string xMouseName = "Mouse X";
        string yMouseName = "Mouse Y";

        TFPInfo controllerInfo;

        void Awake()
        {
            InitializeCollisionMotor();
        }

        void InitializeCollisionMotor()
        {
            controller = GetComponent<CharacterController>();
            kinematicCapsule = GetComponent<CapsuleCollider>();
            standingHeight = controller.height;
            standingCenter = controller.center;
            capsuleBottomLocalY = standingCenter.y - (standingHeight * 0.5f);
            cameraOffset = standingHeight - standingEyeHeight;
            crouchColliderHeight = Mathf.Max(crouchColliderHeight, controller.radius * 2f + 0.1f);
            kinematicCapsule.direction = 1;
            kinematicCapsule.radius = controller.radius;
            kinematicCapsule.height = controller.height;
            kinematicCapsule.center = controller.center;
            kinematicCapsule.isTrigger = false;
            controller.enabled = false;
            capsuleMotor = new OnlyVolunteersCapsuleMotor(
                transform,
                kinematicCapsule,
                controller.skinWidth,
                controller.slopeLimit,
                GetEnvironmentLayerMask());
        }

        void Start()
        {
            // Keep this idempotent for editor domain/play-mode configurations that can clear
            // non-serialized runtime state without reconstructing the scene object.
            if (capsuleMotor == null)
            {
                InitializeCollisionMotor();
            }
            //get the transform of a child with a camera component
            if (!customCameraTransform && !thirdPersonMode)
            {
                cam = transform.GetComponentInChildren<Camera>().transform;
            }

            physicalCrouched = controller.height < standingHeight - CapsuleHeightEpsilon;
            lastSaneVelocity = Vector3.zero;
            cameraTransitionStartY = cam.localPosition.y;
            cameraTransitionTargetY = cam.localPosition.y;
            visualStanceCameraY = cam.localPosition.y;
            cameraTransitionInitialized = true;
            grounded = capsuleMotor.TryGetGround(GroundProbeDistance, out _);
            wasGrounded = grounded;

            //Handle custom input names
            if (customInputNames)
            {
                jumpBtn = jumpBtnCustom;
                crouchBtn = crouchBtnCustom;
                runBtn = runBtnCustom;
                unlockMouseBtn = unlockMouseBtnCustom;
                xInName = xInNameCustom;
                yInName = yInNameCustom;
                xMouseName = xMouseNameCustom;
                yMouseName = yMouseNameCustom;
            }
            if (customInputSystem != null && customInputSystem.useFPSControllerAxisNames)
            {
                customInputSystem.SetAxisNames(jumpBtn, crouchBtn, runBtn, unlockMouseBtn, xInName, yInName, xMouseName, yMouseName);
            }

            if (sprintByDefault)
            {
                running = true;
            }

            if (definedByHeight)
            {
                RecalculateJumpValues();
                originalJT = maxJumpTime;
                originalMaxJH = maxJumpHeight;
                originalMinJH = minJumpHeight;
            }

            cameraAngle = cam.eulerAngles.y;
            mouseLocked = startMouseLock;

            controllerInfo = GetInfo();
            ExecuteExtension(ExtFunc.Start);
        }

        void Update()
        {
            if(definedByHeight && (originalJT != maxJumpTime || originalMaxJH != maxJumpHeight || originalMinJH != minJumpHeight))
            {
                RecalculateJumpValues();
                originalJT = maxJumpTime;
                originalMaxJH = maxJumpHeight;
                originalMinJH = minJumpHeight;
            }


            ExecuteExtension(ExtFunc.PreUpdate);
            if (movementEnabled)
            {
                UpdateInput();
            }

            UpdateMouseLock();
            ExecuteExtension(ExtFunc.PostInput);
            if (thirdPersonMode && movementEnabled)
            {
                ThirdPersonSteering();
            }
            else
            {
                if (mouseLocked)
                {
                    MouseLook();
                }
            }
            if (!moveInFixedUpdate && movementEnabled)
            {
                UpdateMovement(Time.deltaTime);
            }
            ExecuteExtension(ExtFunc.PostUpdate);
        }

        void FixedUpdate()
        {
            ExecuteExtension(ExtFunc.PreFixedUpdate);
            if (moveInFixedUpdate && movementEnabled)
            {
                UpdateMovement(Time.deltaTime);
            }
            ExecuteExtension(ExtFunc.PostFixedUpdate);
        }

        void UpdateMovement(float dt)
        {
            if (dt > 0)
            {
                if (capsuleMotor == null)
                {
                    InitializeCollisionMotor();
                }
                forward = transform.forward;
                side = transform.right;
                currentMove = Vector3.zero;
                lastMove = SanitizeVelocity(lastMove, "stored measured velocity", true);
                yVel = SanitizeVerticalVelocity(yVel, "stored vertical velocity");
                wasGrounded = grounded;
                float preSupportVerticalVelocity = yVel;
                RaycastHit supportHit = new RaycastHit();
                grounded = !(jumping && yVel > 0f) &&
                    capsuleMotor.TryGetGround(GroundProbeDistance, out supportHit);
                if (grounded)
                {
                    hitNormal = supportHit.normal;
                    hitPoint = supportHit.point;
                    groundAngle = Vector3.Angle(hitNormal, Vector3.up);
                }
                // Jump is a single fresh press edge consumed exactly once here. It is never
                // buffered, never carried into the air, and holding the key never retriggers it.
                bool jumpEdge = jumpPressed > 0f;
                jumpPressed = 0f;
                slideMove = Vector3.zero;
                Vector3 lastMoveH = Vector3.Scale(lastMove, new Vector3(1, 0, 1));

                bool justLeftGround = wasGrounded && !grounded;
                bool justLandedBeforeMove = !wasGrounded && grounded;

                bool crouchIntentLanding = UpdatePhysicalStance(justLandedBeforeMove);

                setCurrentMoveVars();
                ExecuteExtension(ExtFunc.PreMoveCalc);
                Vector3 targetMove = GetHorizontalMove();

                if (slide && !grounded && timeSinceGrounded < coyoteTime)
                {
                    timeSinceGrounded = coyoteTime;
                    slide = true;
                }

                if (grounded && groundAngle >= controller.slopeLimit && slopeSlideEnabled)
                {
                    if (Physics.Raycast(transform.position, Vector3.down, out ledgeCheck, 0.1f + (controller.radius * 2)))
                    {
                        if (Vector3.Angle(ledgeCheck.normal, Vector3.up) >= controller.slopeLimit)
                        {
                            slide = true;
                        }
                        else
                        {
                            slide = false;
                        }
                    }
                    else if (Physics.Raycast(transform.position + (controller.radius * Vector3.up), new Vector3(hitPoint.x, transform.position.y, hitPoint.z) - transform.position, out ledgeCheck, 0.1f + (controller.radius * 2)))
                    {
                        if (Vector3.Angle(ledgeCheck.normal, Vector3.up) >= controller.slopeLimit)
                        {
                            slide = true;
                        }
                        else
                        {
                            slide = false;
                        }
                    }
                    else
                    {
                        slide = false;
                        groundAngle = 0;
                    }
                }
                else
                {
                    slide = false;
                }

                if (slide)
                {
                    slideMove = new Vector3(hitNormal.x, -hitNormal.y, hitNormal.z);
                    Vector3.OrthoNormalize(ref hitNormal, ref slideMove);
                    Vector3 slideMoveh = Vector3.Scale(slideMove, new Vector3(1, 0, 1)).normalized * (slopeSlideSpeed * (1 - groundAngle / 90));
                    if (Vector3.Angle(targetMove, slideMoveh) > 100)
                    {
                        targetMove = slideMoveh;
                    }
                    else
                    {
                        targetMove += slideMoveh;
                    }
                    if (jumpEnabled && jumpWhileSliding)
                    {
                        if (jumpPressed > 0)
                        {
                            targetMove = slideMoveh.normalized * slopeJumpKickbackSpeed;
                            instantMomentumChange = true;
                        }
                    }
                }

                if (grounded)
                {
                    // Accepting a jump freezes the actual horizontal displacement velocity
                    // from the preceding grounded step before this frame's input, sprint, or
                    // diagonal target can accelerate it. Jump itself only assigns yVel.
                    bool jumpAccepted = jumpEnabled && jumpEdge && !slide && !crouching && controller.height >= standingHeight - CapsuleHeightEpsilon;
                    if (jumpAccepted)
                    {
                        currentMove = lastMoveH;
                    }
                    else if (momentumEnabled && !instantMomentumChange)
                    {
                        if (moving || targetMove.magnitude < lastMoveH.magnitude)
                        {
                            currentMove = Vector3.MoveTowards(lastMoveH, targetMove, dt * deceleration);
                        }
                        else
                        {
                            currentMove = Vector3.MoveTowards(lastMoveH, targetMove, dt * acceleration);
                        }
                    }
                    else
                    {
                        currentMove = targetMove;
                    }
                    timeSinceGrounded = 0;
                    jumping = false;
                    if (jumpAccepted)
                    {
                        Jump();
                        grounded = false;
                    }
                    else
                    {
                        var targetYVel = -baseGroundForce + (-maxGroundForce * (groundAngle / 90.0f));
                        if (lastMove.y < 0)
                        {
                            yVel = Mathf.Lerp(lastMove.y, targetYVel, gravity * dt);
                        }
                        else
                        {
                            yVel = targetYVel;
                        }
                    }
                }
                else
                {
                    if (moving)
                    {
                        float availableMagnitude = lastMoveH.magnitude;
                        Vector3 steeredTarget = targetMove.sqrMagnitude > 0.0001f
                            ? targetMove.normalized * Mathf.Min(targetMove.magnitude, availableMagnitude)
                            : Vector3.zero;
                        currentMove = Vector3.Lerp(lastMoveH, steeredTarget, airControl);
                        currentMove = Vector3.ClampMagnitude(currentMove, availableMagnitude);
                    }
                    else
                    {
                        currentMove = Vector3.MoveTowards(lastMoveH, targetMove, airResistance * dt);
                    }
                    if (justLeftGround && !jumping)
                    {
                        // Walking off a ledge begins from the measured vertical velocity.
                        // Do not replace it with baseFallVelocity, which caused the visible
                        // pause followed by a sudden fast drop after edge contacts.
                        yVel = Mathf.Min(0f, lastMove.y);
                    }
                    yVel -= gravity * gravMult * dt;
                    if (yVel < -gravityCap)
                    {
                        yVel = -gravityCap;
                    }

                    timeSinceGrounded += dt;
                }

                ExecuteExtension(ExtFunc.PreMove);

                currentMove += Vector3.up * yVel;
                currentMove = SanitizeVelocity(currentMove, "movement command", false);
                yVel = currentMove.y;
                moveDelta = transform.position;
                CapsuleMotorMoveResult motorResult = capsuleMotor.Move(currentMove * dt);
                moveDelta = motorResult.ResolvedDisplacement;

                if (motorResult.HitCeiling && yVel > 0f)
                {
                    yVel = 0f;
                }

                RaycastHit postMoveSupport = new RaycastHit();
                bool hasPostMoveSupport = yVel <= 0f &&
                    capsuleMotor.TryGetGround(GroundProbeDistance, out postMoveSupport);
                bool groundedAfterMove = yVel <= 0f &&
                    (motorResult.HitGround || hasPostMoveSupport);
                bool justLanded = justLandedBeforeMove || (!wasGrounded && groundedAfterMove);
                grounded = groundedAfterMove;

                if (grounded)
                {
                    RaycastHit finalSupport = hasPostMoveSupport ? postMoveSupport : supportHit;
                    hitNormal = finalSupport.normal.sqrMagnitude > 0f
                        ? finalSupport.normal
                        : Vector3.up;
                    hitPoint = finalSupport.point;
                    groundAngle = Vector3.Angle(hitNormal, Vector3.up);
                    jumping = false;
                    timeSinceGrounded = 0f;
                }

                if (justLanded && !justLandedBeforeMove)
                {
                    crouchIntentLanding = UpdatePhysicalStance(true);
                }

                lastMove = SanitizeVelocity(moveDelta / dt, "measured displacement velocity", true);
                UpdateCameraPresentation(dt, justLanded, preSupportVerticalVelocity, crouchIntentLanding);
                instantMomentumChange = false;
                ExecuteExtension(ExtFunc.PostMove);
            }
        }

        bool UpdatePhysicalStance(bool justLanded)
        {
            // Airborne capsule resizing is deliberately disabled. An airborne Ctrl press has
            // no effect on capsule, camera, velocity, gravity, or ground state. A capsule that
            // leaves a ledge crouched remains unchanged until valid support is reacquired.
            if (!grounded)
            {
                standingBlocked = false;
                airCrouchLandingIntent = crouchEnabled && crouching && !physicalCrouched;
                return false;
            }

            bool wantsCrouch = crouchEnabled && crouching;
            standingBlocked = false;
            // Input is sampled before movement. If Ctrl is held on the confirmed
            // AIR -> GROUND frame, it is a landing request even when it was pressed during
            // the final render frame before support confirmation.
            bool crouchIntentLanding = justLanded && wantsCrouch && !physicalCrouched;

            if (wantsCrouch)
            {
                if (!physicalCrouched)
                {
                    // Crouching is a single bottom-anchored transaction. There are no
                    // half-height collision states for a ledge to hold onto.
                    ApplyBottomAnchoredCapsule(crouchColliderHeight);
                    physicalCrouched = true;
                }

                if (crouchIntentLanding)
                {
                    // The collision stance changes at valid support, but presentation keeps
                    // the airborne eye line. The landing response supplies the only settle.
                    crouchLandingVisualHold = true;
                    CancelVisualStanceTransitionAtCurrentHeight();
                }
            }
            else if (physicalCrouched)
            {
                if (capsuleMotor.CanOccupy(standingHeight, standingCenter))
                {
                    // Standing is also transactional: test the complete final capsule, then
                    // switch once. Failure leaves the known-safe crouched capsule unchanged.
                    ApplyCapsule(standingHeight, standingCenter);
                    physicalCrouched = false;
                    if (crouchLandingVisualHold)
                    {
                        crouchLandingVisualHold = false;
                        crouchLandingVisualHoldReleased = true;
                    }
                }
                else
                {
                    standingBlocked = true;
                }
            }
            else
            {
                ApplyCapsule(standingHeight, standingCenter);
            }

            airCrouchLandingIntent = false;
            return crouchIntentLanding;
        }

        void ApplyBottomAnchoredCapsule(float height)
        {
            ApplyCapsule(height, GetBottomAnchoredCenter(height));
        }

        void ApplyCapsule(float height, Vector3 center)
        {
            if (Mathf.Abs(kinematicCapsule.height - height) <= CapsuleHeightEpsilon &&
                (kinematicCapsule.center - center).sqrMagnitude <= CapsuleHeightEpsilon * CapsuleHeightEpsilon)
            {
                return;
            }

            capsuleMotor.SetShape(height, center);
            controller.height = height;
            controller.center = center;
        }

        Vector3 GetBottomAnchoredCenter(float height)
        {
            return new Vector3(
                standingCenter.x,
                capsuleBottomLocalY + (height * 0.5f),
                standingCenter.z);
        }

        void CancelVisualStanceTransitionAtCurrentHeight()
        {
            cameraTransitionInitialized = true;
            cameraTransitionStartY = visualStanceCameraY;
            cameraTransitionTargetY = visualStanceCameraY;
            cameraTransitionElapsed = 0f;
            cameraTransitionDuration = 0f;
        }

        void UpdateCameraPresentation(
            float dt,
            bool justLanded,
            float preSupportVerticalVelocity,
            bool crouchIntentLanding)
        {
            if (!mouseLookEnabled || thirdPersonMode || cam == null)
            {
                return;
            }

            float crouchedCameraY = crouchedEyeHeight;
            float standingCameraY = standingEyeHeight;

            if (grounded && !crouchLandingVisualHold)
            {
                float targetCameraY = physicalCrouched ? crouchedCameraY : standingCameraY;
                BeginVisualStanceTransition(
                    targetCameraY,
                    targetCameraY < visualStanceCameraY
                    ? CrouchCameraDuration
                    : StandCameraDuration);
            }

            if (justLanded)
            {
                StartLandingPresentation(
                    -preSupportVerticalVelocity,
                    crouchIntentLanding || crouchLandingVisualHold);
            }
            if (crouchLandingVisualHoldReleased)
            {
                crouchLandingVisualHoldReleased = false;
                if (!justLanded)
                {
                    BeginLandingOffsetPhase(
                        LandingPresentationPhase.HoldRelease,
                        0f,
                        StandCameraDuration);
                }
            }

            UpdateVisualStanceTransition(dt);
            UpdateLandingPresentation(dt);

            // This is the sole camera-Y write. Physical stance, support, and landing never
            // write the camera independently; their presentation values compose here.
            float cameraY = visualStanceCameraY + landingCameraOffset;
            cam.localPosition = new Vector3(cam.localPosition.x, cameraY, cam.localPosition.z);
        }

        void BeginVisualStanceTransition(float targetY, float duration)
        {
            if (cameraTransitionInitialized &&
                Mathf.Abs(targetY - cameraTransitionTargetY) <= 0.001f)
            {
                return;
            }

            cameraTransitionInitialized = true;
            cameraTransitionStartY = visualStanceCameraY;
            cameraTransitionTargetY = targetY;
            cameraTransitionElapsed = 0f;
            cameraTransitionDuration = duration;
        }

        void UpdateVisualStanceTransition(float dt)
        {
            if (!cameraTransitionInitialized)
            {
                return;
            }

            cameraTransitionElapsed += dt;
            float progress = cameraTransitionDuration > 0f
                ? Mathf.Clamp01(cameraTransitionElapsed / cameraTransitionDuration)
                : 1f;
            visualStanceCameraY = Mathf.Lerp(
                cameraTransitionStartY,
                cameraTransitionTargetY,
                SmootherStep(progress));
        }

        void StartLandingPresentation(float impactSpeed, bool settleIntoCrouchHold)
        {
            float impact01 = Mathf.InverseLerp(3f, 14f, Mathf.Max(0f, impactSpeed));
            float compression = Mathf.Lerp(0.018f, 0.065f, impact01);
            float settledOffset = settleIntoCrouchHold ? -CrouchLandingHoldOffset : 0f;
            float peakOffset = -Mathf.Max(compression,
                settleIntoCrouchHold ? CrouchLandingHoldOffset + 0.012f : 0f);

            landingPhaseStartOffset = landingCameraOffset;
            landingPhaseTargetOffset = peakOffset;
            landingPhaseElapsed = 0f;
            landingPhaseDuration = LandingCompressionDuration;
            landingPresentationPhase = LandingPresentationPhase.Compression;

            // Stored now so Recovery has one deterministic destination and cannot restart
            // from stance changes on later frames.
            landingRecoveryTargetOffset = settledOffset;
        }

        void BeginLandingOffsetPhase(
            LandingPresentationPhase phase,
            float targetOffset,
            float duration)
        {
            landingPresentationPhase = phase;
            landingPhaseStartOffset = landingCameraOffset;
            landingPhaseTargetOffset = targetOffset;
            landingPhaseElapsed = 0f;
            landingPhaseDuration = duration;
        }

        void UpdateLandingPresentation(float dt)
        {
            if (landingPresentationPhase == LandingPresentationPhase.None)
            {
                return;
            }

            landingPhaseElapsed += dt;
            float progress = landingPhaseDuration > 0f
                ? Mathf.Clamp01(landingPhaseElapsed / landingPhaseDuration)
                : 1f;
            landingCameraOffset = Mathf.Lerp(
                landingPhaseStartOffset,
                landingPhaseTargetOffset,
                SmootherStep(progress));

            if (progress < 1f)
            {
                return;
            }

            if (landingPresentationPhase == LandingPresentationPhase.Compression)
            {
                BeginLandingOffsetPhase(
                    LandingPresentationPhase.Recovery,
                    landingRecoveryTargetOffset,
                    LandingRecoveryDuration);
            }
            else
            {
                landingPresentationPhase = LandingPresentationPhase.None;
            }
        }

        static float SmootherStep(float value)
        {
            value = Mathf.Clamp01(value);
            return value * value * value * (value * ((6f * value) - 15f) + 10f);
        }

        int GetEnvironmentLayerMask()
        {
            // Query every layer the CharacterController can collide with. The player and
            // environment may share a layer, so self is rejected per collider below.
            int mask = Physics.AllLayers;
            for (int layer = 0; layer < 32; layer++)
            {
                if (Physics.GetIgnoreLayerCollision(gameObject.layer, layer))
                {
                    mask &= ~(1 << layer);
                }
            }
            return mask;
        }

        Vector3 SanitizeVelocity(Vector3 velocity, string context, bool updateLastSane)
        {
            bool invalidHorizontal = !IsFinite(velocity.x) || !IsFinite(velocity.z) ||
                ((velocity.x * velocity.x) + (velocity.z * velocity.z)) >
                (MaximumSaneHorizontalSpeed * MaximumSaneHorizontalSpeed);
            bool invalidVertical = !IsFinite(velocity.y) || Mathf.Abs(velocity.y) > MaximumSaneVerticalSpeed;

            if (invalidHorizontal)
            {
                velocity.x = lastSaneVelocity.x;
                velocity.z = lastSaneVelocity.z;
            }
            if (invalidVertical)
            {
                velocity.y = lastSaneVelocity.y;
            }

            if (invalidHorizontal || invalidVertical)
            {
                WarnAboutCorruptVelocity(context, invalidHorizontal, invalidVertical);
            }

            if (updateLastSane)
            {
                lastSaneVelocity = velocity;
            }
            return velocity;
        }

        float SanitizeVerticalVelocity(float velocity, string context)
        {
            Vector3 sanitized = SanitizeVelocity(new Vector3(0f, velocity, 0f), context, false);
            return sanitized.y;
        }

        static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        [System.Diagnostics.Conditional("UNITY_EDITOR")]
        [System.Diagnostics.Conditional("DEVELOPMENT_BUILD")]
        void WarnAboutCorruptVelocity(string context, bool horizontal, bool vertical)
        {
            if (Time.unscaledTime < nextVelocityWarningTime)
            {
                return;
            }

            nextVelocityWarningTime = Time.unscaledTime + 1.0f;
            Debug.LogWarning(
                $"FPSController rejected corrupt {context} " +
                $"(horizontal={horizontal}, vertical={vertical}) and restored the last sane component.",
                this);
        }

        public Vector3 MeasuredVelocity => lastMove;
        public bool HasValidGroundSupport => grounded;
        public bool IsCrouched => physicalCrouched;
        public bool HasCrouchLandingIntent => airCrouchLandingIntent;
        public bool IsStandingBlocked => standingBlocked;

        void setCurrentMoveVars()
        {
            currentTurnMult = 1.0f;
            if (grounded)
            {
                currentMoveSpeed = moveSpeed;
                currentStrafeMult = 1.0f;
                currentBackwardMult = 1.0f;
                bool crouchActive = crouchEnabled &&
                    (crouching || controller.height < standingHeight - CapsuleHeightEpsilon);
                if (crouchActive)
                {
                    currentMoveSpeed *= crouchMult;
                }
                else if (running && sprintEnabled)
                {
                    if (thirdPersonMode)
                    {
                        currentTurnMult *= sprintTurnMult;
                    }
                    currentMoveSpeed *= sprintMult;
                }
            }
            else
            {
                // Air input can steer only the horizontal magnitude that survived the last
                // cast-resolved movement. It cannot regenerate speed removed by a wall,
                // corner, or other collision, and Shift never retargets it.
                currentMoveSpeed = Vector3.Scale(lastMove, new Vector3(1f, 0f, 1f)).magnitude;
                currentStrafeMult = 1.0f;
                currentBackwardMult = 1.0f;

                // Fixed gravity while airborne: holding jump never changes gravity or velocity.
                gravMult = 1.0f;
            }
        }

        Vector3 GetHorizontalMove()
        {
            if (!moving)
            {
                return Vector3.zero;
            }

            Vector2 input = Vector2.ClampMagnitude(new Vector2(xIn, yIn), 1.0f);
            float inputMagnitude = input.magnitude;
            Vector3 targetDirection;

            if (thirdPersonMode && (!walkBackwards && !strafe))
            {
                targetDirection = forward * (walkBackwards ? Mathf.Sign(input.y) : 1f);
            }
            else
            {
                // All four cardinal directions have the same target magnitude. The input is
                // clamped first and the final direction is normalized before the deliberate
                // grounded diagonal bonus is applied.
                targetDirection = (forward * input.y) + (side * input.x);
            }

            if (targetDirection.sqrMagnitude < 0.0001f)
            {
                return Vector3.zero;
            }

            float targetSpeed = currentMoveSpeed * inputMagnitude;
            if (grounded)
            {
                bool fullDiagonal = Mathf.Abs(input.x) > 0.1f && Mathf.Abs(input.y) > 0.1f;
                if (fullDiagonal)
                {
                    targetSpeed *= 1.05f;
                }
            }

            // In air targetSpeed is exactly the cast-resolved horizontal magnitude from the
            // previous movement (scaled only by analog input), so WASD and Shift cannot add
            // speed removed by a collision.
            return targetDirection.normalized * targetSpeed;
        }

        void Jump()
        {
            jumping = true;
            // The one and only positive launch assignment; the jump edge is already consumed.
            yVel = jumpSpeed;
        }

        void UpdateMouseLock()
        {
            if (mouseLockToggleEnabled && Time.timeScale > 0)
            {
                if (customInputSystem == null ? Input.GetButtonDown(unlockMouseBtn) : customInputSystem.UnlockMouseButton())
                {
                    mouseLocked = false;
                }
                else if (customInputSystem == null ? Input.GetMouseButtonDown(0) : customInputSystem.MousePressed())
                {
                    mouseLocked = true;
                }
            }

            if (mouseLocked)
            {
                Cursor.lockState = CursorLockMode.Locked;
                Cursor.visible = false;
            }
            else
            {
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }

        }

        void MouseLook()
        {
            if (mouseLookEnabled)
            {
                float horizontalLook = transform.localEulerAngles.y;
                float verticalLook = cam.localEulerAngles.x;

                horizontalLook += xMouse * sensitivity;

                if (verticalLookEnabled)
                {
                    verticalLook -= yMouse * sensitivity;
                    if (verticalLook > verticalLookLimit && verticalLook < 180)
                    {
                        verticalLook = verticalLookLimit;
                    }
                    else if (verticalLook > 180 && verticalLook < 360 - verticalLookLimit)
                    {
                        verticalLook = 360 - verticalLookLimit;
                    }

                    cam.localEulerAngles = new Vector3(verticalLook, 0, 0);
                }

                transform.localEulerAngles = new Vector3(0, horizontalLook, 0);
            }
        }

        void ThirdPersonSteering()
        {
            bool snap = Mathf.Abs(lastMove.x) + Mathf.Abs(lastMove.x) < Time.deltaTime * currentMoveSpeed * 0.5f;
            Vector3 inputDir = new Vector3(xIn, 0, yIn);
            if (walkBackwards && yIn < 0)
            {
                inputDir = new Vector3(-xIn, 0, -yIn);
            }

            if (inputDir.magnitude > 0.01f)
            {
                if (cameraAlignSpeed > 0 && !snap)
                {
                    cameraAngle = Mathf.MoveTowardsAngle(cameraAngle, cam.eulerAngles.y, Time.deltaTime * cameraAlignSpeed);
                }
                else
                {
                    cameraAngle = cam.eulerAngles.y;
                }
                float targetAngle = 0;
                if (walkBackwards && strafe)
                {
                    targetAngle = Mathf.Atan2(0, inputDir.z) * Mathf.Rad2Deg + cameraAngle;
                }
                else
                {
                    targetAngle = Mathf.Atan2(inputDir.x, inputDir.z) * Mathf.Rad2Deg + cameraAngle;
                }
                if (turnSpeed != 0 && !snap)
                {
                    float finalAngle = Mathf.MoveTowardsAngle(transform.eulerAngles.y, targetAngle, turnSpeed * currentTurnMult * Time.deltaTime);
                    transform.eulerAngles = new Vector3(0, finalAngle, 0);
                }
                else
                {
                    transform.eulerAngles = new Vector3(0, targetAngle, 0);
                }
            }
        }

        void UpdateInput()
        {
            bool standard = customInputSystem == null;
            xIn = standard ? Input.GetAxisRaw(xInName) : customInputSystem.XAxis();
            yIn = standard ? Input.GetAxisRaw(yInName) : customInputSystem.YAxis();
            // Movement always uses a clamped two-axis vector. The legacy inspector flag is
            // retained for data compatibility but cannot re-enable the sqrt(2) diagonal.
            Vector2 normalised = Vector2.ClampMagnitude(new Vector2(xIn, yIn), 1.0f);
            xIn = normalised.x;
            yIn = normalised.y;
            xMouse = standard ? Input.GetAxis(xMouseName) : customInputSystem.XMouse();
            yMouse = standard ? Input.GetAxis(yMouseName) : customInputSystem.YMouse();
            moving = Mathf.Abs(xIn) > 0.1 || Mathf.Abs(yIn) > 0.1;
            if (crouchToggleStyle)
            {
                if (standard ? Input.GetButtonDown(crouchBtn) : customInputSystem.CrouchPressed())
                {
                    crouching = !crouching;
                }
            }
            else
            {
                crouching = standard ? Input.GetButton(crouchBtn) : customInputSystem.CrouchHeld();
            }
            bool runPressed = standard ? Input.GetButtonDown(runBtn) || Input.GetAxisRaw(runBtn) > 0.1f : customInputSystem.RunPressed();
            bool runHeld = standard ? Input.GetButton(runBtn) || Input.GetAxisRaw(runBtn) > 0.1f : customInputSystem.RunHeld();
            if (sprintToggleStyle)
            {
                if (runPressed)
                {
                    running = !running;
                }
            }
            else if (sprintByDefault)
            {
                running = !runHeld;
            }
            else
            {
                running = runHeld;
            }
            jumpHeld = standard ? Input.GetButton(jumpBtn) : customInputSystem.JumpHeld();
            if (standard ? Input.GetButtonDown(jumpBtn) : customInputSystem.JumpPressed())
            {
                // One-frame edge flag only; the movement step consumes it immediately.
                jumpPressed = 1f;
            }
        }

        void RecalculateJumpValues()
        {
            jumpGravityMult = ((2 * maxJumpHeight) / Mathf.Pow(maxJumpTime, 2)) / gravity;
            jumpSpeed = (2 * maxJumpHeight) / maxJumpTime;
            minJumpTime = (2 * minJumpHeight) / jumpSpeed;
            postJumpGravityMult = ((2 * minJumpHeight) / Mathf.Pow(minJumpTime, 2)) / gravity;
        }

#if UNITY_EDITOR
        private void OnDrawGizmosSelected()
        {
            if (controller == null)
            {
                controller = gameObject.GetComponent<CharacterController>();
            }
            Vector3 pos = transform.position + controller.center;
            GizmoUtilities.DrawWireCapsule(pos, Quaternion.identity, controller.radius + controller.skinWidth, controller.height + (2*controller.skinWidth), Color.cyan);
            Gizmos.color = Color.red;
            Gizmos.DrawLine(transform.position + new Vector3(-controller.radius, controller.stepOffset,0), transform.position + new Vector3(controller.radius, controller.stepOffset, 0));
            Gizmos.DrawLine(transform.position + new Vector3(0, controller.stepOffset, -controller.radius), transform.position + new Vector3(0, controller.stepOffset, controller.radius));
        }
#endif

        TFPData GetData()
        {
            return new TFPData(movementEnabled, moving, jumpHeld, crouching, running, mouseLocked, mouseLookEnabled,
                jumpPressed, xIn, yIn, xMouse, yMouse, jumping, grounded, timeSinceGrounded, yVel, slide,
                gravMult, currentStrafeMult, currentBackwardMult, currentMoveSpeed, groundAngle,
                lastMove, currentMove, forward, side, moveDelta, hitNormal, hitPoint, slideMove,
                standingHeight, cameraOffset);
        }

        TFPInfo GetInfo()
        {
            return new TFPInfo(controller, cam, extensionsEnabled, slopeSlideEnabled,
                sprintEnabled, momentumEnabled, crouchEnabled, jumpEnabled, verticalLookEnabled,
                customInputNames, airControl, airSprintEnabled, jumpSpeed, variableHeight, coyoteTime,
                bunnyhopTolerance, jumpGravityMult, postJumpGravityMult, jumpWhileSliding, slopeJumpKickbackSpeed,
                gravity, baseGroundForce, maxGroundForce, gravityCap, baseFallVelocity, airResistance,
                airMoveSpeed, airStrafeMult, airBackwardMult, airSprintMult, moveSpeed, slopeSlideSpeed,
                acceleration, deceleration, sprintMult, strafeMult, backwardMult, sensitivity, verticalLookLimit,
                crouchToggleStyle, crouchColliderHeight, crouchMult, crouchTransitionSpeed, crouchHeadHitLayerMask,
                jumpBtn, crouchBtn, runBtn, unlockMouseBtn, xInName, yInName, xMouseName, yMouseName,
                mouseLookEnabled, customCameraTransform, normaliseMoveInput, moveInFixedUpdate, definedByHeight,
                maxJumpHeight, maxJumpTime, minJumpHeight, sprintToggleStyle, sprintByDefault, mouseLockToggleEnabled,
                startMouseLock);
        }

        void SetData(TFPData newData)
        {
            movementEnabled = newData.movementEnabled;
            moving = newData.moving;
            jumpHeld = newData.jumpHeld;
            crouching = newData.crouching;
            running = newData.running;
            mouseLocked = newData.mouseLocked;
            mouseLookEnabled = newData.mouseLookEnabled;
            jumpPressed = newData.jumpPressed;
            xIn = newData.xIn;
            yIn = newData.yIn;
            xMouse = newData.xMouse;
            yMouse = newData.yMouse;
            jumping = newData.jumping;
            grounded = newData.grounded;
            timeSinceGrounded = newData.timeSinceGrounded;
            yVel = newData.yVel;
            slide = newData.slide;
            gravMult = newData.gravMult;
            currentStrafeMult = newData.currentStrafeMult;
            currentBackwardMult = newData.currentBackwardMult;
            currentMoveSpeed = newData.currentMoveSpeed;
            groundAngle = newData.groundAngle;
            lastMove = newData.lastMove;
            currentMove = newData.currentMove;
            forward = newData.forward;
            side = newData.side;
            moveDelta = newData.moveDelta;
            hitNormal = newData.hitNormal;
            hitPoint = newData.hitPoint;
            slideMove = newData.slideMove;
            standingHeight = newData.standingHeight;
            cameraOffset = newData.cameraOffset;
        }

        void ExecuteExtension(ExtFunc command)
        {
            if (!extensionsEnabled)
            {
                return;
            }
            TFPData data = GetData();
            foreach (TFPExtension extension in Extensions)
            {
                switch (command)
                {
                    case ExtFunc.Start:
                        extension.ExStart(ref data, controllerInfo);
                        break;
                    case ExtFunc.PreUpdate:
                        extension.ExPreUpdate(ref data, controllerInfo);
                        break;
                    case ExtFunc.PostUpdate:
                        extension.ExPostUpdate(ref data, controllerInfo);
                        break;
                    case ExtFunc.PreFixedUpdate:
                        extension.ExPreFixedUpdate(ref data, controllerInfo);
                        break;
                    case ExtFunc.PostFixedUpdate:
                        extension.ExPostFixedUpdate(ref data, controllerInfo);
                        break;
                    case ExtFunc.PreMove:
                        extension.ExPreMove(ref data, controllerInfo);
                        break;
                    case ExtFunc.PreMoveCalc:
                        extension.ExPreMoveCalc(ref data, controllerInfo);
                        break;
                    case ExtFunc.PostMove:
                        extension.ExPostMove(ref data, controllerInfo);
                        break;
                    case ExtFunc.PostInput:
                        extension.ExPostInput(ref data, controllerInfo);
                        break;
                    default:
                        break;
                }

            }
            SetData(data);
        }

    }
}
