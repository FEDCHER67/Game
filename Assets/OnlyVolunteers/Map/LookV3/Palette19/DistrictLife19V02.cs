using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Local, deterministic presentation. No Animator, rigs, navigation or gameplay authority.
    public sealed class DistrictLife19V02 : MonoBehaviour
    {
        [System.Serializable] public sealed class Flyer
        {
            public Transform body, leftWing, rightWing;
            public Vector3 centre;
            public float radius=8, speed=.35f, phase, flap=5;
        }
        public Flyer[] flyers;
        public Light[] wornLamps;
        [Tooltip("W86 (Fedya 25.10): lamps inside these XZ rects (Downtown) burn steadily and only now and then drop out briefly; " +
                 "outside them the worn flicker stays as it was (Rough). Empty = the old behaviour everywhere.")]
        public Rect[] calmAreas = new Rect[0];
        bool[] calm;
        private void Update()
        {
            float t=Time.time;
            if(flyers!=null) foreach(var f in flyers)
            {
                if(!f.body) continue;
                float a=t*f.speed+f.phase;
                f.body.position=f.centre+new Vector3(Mathf.Cos(a)*f.radius,Mathf.Sin(a*2)*.32f,Mathf.Sin(a)*f.radius*.64f);
                f.body.rotation=Quaternion.LookRotation(new Vector3(-Mathf.Sin(a),0,Mathf.Cos(a)*.64f));
                float flap=Mathf.Sin(t*f.flap+f.phase)*32;
                if(f.leftWing) f.leftWing.localRotation=Quaternion.Euler(0,0,flap);
                if(f.rightWing) f.rightWing.localRotation=Quaternion.Euler(0,0,-flap);
            }
            if(wornLamps!=null)
            {
                if(calm==null || calm.Length!=wornLamps.Length)
                {
                    calm=new bool[wornLamps.Length];
                    for(int i=0;i<wornLamps.Length;i++)
                        if(wornLamps[i] && calmAreas!=null) foreach(var r in calmAreas)
                            if(r.Contains(new Vector2(wornLamps[i].transform.position.x,wornLamps[i].transform.position.z))) { calm[i]=true; break; }
                }
                for(int i=0;i<wornLamps.Length;i++)
                {
                    if(!wornLamps[i]) continue;
                    // calm: a slow noise that dips below .1 only rarely: steady light, a short drop-out every half minute or so per lamp
                    bool on = calm[i] ? Mathf.PerlinNoise(i*5.3f+31f,t*.55f)>.1f || Mathf.PerlinNoise(i*2.1f,t*9f)>.3f
                                      : Mathf.PerlinNoise(i*5.3f,t*7)>.42f;
                    wornLamps[i].intensity=on ? .65f : .025f;
                }
            }
        }
    }
}
