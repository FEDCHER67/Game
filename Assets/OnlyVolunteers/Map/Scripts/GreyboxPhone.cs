using OnlyVolunteers.Inventory;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Physics;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Vadim's phone on the map's KCC pawn (Tab), as in NetworkTest: while it is out the pawn stands still, the cursor is
    // free and the hands are busy - no Q / E (GreyboxInteractor), no LMB grab (PhysicsGrabber, letting go of a held
    // body), no inventory keys or wheel (the phone's map zooms with the wheel). Getting into the van puts it away: the
    // pawn is switched off there. Added by MapGreyboxBuilder.PlaceGameplay.
    [RequireComponent(typeof(KccFirstPersonInput))]
    public sealed class GreyboxPhone : MonoBehaviour
    {
        private PhoneController phone;
        private Behaviour[] hands;

        private void Start()
        {
            var input = GetComponent<KccFirstPersonInput>();
            hands = new Behaviour[]
            {
                GetComponentInChildren<PhysicsGrabber>(true),
                GetComponentInChildren<GreyboxInteractor>(true),
                GetComponentInChildren<InventoryInput>(true),
            };
            phone = PhoneController.Create(input.ViewCamera, input);
            phone.OpenChanged += SetHandsBusy;
        }

        private void SetHandsBusy(bool busy)
        {
            foreach (Behaviour hand in hands)
                if (hand != null)
                    hand.enabled = !busy;
        }

        private void OnDisable()
        {
            if (phone != null)
                phone.SetOpen(false);
        }

        private void OnDestroy()
        {
            if (phone != null)
                Destroy(phone.gameObject);
        }
    }
}
