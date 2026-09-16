using System;

namespace Friendslop.Network
{
    public sealed class SessionSnapshot
    {
        public SessionSnapshot(
            SessionState state,
            int? localConnectionId,
            int participantCount,
            string lastFailure)
        {
            if (participantCount < 0)
                throw new ArgumentOutOfRangeException(nameof(participantCount));

            State = state;
            LocalConnectionId = localConnectionId;
            ParticipantCount = participantCount;
            LastFailure = lastFailure;
        }

        public SessionState State { get; }

        public int? LocalConnectionId { get; }

        public int ParticipantCount { get; }

        public string LastFailure { get; }
    }
}
