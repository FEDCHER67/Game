namespace Friendslop.Network
{
    public enum SessionState
    {
        Stopped,
        StartingHost,
        Host,
        StartingClient,
        Client,
        Stopping,
        Failed
    }
}
