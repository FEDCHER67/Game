using System.Text;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Physics layers of the NPC capture prototype (stage 1). The names live in ProjectSettings/TagManager.asset, the
    // collision pairs in ProjectSettings/DynamicsManager.asset; this file is the code-side copy of both. Everything else
    // collides with everything:
    //   VehicleInterior x every layer - trigger/query volumes only;
    //   NpcSeated x NpcBody, NpcSeated x NpcSeated - NPCs sitting in the cargo bay ignore lying bodies and each other;
    //   RemotePlayer x Vehicle - network proxies of other players do not push the van (draft, section 3).
    // The KCC builds its CollidableLayers from this matrix in Awake, so Player must keep colliding with Vehicle.
    // TRAP for the network work (nothing uses RemotePlayer yet): a KCC motor on RemotePlayer (proxies of other players,
    // host/server simulation of them, client prediction) gets Vehicle dropped from its CollidableLayers by the pair above,
    // so it walks through the van and falls through the cargo floor. Whoever moves a motor onto RemotePlayer must add
    // it back right after the motor's Awake: motor.CollidableLayers |= VehicleMask (the matrix pair then only stops
    // PhysX contacts: the proxy does not shove the van). Or drop the pair and use per-proxy Physics.IgnoreCollision.
    public static class OvLayers
    {
        public const int Player = 8;
        public const int RemotePlayer = 9;
        public const int Vehicle = 10;
        public const int VehicleInterior = 11;
        public const int NpcBody = 12;
        public const int NpcSeated = 13;

        public const int PlayerMask = 1 << Player;
        public const int VehicleMask = 1 << Vehicle;
        public const int NpcMask = (1 << NpcBody) | (1 << NpcSeated);
        // Hits (Q, later weapons) ignore our own capsule and the cargo-bay query volumes.
        public const int ShootMask = ~((1 << Player) | (1 << VehicleInterior));

        private static readonly (int layer, string name)[] Names =
        {
            (Player, "Player"), (RemotePlayer, "RemotePlayer"), (Vehicle, "Vehicle"),
            (VehicleInterior, "VehicleInterior"), (NpcBody, "NpcBody"), (NpcSeated, "NpcSeated"),
        };

        /// <summary>Whether the table above says the two layers ignore each other.</summary>
        public static bool ShouldIgnore(int a, int b)
        {
            if (a == VehicleInterior || b == VehicleInterior) return true;
            if ((a == NpcSeated && (b == NpcBody || b == NpcSeated)) || (b == NpcSeated && a == NpcBody)) return true;
            return (a == RemotePlayer && b == Vehicle) || (a == Vehicle && b == RemotePlayer);
        }

        // ProjectSettings are shared with Vadim and easy to lose in a merge: say so once at start instead of letting bodies
        // silently fall through the van or seated NPCs explode against lying ones.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void CheckSettings()
        {
            var problems = new StringBuilder();
            foreach ((int layer, string name) in Names)
                if (LayerMask.LayerToName(layer) != name)
                    problems.Append($" layer {layer} is '{LayerMask.LayerToName(layer)}', expected '{name}';");
            for (int a = 0; a < 32; a++)
                for (int b = a; b < 32; b++)
                {
                    bool expected = ShouldIgnore(a, b);
                    if (Physics.GetIgnoreLayerCollision(a, b) != expected)
                        problems.Append($" {a}x{b} should {(expected ? "ignore" : "collide")};");
                }
            if (problems.Length > 0)
                Debug.LogWarning($"[OvLayers] ProjectSettings differ from OvLayers (TagManager / Physics collision matrix):{problems}");
        }
    }
}
