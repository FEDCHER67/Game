#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Transient Play-test witness. Never saved into a scene or a player build.
    public sealed class G18RouteContactWitness : MonoBehaviour
    {
        public readonly HashSet<string> Contacts = new();
        void OnCollisionEnter(Collision collision) => Observe(collision);
        void OnCollisionStay(Collision collision) => Observe(collision);
        void Observe(Collision collision)
        {
            var c=collision.collider;
            if(c is TerrainCollider)return;
            Contacts.Add((c.transform.parent?c.transform.parent.name+"/":"")+c.name);
        }
    }
}
#endif
