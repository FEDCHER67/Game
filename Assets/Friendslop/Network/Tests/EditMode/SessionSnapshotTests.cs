using System.Reflection;
using NUnit.Framework;

namespace Friendslop.Network.Tests.EditMode
{
    public sealed class SessionSnapshotTests
    {
        [Test]
        public void SnapshotExposesOnlyReadOnlyProperties()
        {
            var snapshot = new SessionSnapshot(SessionState.Client, 8, 2, "diagnostic");

            Assert.That(snapshot.State, Is.EqualTo(SessionState.Client));
            Assert.That(snapshot.LocalConnectionId, Is.EqualTo(8));
            Assert.That(snapshot.ParticipantCount, Is.EqualTo(2));
            Assert.That(snapshot.LastFailure, Is.EqualTo("diagnostic"));
            foreach (var property in typeof(SessionSnapshot).GetProperties(BindingFlags.Instance | BindingFlags.Public))
                Assert.That(property.SetMethod, Is.Null, $"{property.Name} must not be mutable.");
        }
    }
}
