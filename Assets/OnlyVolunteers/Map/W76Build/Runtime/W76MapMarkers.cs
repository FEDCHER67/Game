using UnityEngine;

namespace OnlyVolunteers.Map.W76
{
    // Lamps, rails, posts, traffic lights, signs, hydrants, benches: NPCs grab them while being loaded (handoff v02 §2).
    public sealed class W76GripAnchor : MonoBehaviour
    {
    }

    // Border checkpoint gate (handoff v02 §8.4): the "Leave the country" button only answers; the van is turned back.
    public sealed class W76LeaveCountryButton : MonoBehaviour
    {
        public string Label = "Leave the country";
        [TextArea] public string Reply = "Нет, страну покинуть нельзя: введено военное положение";

        public string Press()
        {
            Debug.Log("[W76 checkpoint] " + Reply);
            return Reply;
        }
    }

    // Elite gate trap / Tramduro bridge missiles (handoff v02 §8.7, §8.10): markers only, mechanics OPEN.
    public sealed class W76TrapMarker : MonoBehaviour
    {
        public string Kind = "elite_gate_latch";
        [Tooltip("Seconds until the gate shuts behind the van (OPEN, Vadim).")] public float Seconds = 8f;
    }
}
