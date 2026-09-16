using NUnit.Framework;

namespace Friendslop.Network.Tests.EditMode
{
    public sealed class StopCompletionTrackerTests
    {
        [Test]
        public void ClientStopRequiresExplicitTerminalAcknowledgement()
        {
            var tracker = new StopCompletionTracker();

            tracker.Begin(waitForClient: true, waitForServer: false);

            Assert.That(tracker.IsComplete, Is.False);
            tracker.AcknowledgeClientStopped();
            Assert.That(tracker.IsComplete, Is.True);
        }

        [Test]
        public void HostStopRequiresBothTerminalAcknowledgements()
        {
            var tracker = new StopCompletionTracker();

            tracker.Begin(waitForClient: true, waitForServer: true);
            tracker.AcknowledgeClientStopped();

            Assert.That(tracker.IsComplete, Is.False);
            tracker.AcknowledgeServerStopped();
            tracker.AcknowledgeServerStopped();
            Assert.That(tracker.IsComplete, Is.True);
        }
    }
}
