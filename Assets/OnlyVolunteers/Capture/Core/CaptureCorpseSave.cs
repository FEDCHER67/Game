using System;
using OnlyVolunteers.Operation.Stage1;
using UnityEngine;

namespace OnlyVolunteers.Capture
{
    [Serializable]
    public sealed class CaptureCorpseSave
    {
        public CaptureFacts facts;
        public OperationState operation;
        public bool bagged, held;
        public Vector3 position;
        public Quaternion rotation = Quaternion.identity;
        public Vector3[] bonePositions;
        public Quaternion[] boneRotations;
    }
    [Serializable]
    public struct CaptureWitnessHook
    {
        public string patientId, districtId;
        public bool bagged;
        public int points;
    }
}
