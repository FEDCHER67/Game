using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;

namespace OnlyVolunteers.Map.W19
{
    // Opens the scene named in Temp/open_scene_once.txt after the next domain reload, then deletes the request.
    // Lets an agent open a scene for Vadim when the Unity MCP bridge is down.
    [InitializeOnLoad]
    static class W19OpenSceneOnce
    {
        const string Request = "Temp/open_scene_once.txt";

        static W19OpenSceneOnce() => EditorApplication.delayCall += Open;

        static void Open()
        {
            if (!File.Exists(Request) || EditorApplication.isPlayingOrWillChangePlaymode) return;
            string path = File.ReadAllText(Request).Trim();
            File.Delete(Request);
            if (File.Exists(path) && EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                EditorSceneManager.OpenScene(path);
        }
    }
}
