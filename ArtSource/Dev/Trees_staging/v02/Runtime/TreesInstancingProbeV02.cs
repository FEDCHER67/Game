using UnityEngine;
using UnityEngine.Rendering;

namespace OnlyVolunteers.Trees
{
    // Test-scene-only explicit GPU instancing probe. No component is added to tree prefabs.
    public sealed class TreesInstancingProbeV02 : MonoBehaviour
    {
        [SerializeField] private Mesh mesh;
        [SerializeField] private Material material;
        private readonly Matrix4x4[] matrices = new Matrix4x4[16];
        public int SubmittedInstances { get; private set; }
        public void Configure(Mesh value, Material surface) { mesh = value; material = surface; }
        private void Awake()
        {
            for (int i = 0; i < matrices.Length; i++)
                matrices[i] = Matrix4x4.TRS(transform.position + new Vector3((i % 4) * 6, 0, (i / 4) * 7), Quaternion.Euler(0, i * 23, 0), new Vector3(1.25f, .78f, 1.25f));
        }
        private void Update()
        {
            if (!mesh || !material || !SystemInfo.supportsInstancing) return;
            var parameters = new RenderParams(material)
            {
                worldBounds = new Bounds(transform.position + new Vector3(9, 4, 10.5f), new Vector3(32, 16, 38)),
                shadowCastingMode = ShadowCastingMode.On,
                receiveShadows = true
            };
            Graphics.RenderMeshInstanced(parameters, mesh, 0, matrices);
            SubmittedInstances = matrices.Length;
        }
    }
}
