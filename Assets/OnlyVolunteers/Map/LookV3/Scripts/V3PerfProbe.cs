using Unity.Profiling;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // Quick render profile for the style v3 smoke run: added to the Play session by the editor tooling (never saved in a
    // scene), it averages frame time, SetPass calls, draw calls and triangles over a window that Reset() starts.
    public sealed class V3PerfProbe : MonoBehaviour
    {
        private ProfilerRecorder setPass, drawCalls, triangles, vertices, mainThread;
        public int Frames;
        public double SumDt, MaxDt, SumSetPass, SumDraws, SumTris, SumVerts, SumMain;

        private void OnEnable()
        {
            setPass = ProfilerRecorder.StartNew(ProfilerCategory.Render, "SetPass Calls Count");
            drawCalls = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Batches Count");
            triangles = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Triangles Count");
            vertices = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Vertices Count");
            mainThread = ProfilerRecorder.StartNew(ProfilerCategory.Internal, "Main Thread", 15);
        }

        private void OnDisable()
        {
            setPass.Dispose();
            drawCalls.Dispose();
            triangles.Dispose();
            vertices.Dispose();
            mainThread.Dispose();
        }

        public void ResetStats()
        {
            Frames = 0;
            SumDt = MaxDt = SumSetPass = SumDraws = SumTris = SumVerts = SumMain = 0;
        }

        private void Update()
        {
            Frames++;
            double dt = Time.unscaledDeltaTime;
            SumDt += dt;
            if (dt > MaxDt) MaxDt = dt;
            SumSetPass += setPass.LastValue;
            SumDraws += drawCalls.LastValue;
            SumTris += triangles.LastValue;
            SumVerts += vertices.LastValue;
            SumMain += mainThread.LastValue * 1e-6;
        }

        public string Report(string label)
        {
            if (Frames == 0) return label + ": no frames";
            double n = Frames;
            return $"{label}: {Frames} frames, {n / SumDt:0.0} fps avg (frame {SumDt / n * 1000.0:0.0} ms, worst {MaxDt * 1000.0:0.0} ms), main thread {SumMain / n:0.0} ms, " +
                   $"SetPass {SumSetPass / n:0}, batches {SumDraws / n:0}, triangles {SumTris / n / 1e6:0.00} M, vertices {SumVerts / n / 1e6:0.00} M";
        }
    }
}
