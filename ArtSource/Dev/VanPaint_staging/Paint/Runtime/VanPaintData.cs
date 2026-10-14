using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Vehicles.Paint
{
    [Serializable]
    public struct PaintDab
    {
        public Vector2 uv;
        public Vector2 radius;
        public Rect clip;
        public PaintDab(Vector2 uv, Vector2 radius, Rect clip)
        { this.uv = uv; this.radius = radius; this.clip = clip; }
    }

    // Transport-neutral commands. A stroke (including lettering) is one undo unit.
    [Serializable]
    public sealed class PaintStroke
    {
        public string id = Guid.NewGuid().ToString("N");
        public Color color;
        public string text;
        public List<PaintDab> dabs = new();
    }

    [Serializable]
    public sealed class VanPaintSave
    {
        public int version = 1;
        public string vanId;
        public int resolution;
        public string pngFile;
        public string pngSha256;
        public List<PaintStroke> strokes = new();
    }
}
