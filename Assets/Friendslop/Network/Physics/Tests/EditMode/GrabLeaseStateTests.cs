using NUnit.Framework;

namespace Friendslop.Network.Physics.Tests
{
    public sealed class GrabLeaseStateTests
    {
        [Test]
        public void FirstConnectionAcquiresExclusiveLease()
        {
            GrabLeaseState lease = new GrabLeaseState();

            Assert.That(lease.TryAcquire(4), Is.True);
            Assert.That(lease.HolderConnectionId, Is.EqualTo(4));
            Assert.That(lease.TryAcquire(7), Is.False);
            Assert.That(lease.HolderConnectionId, Is.EqualTo(4));
        }

        [Test]
        public void ForeignReleaseCannotClearLease()
        {
            GrabLeaseState lease = new GrabLeaseState();
            lease.TryAcquire(4);

            Assert.That(lease.TryRelease(7), Is.False);
            Assert.That(lease.HolderConnectionId, Is.EqualTo(4));
        }

        [Test]
        public void HolderReleaseAllowsFreshAcquisition()
        {
            GrabLeaseState lease = new GrabLeaseState();
            lease.TryAcquire(4);

            Assert.That(lease.TryRelease(4), Is.True);
            Assert.That(lease.TryAcquire(7), Is.True);
            Assert.That(lease.HolderConnectionId, Is.EqualTo(7));
        }

        [Test]
        public void ForceReleaseIsIdempotent()
        {
            GrabLeaseState lease = new GrabLeaseState();
            lease.TryAcquire(4);

            Assert.That(lease.ForceRelease(), Is.True);
            Assert.That(lease.ForceRelease(), Is.False);
            Assert.That(lease.HolderConnectionId, Is.Null);
        }

        [Test]
        public void InvalidConnectionCannotAcquire()
        {
            GrabLeaseState lease = new GrabLeaseState();

            Assert.That(lease.TryAcquire(-1), Is.False);
            Assert.That(lease.HolderConnectionId, Is.Null);
        }
    }
}
