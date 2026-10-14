using System;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.InputSystem;

namespace OnlyVolunteers.Sky22V05
{
    [DisallowMultipleComponent]
    public sealed class SkyClock22 : MonoBehaviour
    {
        [SerializeField,Range(0,24)] float hour=12;
        [SerializeField,Min(.1f)] float cycleMinutes=24;
        [SerializeField] bool running=true;
        [SerializeField] bool debugKeys=true;
        [SerializeField] UnityEvent<bool> nightChanged=new UnityEvent<bool>();
        bool publishedNight;
        public event Action<bool> NightChanged;
        public float Hour => hour;
        public bool IsNight => SkyModel22.IsNight(hour);
        public bool Running { get=>running;set=>running=value; }
        public float CycleMinutes { get=>cycleMinutes;set=>cycleMinutes=Mathf.Max(.1f,value); }
        public UnityEvent<bool> OnNightChanged => nightChanged;
        void OnEnable() { hour=SkyModel22.Wrap(hour); Publish(); }
        void Publish() { publishedNight=IsNight;NightChanged?.Invoke(IsNight); nightChanged.Invoke(IsNight); }
        public void SetHour(float value) { bool before=IsNight; hour=SkyModel22.Wrap(value); if(before!=IsNight)Publish(); }
        public void Tick(float deltaSeconds) { if(running)SetHour(SkyModel22.Advance(hour,deltaSeconds,cycleMinutes)); }
        void Update()
        {
            if(publishedNight!=IsNight)Publish(); // Inspector edits also resynchronize listeners.
            Tick(Time.deltaTime);
            if(!debugKeys || Keyboard.current==null)return;
            var k=Keyboard.current;
            if(k.backslashKey.wasPressedThisFrame)running=!running;
            float scrub=(k.rightBracketKey.isPressed?1:0)-(k.leftBracketKey.isPressed?1:0);
            if(scrub!=0)SetHour(hour+scrub*Time.unscaledDeltaTime*(k.shiftKey.isPressed?6:1));
        }
    }
}
