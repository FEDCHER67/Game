namespace Friendslop.Network.Physics
{
    internal sealed class GrabLeaseState
    {
        private int? _holderConnectionId;

        public int? HolderConnectionId => _holderConnectionId;

        public bool TryAcquire(int connectionId)
        {
            if (connectionId < 0 || _holderConnectionId.HasValue)
                return false;

            _holderConnectionId = connectionId;
            return true;
        }

        public bool TryRelease(int connectionId)
        {
            if (_holderConnectionId != connectionId)
                return false;

            _holderConnectionId = null;
            return true;
        }

        public bool ForceRelease()
        {
            if (!_holderConnectionId.HasValue)
                return false;

            _holderConnectionId = null;
            return true;
        }
    }
}
