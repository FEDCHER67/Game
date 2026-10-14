using System.Collections.Generic;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Map;
using OnlyVolunteers.Phone;
using OnlyVolunteers.Player;
using OnlyVolunteers.Player.Physics;
using UnityEngine;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Vehicles.Paint
{
    // Scene-local input ownership. Existing movement, inventory, phone and van scripts stay unchanged.
    [DefaultExecutionOrder(-1000)]
    public sealed class VanPaintMapMode : MonoBehaviour
    {
        public VanPaintInteractor Painter;
        public VanPaintHud Hud;
        public GreyboxKccPawn Pawn;
        public Transform Station;
        public bool Active { get; private set; }
        readonly List<Behaviour> muted = new();
        KccFirstPersonInput movement;
        bool oldMovementLock, oldLookSuspend, textLocked;
        void Start()
        {
            movement = Pawn.GetComponent<KccFirstPersonInput>();
            Painter.enabled = false; Hud.SetMapHelp(); Hud.SetShown(false);
            Painter.TextModeChanged += TextMode;
        }
        void Update()
        {
            if (!Pawn.Controlled || !movement.isActiveAndEnabled)
            { if (Active) ExitPaint(); return; }
            if (Painter.TextOpen) return;
            var keyboard = Keyboard.current;
            if (keyboard == null || !keyboard.bKey.wasPressedThisFrame) return;
            var eye = Pawn.ViewCamera.transform;
            PickOrStow(new Ray(eye.position, eye.forward));
        }
        public bool PickOrStow(Ray ray)
        {
            if (!Pawn.Controlled) return false;
            var phone = Object.FindAnyObjectByType<PhoneController>();
            if (!Active && (phone != null && phone.IsOpen || movement.MovementLocked || movement.LookSuspended)) return false;
            if (!Physics.Raycast(ray,out var hit,3.5f,~0,QueryTriggerInteraction.Ignore) || hit.collider.GetComponentInParent<VanPaintProp>() == null)
            { if (Active) ExitPaint(); return false; }
            if (!Active)
            {
                Active=true;
                // Stop contextual actions before muting inventory; its OnDisable may restore inventory ownership.
                Mute(Pawn.GetComponentInChildren<GreyboxInteractor>());
                Mute(Pawn.GetComponent<PhysicsGrabber>());
                Mute(Pawn.GetComponentInChildren<InventoryInput>());
                Mute(phone);
                Painter.enabled=true; Hud.SetShown(true);
            }
            return Painter.PickUp(ray);
        }
        void Mute(Behaviour value) { if(value != null && value.enabled) { value.enabled=false; muted.Add(value); } }
        void TextMode(bool open)
        {
            if (open && !textLocked)
            {
                oldMovementLock=movement.MovementLocked; oldLookSuspend=movement.LookSuspended;
                movement.MovementLocked=true; movement.LookSuspended=true; textLocked=true;
            }
            else if (!open && textLocked)
            {
                movement.MovementLocked=oldMovementLock; movement.LookSuspended=oldLookSuspend; textLocked=false;
            }
        }
        public void ExitPaint()
        {
            Painter.StowTools(); TextMode(false); Painter.enabled=false; Active=false; Hud.SetShown(false);
            foreach(var value in muted) if(value != null) value.enabled=true;
            muted.Clear();
        }
        void OnDisable() { if(Active) ExitPaint(); }
        void OnDestroy() { if(Painter != null) Painter.TextModeChanged-=TextMode; }
        void OnGUI()
        {
            if(Active || Pawn == null || !Pawn.Controlled || Station == null || Vector3.Distance(Pawn.Position,Station.position)>6) return;
            GUI.Label(new Rect(Screen.width/2-250,Screen.height-115,500,30),"GRANDPA'S PAINT  —  aim at brush / can and press B");
        }
    }
}
