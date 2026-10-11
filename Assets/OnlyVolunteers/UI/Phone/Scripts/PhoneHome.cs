using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace OnlyVolunteers.Phone
{
    // Home screens with Android "finger" logic for the mouse cursor:
    // tap an icon = open it; press and hold an icon = move mode: while the button stays down the icon
    // follows the cursor (hold it at the screen edge to go to the next page), release = it lands in the
    // nearest slot. A quick drag (no hold) anywhere = swipe pages; the mouse wheel also switches pages.
    // Page 1 keeps its top rows for the clock and the notification; other pages use the full grid.
    public sealed class PhoneHome : PhoneApp
    {
        private enum Gesture { None, Pressing, Moving, Swiping }

        private const int PageCount = 3;
        private const int Columns = 3;
        private const int Rows = 6;
        private const int SlotsPerPage = Columns * Rows;
        private const int FirstRowOnFirstPage = 2;
        private const float IconSize = 80f;
        private const float FirstRowY = 104f;
        private const float RowStep = 116f;
        private const float HoldSeconds = 0.4f;
        private const float HoldSlopPixels = 12f;
        private const float EdgeZone = 30f;
        private const float EdgeHoldSeconds = 0.5f;
        private const float SwipeShare = 0.18f;
        private static readonly float[] ColumnX = { 66f, 196f, 326f };

        private sealed class Cell
        {
            public PhoneApp App;
            public int Page;
            public int Slot;
            public RectTransform Rect;
            public Image Hit;
            public GameObject Badge;
            public Text Count;
        }

        private readonly PhoneApp[][] pages = new PhoneApp[PageCount][];
        private readonly List<Cell> cells = new();
        private readonly RectTransform[] pageRoots = new RectTransform[PageCount];
        private readonly Image[] dots = new Image[PageCount];
        private RectTransform pagesRoot;
        private RectTransform dragLayer;
        private Image dropMarker;
        private Text bigClock;
        private Text date;
        private Text cardTitle;
        private Text cardBody;
        private int page;

        private Gesture gesture;
        private Cell pressed;
        private float pressTime;
        private Vector2 pressPosition;
        private Vector2 grabOffset;
        private float edgeTimer;
        private int targetSlot = -1;
        private bool clickConsumed;
        private bool rebuildAfterDrop;
        private float swipeStartX;
        private float swipeOffset;
        private float wheelCooldown;

        public override string Title => "Home";
        public override string IconName => "wallpaper";

        protected override void Build(RectTransform root)
        {
            for (int i = 0; i < PageCount; i++)
                pages[i] = new PhoneApp[SlotsPerPage];

            var swipe = PhoneUi.Panel(root, "SwipeArea", new Color(0, 0, 0, 0));
            swipe.raycastTarget = true;
            swipe.rectTransform.Stretch();
            var relay = swipe.gameObject.AddComponent<PhoneDragRelay>();
            relay.Began = BeginSwipe;
            relay.Dragged = DragSwipe;
            relay.Ended = e => EndSwipe();

            pagesRoot = PhoneUi.Rect("Pages", root).Stretch();
            for (int i = 0; i < PageCount; i++)
            {
                pageRoots[i] = PhoneUi.Rect("Page" + i, pagesRoot);
                pageRoots[i].anchorMin = new Vector2(0, 0);
                pageRoots[i].anchorMax = new Vector2(0, 1);
                pageRoots[i].pivot = new Vector2(0, 0.5f);
                pageRoots[i].sizeDelta = new Vector2(PhoneLayout.Width, 0);
                pageRoots[i].anchoredPosition = new Vector2(i * PhoneLayout.Width, 0);
                PhoneUi.Rect("Grid", pageRoots[i]).Stretch();
            }
            BuildClockAndCard(pageRoots[0]);

            for (int i = 0; i < PageCount; i++)
            {
                int index = i;
                var dot = PhoneUi.Button(root, "Dot" + i, Color.white, 0, () => GoToPage(index));
                dot.image.sprite = PhoneUi.Circle;
                dot.image.type = Image.Type.Simple;
                ((RectTransform)dot.transform).Place(new Vector2(0.5f, 0),
                    new Vector2((i - (PageCount - 1) * 0.5f) * 16f, 36f), new Vector2(8, 8));
                dots[i] = dot.image;
            }

            dragLayer = PhoneUi.Rect("DragLayer", root).Stretch();
            dropMarker = PhoneUi.Panel(dragLayer, "DropMarker", new Color(1, 1, 1, 0.24f), 22);
            dropMarker.rectTransform.sizeDelta = new Vector2(IconSize + 16, IconSize + 16);
            dropMarker.gameObject.SetActive(false);
        }

        // Page 1 top: time, date and the latest notification only.
        private void BuildClockAndCard(RectTransform parent)
        {
            bigClock = PhoneUi.Label(parent, "12:00", 84, Color.white, TextAnchor.MiddleCenter, true, true);
            bigClock.rectTransform.Top(42, 98);
            bigClock.gameObject.AddComponent<Shadow>().effectColor = new Color(0, 0, 0, 0.3f);
            date = PhoneUi.Label(parent, "", 18, new Color(1, 1, 1, 0.95f), TextAnchor.MiddleCenter, true);
            date.rectTransform.Top(138, 26);
            date.gameObject.AddComponent<Shadow>().effectColor = new Color(0, 0, 0, 0.3f);

            // The private request (canon §53) until answered, then the newest message.
            var card = PhoneUi.Button(parent, "Notification", new Color(1, 1, 1, 0.92f), 22,
                () => Phone.OpenApp(Phone.Messages.OpenThread(Phone.Messages.RequestAnswered
                    ? Phone.Messages.LatestThread : "Unknown number")));
            ((RectTransform)card.transform).Top(180, 94, 12, 12);
            PhoneUi.Picture(card.transform, "Icon", PhoneUi.Icon("app_messages")).rectTransform
                .Place(new Vector2(0, 1), new Vector2(34, -34), new Vector2(36, 36));
            cardTitle = PhoneUi.Label(card.transform, "", 16, PhoneUi.Ink, TextAnchor.MiddleLeft, true);
            cardTitle.rectTransform.Top(14, 24, 62, 60);
            PhoneUi.Label(card.transform, "now", 13, PhoneUi.Muted, TextAnchor.MiddleRight)
                .rectTransform.Top(14, 24, 0, 16);
            cardBody = PhoneUi.Label(card.transform, "", 14, PhoneUi.Ink, TextAnchor.UpperLeft);
            cardBody.verticalOverflow = VerticalWrapMode.Truncate;
            cardBody.rectTransform.Top(40, 42, 62, 16);
        }

        // ---------- slots ----------

        private static bool Valid(int p, int slot) => p != 0 || slot / Columns >= FirstRowOnFirstPage;
        private static Vector2 SlotCentre(int slot) => new(ColumnX[slot % Columns], FirstRowY + slot / Columns * RowStep);
        private static Vector2 SlotAnchored(int slot) => new(SlotCentre(slot).x, -SlotCentre(slot).y);

        // Slot centre in DragLayer coordinates (its pivot is the screen centre).
        private static Vector2 SlotInLayer(int slot) =>
            new(SlotCentre(slot).x - PhoneLayout.Width * 0.5f, PhoneLayout.Height * 0.5f - SlotCentre(slot).y);

        // Puts an app into the first free slot (page by page). On page 1 icons start one row lower,
        // the row right under the notification is filled last (it still accepts dragged icons).
        public void Place(PhoneApp app)
        {
            for (int p = 0; p < PageCount; p++)
            for (int i = 0; i < SlotsPerPage; i++)
            {
                int s = p == 0 ? (i + Columns * (FirstRowOnFirstPage + 1)) % SlotsPerPage : i;
                if (!Valid(p, s) || pages[p][s] != null)
                    continue;
                pages[p][s] = app;
                if (gesture == Gesture.Moving)
                    rebuildAfterDrop = true;
                else
                    RebuildGrid();
                return;
            }
            Debug.LogWarning("[Phone] no free home slot for " + app.Title);
        }

        private int NearestSlot(Vector2 inLayer, bool freeOnly)
        {
            int best = -1;
            float bestDistance = float.MaxValue;
            for (int s = 0; s < SlotsPerPage; s++)
            {
                if (!Valid(page, s))
                    continue;
                var occupant = pages[page][s];
                if (freeOnly && occupant != null && occupant != pressed.App)
                    continue;
                float distance = (SlotInLayer(s) - inLayer).sqrMagnitude;
                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    best = s;
                }
            }
            return best;
        }

        // ---------- cells ----------

        private void RebuildGrid()
        {
            rebuildAfterDrop = false;
            foreach (var cell in cells)
                if (cell.Rect != null)
                    UnityEngine.Object.Destroy(cell.Rect.gameObject);
            cells.Clear();
            for (int p = 0; p < PageCount; p++)
            for (int s = 0; s < SlotsPerPage; s++)
                if (pages[p][s] != null)
                    cells.Add(BuildCell((RectTransform)pageRoots[p].Find("Grid"), pages[p][s], p, s));
        }

        private Cell BuildCell(RectTransform grid, PhoneApp app, int p, int s)
        {
            var cell = new Cell { App = app, Page = p, Slot = s };
            var button = PhoneUi.HitArea(grid, "Cell_" + app.Title, () =>
            {
                // A swipe or a move that started on this icon must not open it on release.
                if (clickConsumed || gesture == Gesture.Moving)
                {
                    clickConsumed = false;
                    return;
                }
                Phone.OpenApp(app);
            });
            cell.Hit = button.GetComponent<Image>(); // not button.image: Awake may not have run yet
            cell.Rect = ((RectTransform)button.transform).Place(new Vector2(0, 1), SlotAnchored(s),
                new Vector2(IconSize + 12, IconSize + 12));
            button.transition = Selectable.Transition.ColorTint;
            button.targetGraphic = PhoneUi.Picture(button.transform, "Icon", PhoneUi.Icon(app.IconName));
            button.targetGraphic.rectTransform.Place(new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(IconSize, IconSize));
            var label = PhoneUi.Label(button.transform, app.Title, 14, Color.white, TextAnchor.MiddleCenter, true);
            label.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(0, -IconSize * 0.5f - 13f), new Vector2(120, 22));
            label.gameObject.AddComponent<Shadow>().effectColor = new Color(0, 0, 0, 0.6f);

            var badge = PhoneUi.Panel(button.transform, "Badge", PhoneUi.Hex("#FF3B30"));
            badge.sprite = PhoneUi.Circle;
            badge.rectTransform.Place(new Vector2(0.5f, 0.5f), new Vector2(IconSize * 0.5f - 6, IconSize * 0.5f - 6),
                new Vector2(26, 26));
            cell.Count = PhoneUi.Label(badge.transform, "", 14, Color.white, TextAnchor.MiddleCenter, true);
            cell.Count.rectTransform.Stretch();
            cell.Badge = badge.gameObject;

            var relay = button.gameObject.AddComponent<PhoneDragRelay>();
            relay.Pressed = e => Press(cell, e);
            relay.Released = e =>
            {
                if (gesture == Gesture.Pressing)
                    gesture = Gesture.None;
            };
            // Move mode follows the mouse by polling; a uGUI drag on an icon is only a page swipe.
            relay.Began = e =>
            {
                if (gesture == Gesture.Moving)
                    return;
                BeginSwipe(e);
                clickConsumed = true; // the page moves with the cursor, the icon may still be under it
            };
            relay.Dragged = DragSwipe;
            relay.Ended = e => EndSwipe();
            return cell;
        }

        // ---------- move mode ----------

        private void Press(Cell cell, PointerEventData e)
        {
            if (gesture != Gesture.None)
                return;
            gesture = Gesture.Pressing;
            pressed = cell;
            pressTime = Time.unscaledTime;
            pressPosition = e.position;
            clickConsumed = false;
        }

        private void Lift(Cell cell)
        {
            gesture = Gesture.Moving;
            clickConsumed = true;
            Vector2 local = dragLayer.InverseTransformPoint(cell.Rect.position);
            cell.Rect.SetParent(dragLayer, true);
            cell.Rect.anchorMin = cell.Rect.anchorMax = new Vector2(0.5f, 0.5f);
            cell.Rect.anchoredPosition = local;
            cell.Hit.raycastTarget = false;
            grabOffset = PointerInLayer(out var pointer) ? local - pointer : Vector2.zero;
            edgeTimer = 0f;
            targetSlot = cell.Slot;
            Phone.PlayTap();
        }

        private bool PointerInLayer(out Vector2 local) =>
            RectTransformUtility.ScreenPointToLocalPointInRectangle(dragLayer, Input.mousePosition, null, out local);

        private void UpdateMovingIcon()
        {
            var icon = pressed.Rect;
            if (PointerInLayer(out var pointer))
            {
                float k = 1f - Mathf.Exp(-30f * Time.unscaledDeltaTime);
                icon.anchoredPosition = Vector2.Lerp(icon.anchoredPosition, pointer + grabOffset, k);
                icon.localScale = Vector3.one * Mathf.Lerp(icon.localScale.x, 1.15f, k);
                icon.localRotation = Quaternion.Euler(0, 0, Mathf.Sin(Time.unscaledTime * 18f) * 2.5f);

                // Hold at the screen edge to carry the icon to the neighbour page.
                bool right = pointer.x > PhoneLayout.Width * 0.5f - EdgeZone && page < PageCount - 1;
                bool left = pointer.x < -PhoneLayout.Width * 0.5f + EdgeZone && page > 0;
                edgeTimer = right || left ? edgeTimer + Time.unscaledDeltaTime : 0f;
                if (edgeTimer > EdgeHoldSeconds)
                    GoToPage(page + (right ? 1 : -1));
            }

            // Same page: drop on any slot (swaps). Other page: prefer the nearest free slot.
            bool otherPage = page != pressed.Page;
            targetSlot = NearestSlot(icon.anchoredPosition, otherPage);
            if (targetSlot < 0)
                targetSlot = NearestSlot(icon.anchoredPosition, false);
            dropMarker.gameObject.SetActive(targetSlot >= 0);
            if (targetSlot >= 0)
                dropMarker.rectTransform.anchoredPosition = SlotInLayer(targetSlot);

            if (!Input.GetMouseButton(0))
                Drop(true);
        }

        private void Drop(bool place)
        {
            if (pressed != null && place && targetSlot >= 0 &&
                !(page == pressed.Page && targetSlot == pressed.Slot))
            {
                pages[pressed.Page][pressed.Slot] = pages[page][targetSlot];
                pages[page][targetSlot] = pressed.App;
            }
            gesture = Gesture.None;
            pressed = null;
            targetSlot = -1;
            dropMarker.gameObject.SetActive(false);
            RebuildGrid();
        }

        // Cells glide to their slots; in move mode the one in the target slot previews the swap.
        private void UpdateCells()
        {
            float k = 1f - Mathf.Exp(-18f * Time.unscaledDeltaTime);
            bool moving = gesture == Gesture.Moving && pressed != null;
            foreach (var cell in cells)
            {
                if (moving && cell == pressed)
                    continue;
                int slot = cell.Slot;
                if (moving && pressed.Page == page && cell.Page == page && cell.Slot == targetSlot &&
                    targetSlot != pressed.Slot)
                    slot = pressed.Slot;
                cell.Rect.anchoredPosition = Vector2.Lerp(cell.Rect.anchoredPosition, SlotAnchored(slot), k);
                int value = cell.App.Badge;
                cell.Badge.SetActive(value > 0);
                cell.Count.text = value.ToString();
            }
        }

        // ---------- pages ----------

        private void BeginSwipe(PointerEventData e)
        {
            if (gesture == Gesture.Moving)
                return;
            gesture = Gesture.Swiping;
            pressed = null;
            swipeStartX = e.position.x;
            swipeOffset = 0f;
        }

        private void DragSwipe(PointerEventData e)
        {
            if (gesture != Gesture.Swiping)
                return;
            float dx = (e.position.x - swipeStartX) / Mathf.Max(0.01f, Root.lossyScale.x);
            bool pastEdge = (page == 0 && dx > 0) || (page == PageCount - 1 && dx < 0);
            swipeOffset = pastEdge ? dx * 0.3f : dx;
        }

        private void EndSwipe()
        {
            if (gesture != Gesture.Swiping)
                return;
            if (Mathf.Abs(swipeOffset) > PhoneLayout.Width * SwipeShare)
                GoToPage(page + (swipeOffset < 0 ? 1 : -1));
            gesture = Gesture.None;
            swipeOffset = 0f;
        }

        private void GoToPage(int target)
        {
            page = Mathf.Clamp(target, 0, PageCount - 1);
            edgeTimer = 0f;
        }

        public override bool Back()
        {
            if (page == 0)
                return false;
            GoToPage(0);
            return true;
        }

        public override void Hide()
        {
            if (gesture == Gesture.Moving)
                Drop(false);
            else if (rebuildAfterDrop)
                RebuildGrid();
            gesture = Gesture.None;
            swipeOffset = 0f;
            base.Hide();
        }

        public override void Tick()
        {
            var now = DateTime.Now;
            bigClock.text = now.ToString("HH:mm");
            date.text = now.ToString("dddd, d MMMM", CultureInfo.InvariantCulture);
            var messages = Phone.Messages;
            cardTitle.text = messages.RequestAnswered ? messages.LatestThread : "PRIVATE REQUEST";
            cardBody.text = messages.RequestAnswered ? messages.LatestText
                : "Heart · O− · Perfect+\nOffer: <b>$25,000</b>";

            if (gesture == Gesture.Pressing)
            {
                bool held = Input.GetMouseButton(0);
                bool still = ((Vector2)Input.mousePosition - pressPosition).magnitude < HoldSlopPixels;
                if (!held || !still)
                    gesture = Gesture.None;
                else if (Time.unscaledTime - pressTime >= HoldSeconds)
                    Lift(pressed);
            }
            if (gesture == Gesture.Moving)
                UpdateMovingIcon();
            else if (gesture == Gesture.None)
                WheelPages();
            UpdateCells();

            float target = -page * PhoneLayout.Width + (gesture == Gesture.Swiping ? swipeOffset : 0f);
            float x = gesture == Gesture.Swiping ? target
                : Mathf.Lerp(pagesRoot.anchoredPosition.x, target, 1f - Mathf.Exp(-16f * Time.unscaledDeltaTime));
            pagesRoot.anchoredPosition = new Vector2(Mathf.Abs(x - target) < 0.5f ? target : x, 0);
            for (int i = 0; i < PageCount; i++)
                dots[i].color = new Color(1, 1, 1, i == page ? 0.95f : 0.4f);
        }

        private void WheelPages()
        {
            wheelCooldown -= Time.unscaledDeltaTime;
            float wheel = Input.mouseScrollDelta.y;
            if (wheel == 0f || wheelCooldown > 0f)
                return;
            GoToPage(page + (wheel < 0f ? 1 : -1));
            wheelCooldown = 0.25f;
        }
    }
}
