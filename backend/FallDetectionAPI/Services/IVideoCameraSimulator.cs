namespace FallDetectionAPI.Services;

public interface IVideoCameraSimulator
{
    Task StartSimulationAsync(CancellationToken cancellationToken = default);
    Task StopSimulationAsync();
    bool IsRunning { get; }
    int FramesSent { get; }
    Dictionary<int, int> CameraFrameCounts { get; }
}
