using System;

namespace Friendslop.Network
{
    public interface ISessionController
    {
        SessionSnapshot Snapshot { get; }

        event Action<SessionSnapshot> SnapshotChanged;

        bool StartHost(ushort port);

        bool StartClient(string address, ushort port);

        void Stop();
    }
}
