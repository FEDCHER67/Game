using System;

namespace OnlyVolunteers.Props.TableAstra
{
    /// <summary>Ideal no-slip caster on a plane; all angles are continuous radians.</summary>
    internal static class CasterKinematics
    {
        internal static void Advance(ref double heading, ref double spin, ref bool reversing,
            double forwardVelocity, double lateralVelocity, double bodyYawRate, double dt,
            double trail, double radius, double axleSign)
        {
            if (dt <= 0.0) return;
            double speed = Math.Sqrt(forwardVelocity * forwardVelocity + lateralVelocity * lateralVelocity);
            double rolling = forwardVelocity * Math.Cos(heading) + lateralVelocity * Math.Sin(heading);
            double sideways = -forwardVelocity * Math.Sin(heading) + lateralVelocity * Math.Cos(heading);
            if (speed > 0.0)
            {
                bool backwards = rolling < 0.0;
                // Exactly antiparallel is unstable in the ideal equations. Seed the flip once,
                // preserving negative initial rolling, with a tiny deterministic fork bias.
                if (backwards && !reversing && Math.Abs(sideways) <= speed * 1e-6)
                    heading += 0.5 * Math.PI / 180.0;
                reversing = backwards;
            }
            int steps = Math.Max(1, (int)Math.Ceiling((speed / trail + Math.Abs(bodyYawRate)) * dt / 0.1));
            double h = dt / steps;
            for (int i = 0; i < steps; i++)
            {
                double rate = (-forwardVelocity * Math.Sin(heading) + lateralVelocity * Math.Cos(heading)) / trail - bodyYawRate;
                double midpoint = heading + rate * h * 0.5;
                heading += ((-forwardVelocity * Math.Sin(midpoint) + lateralVelocity * Math.Cos(midpoint)) / trail - bodyYawRate) * h;
                spin += (forwardVelocity * Math.Cos(midpoint) + lateralVelocity * Math.Sin(midpoint)) * h / (radius * axleSign);
            }
        }
    }
}
