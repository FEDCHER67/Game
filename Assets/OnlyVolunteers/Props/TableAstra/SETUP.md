# TABLE-ASTRA-001 caster motion

Attach `TableAstraCasterMotion` to the moving gurney root and keep the repaired FBX hierarchy intact. The root is found by name or through the unique `RIG_GroundUp` marker when Unity renames the top node to the FBX filename; `Rig Root` can also be assigned explicitly. A Rigidbody on the component or its ancestors is found automatically; assign `Moving Body` for other layouts. Run one controller per rendered rig, including network replicas. Do not animate the same pivots with an Animator concurrently.

The rig uses four equal circular wheels with radius **0.105 model metres**, mechanical trail **0.035 model metres**, and no sideways axle offset. Each `RIG_CasterSteer_SUFFIX` must be directly below `RIG_Table_Root`; its `RIG_WheelRoll_SUFFIX` child is the wheel centre. Suffixes are `Foot_Left`, `Foot_Right`, `Head_Left`, `Head_Right`. In Blender, rest heading is +Y, ground up is +Z, and positive axle is +X. The roll centre is `(0, -0.035, -0.123)` relative to its steering pivot.

Exported marker transforms make Unity import orientation explicit:

- `RIG_GroundUp`, directly under the rig root, is 0.1 m along ground up.
- `RIG_WheelAxle_SUFFIX`, directly under each roll pivot, is 0.1 m along its positive axle.
- `RIG_WheelRadius_SUFFIX`, directly under each roll pivot, is 0.105 m down to the rest contact point.

The Unity 6000.5.11f1 default import was verified: world ground up is +Y, rest heading is -Z, and the derived axle/spin sign is +1. The controller derives heading from the trailing offset, derives the steering and roll axes from these markers, and checks hierarchy, unique names, dimensions and perpendicularity before enabling motion. It therefore does not presume that Blender axes map to particular Unity local axes. All ancestors must have positive uniform scale. The rig must retain that scale and remain upright relative to its initial ground plane. Incorrect or missing markers, dimensions, hierarchy, tilt, or runtime scale changes produce a Console error and disable the component. Mesh circularity is an export validation responsibility; these markers describe the physical geometry.

For unit ground normal `n`, wheel heading `f`, sideways direction `l = n × f`, pivot velocity `v`, trail `t`, radius `r`, and axle `a`, the shared Blender/Unity model is:

```
worldHeadingRate = dot(v, l) / t
localHeadingRate = worldHeadingRate - bodyYawRate
rollingSpeed = dot(v, f)
spinRate = rollingSpeed / (r * dot(a × n, f))
wheelCentre = steerPivot - t * f + verticalOffset * n
```

The ideal trailing caster swivels to cancel lateral wheel-contact velocity. Signed roll follows the current heading throughout steering, including backwards rolling at the start of a reversal. There is no fixed steering speed or low-speed cutoff. Midpoint integration subdivides by distance/trail and root yaw (at most approximately 0.1 radians of estimated motion per step). Angles remain continuous doubles; only the displayed quaternion angle is reduced modulo one revolution.

Exactly antiparallel reverse travel is an unstable mathematical equilibrium. On entering that state, a deterministic **0.5 degree** fork bias seeds the flip once. This is an explicit small approximation to mechanical asymmetry. At zero velocity the controller does not introduce drift. If a pivot remains stationary while the cart rotates about it, its local fork counter-rotates to preserve its world heading.

Dynamic bodies use `Rigidbody.GetPointVelocity` at each steering pivot. Kinematic/transform-driven roots use consecutive rendered poses, with midpoint yaw and the root's angular point velocity, so corners travel at different speeds in turns. Local heading compensates the observed rendered root yaw. Velocity and yaw are assumed constant within each rendered sample; smooth/interpolated root movement gives the best result. Translation over `Teleport Distance` or yaw over `Teleport Yaw Degrees` in one sample resets the motion baseline and holds the current wheel pose. Disabling/re-enabling also resets the baseline.

This component implements **planar wheel-contact kinematics**. The cart's movement controller, Rigidbody, colliders and networking determine its motion. It does not apply forces, solve collisions, simulate suspension, caster inertia, tyre slip, uneven ground or wheel lifting.
