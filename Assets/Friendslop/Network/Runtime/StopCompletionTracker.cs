namespace Friendslop.Network
{
    internal sealed class StopCompletionTracker
    {
        private bool _waitingForClient;
        private bool _waitingForServer;

        public bool IsComplete => !_waitingForClient && !_waitingForServer;

        public void Begin(bool waitForClient, bool waitForServer)
        {
            _waitingForClient = waitForClient;
            _waitingForServer = waitForServer;
        }

        public void AcknowledgeClientStopped()
        {
            _waitingForClient = false;
        }

        public void AcknowledgeServerStopped()
        {
            _waitingForServer = false;
        }
    }
}
