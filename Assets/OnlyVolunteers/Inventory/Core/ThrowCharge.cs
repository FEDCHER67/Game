using System;

namespace OnlyVolunteers.Inventory
{
    /// <summary>The one charged-throw rule of the game (Fedya, WORK_INVENTORY_SPEC decision 6, 2026-10-18): the longer the
    /// throw key is held, the stronger the throw. A tap is a gentle toss (TossSpeed), a full charge takes FullChargeSeconds,
    /// and heavier things reach a lower top speed (MaxSpeed). The client measures the hold and sends charge 0..1; the
    /// server clamps it (Clamp) and turns it into the release velocity (Velocity). Pure maths, no engine types, so every
    /// throw site (hotbar G, a carried body bag, future coolers) and the EditMode tests share it.</summary>
    public static class ThrowCharge
    {
        /// <summary>Hold time of a full charge, seconds.</summary>
        public const float FullChargeSeconds = 1.1f;
        /// <summary>Release speed of a tap (charge 0), m/s, whatever the mass.</summary>
        public const float TossSpeed = 2f;
        /// <summary>Top speed (charge 1) of a light thing (LightMass and below) and of a heavy one (HeavyMass and above), m/s.</summary>
        public const float MaxSpeedLight = 9f, MaxSpeedHeavy = 4.5f;
        public const float LightMass = 1f, HeavyMass = 60f;
        /// <summary>Upward part of the release velocity at charge 0 and at charge 1, m/s (a small arc, not a lob).</summary>
        public const float LiftTap = 0.5f, LiftFull = 1.6f;

        /// <summary>Client: charge 0..1 after holding the throw key for 'heldSeconds'.</summary>
        public static float FromHold(float heldSeconds) => Clamp(heldSeconds / FullChargeSeconds);

        /// <summary>Server: whatever a client sent becomes 0..1 (NaN and infinities count as a tap).</summary>
        public static float Clamp(float charge) => float.IsNaN(charge) || float.IsInfinity(charge) ? 0f : Math.Max(0f, Math.Min(1f, charge));

        /// <summary>Top speed for a mass (kg): MaxSpeedLight down to MaxSpeedHeavy, linear in between.</summary>
        public static float MaxSpeed(float mass)
        {
            if (float.IsNaN(mass) || mass <= LightMass) return MaxSpeedLight;
            float t = Math.Min(1f, (mass - LightMass) / (HeavyMass - LightMass));
            return MaxSpeedLight + (MaxSpeedHeavy - MaxSpeedLight) * t;
        }

        /// <summary>Forward release speed for a (client) charge and a mass.</summary>
        public static float Speed(float charge, float mass) => TossSpeed + (MaxSpeed(mass) - TossSpeed) * Clamp(charge);

        /// <summary>Upward release speed for a (client) charge.</summary>
        public static float Lift(float charge) => LiftTap + (LiftFull - LiftTap) * Clamp(charge);

        /// <summary>Release velocity as (x, y, z) from a view direction (any length; its horizontal part is used, falling
        /// back to the full direction when looking straight up or down), a charge and a mass.</summary>
        public static void Velocity(float dirX, float dirY, float dirZ, float charge, float mass, out float x, out float y, out float z)
        {
            float length = (float)Math.Sqrt(dirX * dirX + dirY * dirY + dirZ * dirZ);
            if (!(length > 1e-5f)) { dirX = 0f; dirY = 0f; dirZ = 1f; length = 1f; }
            dirX /= length; dirY /= length; dirZ /= length;
            float speed = Speed(charge, mass);
            x = dirX * speed; y = dirY * speed + Lift(charge); z = dirZ * speed;
        }
    }
}
