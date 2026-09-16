namespace Friendslop.Network
{
    internal sealed class SessionLifecycle
    {
        public SessionState State { get; private set; } = SessionState.Stopped;

        public int Generation { get; private set; }

        public string LastFailure { get; private set; }

        public bool TryBeginHost(out int generation, out string error)
        {
            return TryBegin(SessionState.StartingHost, out generation, out error);
        }

        public bool TryBeginClient(out int generation, out string error)
        {
            return TryBegin(SessionState.StartingClient, out generation, out error);
        }

        public bool TryBeginStop()
        {
            if (State == SessionState.Stopped || State == SessionState.Stopping)
                return false;

            State = SessionState.Stopping;
            return true;
        }

        public bool TryMarkHostReady(int generation)
        {
            return TryTransition(generation, SessionState.StartingHost, SessionState.Host);
        }

        public bool TryMarkClientReady(int generation)
        {
            return TryTransition(generation, SessionState.StartingClient, SessionState.Client);
        }

        public bool MarkStopped(int generation)
        {
            if (generation != Generation)
                return false;

            State = SessionState.Stopped;
            LastFailure = null;
            return true;
        }

        public bool Fail(int generation, string failure)
        {
            if (generation != Generation)
                return false;

            State = SessionState.Failed;
            LastFailure = string.IsNullOrWhiteSpace(failure)
                ? "The network session failed without a diagnostic."
                : failure;
            return true;
        }

        private bool TryBegin(SessionState startingState, out int generation, out string error)
        {
            if (State != SessionState.Stopped && State != SessionState.Failed)
            {
                generation = Generation;
                error = $"A session is already active or changing state ({State}).";
                return false;
            }

            Generation++;
            generation = Generation;
            State = startingState;
            LastFailure = null;
            error = null;
            return true;
        }

        private bool TryTransition(int generation, SessionState expected, SessionState next)
        {
            if (generation != Generation || State != expected)
                return false;

            State = next;
            return true;
        }
    }
}
