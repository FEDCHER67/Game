#if UNITY_EDITOR
using System.Collections;
using FishNet.Managing;
using FishNet.Transporting.Tugboat;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Friendslop.Network.Tests.PlayMode
{
    public sealed class ValidationSceneTests
    {
        private const string ScenePath =
            "Assets/Friendslop/Network/Validation/MultiplayerBootstrapValidation.unity";

        [UnityTest]
        public IEnumerator ValidationSceneInitializesOneNeutralBootstrap()
        {
            yield return EditorSceneManager.LoadSceneInPlayMode(
                ScenePath,
                new LoadSceneParameters(LoadSceneMode.Single));

            NetworkManager[] managers = Object.FindObjectsByType<NetworkManager>();
            Assert.That(managers, Has.Length.EqualTo(1));

            NetworkManager manager = managers[0];
            Assert.That(manager.Initialized, Is.True);
            Assert.That(manager.TransportManager.Transport, Is.TypeOf<Tugboat>());
            Assert.That(manager.GetComponent<FishNetSessionController>(), Is.Not.Null);
            Assert.That(manager.GetComponent<FishNetSessionController>().Snapshot.State, Is.EqualTo(SessionState.Stopped));
            Assert.That(manager.SpawnablePrefabs.GetObjectCount(), Is.EqualTo(1));

            GameObject player = manager.SpawnablePrefabs.GetObject(true, 0).gameObject;
            Assert.That(player.GetComponent<NeutralNetworkPlayer>(), Is.Not.Null);
            Assert.That(player.GetComponent<Rigidbody>(), Is.Null);

            Object.Destroy(manager.gameObject);
            yield return null;
        }
    }
}
#endif
