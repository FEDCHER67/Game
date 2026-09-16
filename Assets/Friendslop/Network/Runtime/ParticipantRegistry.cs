using System.Collections.Generic;

namespace Friendslop.Network
{
    internal sealed class ParticipantRegistry
    {
        private readonly HashSet<int> _connectionIds = new HashSet<int>();

        public int Count => _connectionIds.Count;

        public bool TryAdd(int connectionId)
        {
            return _connectionIds.Add(connectionId);
        }

        public bool Contains(int connectionId)
        {
            return _connectionIds.Contains(connectionId);
        }

        public bool Remove(int connectionId)
        {
            return _connectionIds.Remove(connectionId);
        }

        public void Clear()
        {
            _connectionIds.Clear();
        }
    }
}
