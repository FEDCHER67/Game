using NUnit.Framework;

namespace Friendslop.Network.Tests.EditMode
{
    public sealed class ParticipantRegistryTests
    {
        [Test]
        public void DuplicateParticipantIsRejected()
        {
            var registry = new ParticipantRegistry();

            Assert.That(registry.TryAdd(12), Is.True);
            Assert.That(registry.TryAdd(12), Is.False);
            Assert.That(registry.Count, Is.EqualTo(1));
        }

        [Test]
        public void RemoveAndClearAreIdempotent()
        {
            var registry = new ParticipantRegistry();
            registry.TryAdd(2);
            registry.TryAdd(7);

            Assert.That(registry.Remove(2), Is.True);
            Assert.That(registry.Remove(2), Is.False);
            registry.Clear();
            registry.Clear();

            Assert.That(registry.Count, Is.Zero);
        }
    }
}
