using NUnit.Framework;

namespace Friendslop.Network.Tests.EditMode
{
    public sealed class SessionLifecycleTests
    {
        [Test]
        public void NewLifecycleIsStopped()
        {
            var lifecycle = new SessionLifecycle();

            Assert.That(lifecycle.State, Is.EqualTo(SessionState.Stopped));
            Assert.That(lifecycle.Generation, Is.Zero);
            Assert.That(lifecycle.LastFailure, Is.Null);
        }

        [Test]
        public void DuplicateStartIsRejectedWithoutChangingTheActiveAttempt()
        {
            var lifecycle = new SessionLifecycle();
            Assert.That(lifecycle.TryBeginHost(out var generation, out _), Is.True);

            Assert.That(lifecycle.TryBeginClient(out var duplicateGeneration, out var error), Is.False);

            Assert.That(lifecycle.State, Is.EqualTo(SessionState.StartingHost));
            Assert.That(lifecycle.Generation, Is.EqualTo(generation));
            Assert.That(duplicateGeneration, Is.EqualTo(generation));
            Assert.That(error, Does.Contain("already"));
        }

        [Test]
        public void StopIsIdempotent()
        {
            var lifecycle = new SessionLifecycle();
            Assert.That(lifecycle.TryBeginHost(out _, out _), Is.True);

            Assert.That(lifecycle.TryBeginStop(), Is.True);
            Assert.That(lifecycle.TryBeginStop(), Is.False);
            Assert.That(lifecycle.State, Is.EqualTo(SessionState.Stopping));
        }

        [Test]
        public void StaleGenerationCannotCompleteANewerAttempt()
        {
            var lifecycle = new SessionLifecycle();
            lifecycle.TryBeginHost(out var oldGeneration, out _);
            lifecycle.Fail(oldGeneration, "first attempt failed");
            lifecycle.TryBeginClient(out var currentGeneration, out _);

            Assert.That(lifecycle.TryMarkHostReady(oldGeneration), Is.False);
            Assert.That(lifecycle.State, Is.EqualTo(SessionState.StartingClient));
            Assert.That(lifecycle.TryMarkClientReady(currentGeneration), Is.True);
            Assert.That(lifecycle.State, Is.EqualTo(SessionState.Client));
        }

        [Test]
        public void FailedAttemptCanBeFollowedByAFreshAttempt()
        {
            var lifecycle = new SessionLifecycle();
            lifecycle.TryBeginClient(out var failedGeneration, out _);
            lifecycle.Fail(failedGeneration, "Connection refused.");

            Assert.That(lifecycle.TryBeginClient(out var freshGeneration, out _), Is.True);

            Assert.That(freshGeneration, Is.EqualTo(failedGeneration + 1));
            Assert.That(lifecycle.State, Is.EqualTo(SessionState.StartingClient));
            Assert.That(lifecycle.LastFailure, Is.Null);
        }
    }
}
