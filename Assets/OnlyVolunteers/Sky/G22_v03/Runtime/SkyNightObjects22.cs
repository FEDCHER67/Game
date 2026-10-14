using UnityEngine;
namespace OnlyVolunteers.Sky22V03
{
    [ExecuteAlways]
    public sealed class SkyNightObjects22 : MonoBehaviour
    {
        [SerializeField] SkyClock22 clock;
        [SerializeField] GameObject[] nightObjects=System.Array.Empty<GameObject>();
        public void Configure(SkyClock22 source, GameObject[] objects) { Unbind();clock=source;nightObjects=objects; if(isActiveAndEnabled)Bind(); }
        void OnEnable()=>Bind();
        void OnDisable()=>Unbind();
        void Bind() { if(!clock)return; clock.NightChanged+=Apply;Apply(clock.IsNight); }
        void Unbind() { if(clock)clock.NightChanged-=Apply; }
        void Apply(bool night) { foreach(var item in nightObjects)if(item && item!=gameObject)item.SetActive(night); }
    }
}
