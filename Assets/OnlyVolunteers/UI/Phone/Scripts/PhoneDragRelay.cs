using System;
using UnityEngine;
using UnityEngine.EventSystems;

namespace OnlyVolunteers.Phone
{
    // Forwards uGUI press/drag events of one element to code-built screens (home icons, page swipe).
    public sealed class PhoneDragRelay : MonoBehaviour, IPointerDownHandler, IPointerUpHandler,
        IBeginDragHandler, IDragHandler, IEndDragHandler
    {
        public Action<PointerEventData> Pressed;
        public Action<PointerEventData> Released;
        public Action<PointerEventData> Began;
        public Action<PointerEventData> Dragged;
        public Action<PointerEventData> Ended;

        public void OnPointerDown(PointerEventData eventData) => Pressed?.Invoke(eventData);
        public void OnPointerUp(PointerEventData eventData) => Released?.Invoke(eventData);
        public void OnBeginDrag(PointerEventData eventData) => Began?.Invoke(eventData);
        public void OnDrag(PointerEventData eventData) => Dragged?.Invoke(eventData);
        public void OnEndDrag(PointerEventData eventData) => Ended?.Invoke(eventData);
    }
}
