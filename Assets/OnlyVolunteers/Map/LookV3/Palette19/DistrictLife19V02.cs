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
            if(wornLamps!=null) for(int i=0;i<wornLamps.Length;i++)
                if(wornLamps[i]) wornLamps[i].intensity=Mathf.PerlinNoise(i*5.3f,t*7)>.42f ? .65f : .025f;
        }
    }
}
