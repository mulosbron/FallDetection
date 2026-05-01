namespace FallDetectionAPI.Application.Abstractions;

public interface IRealtimeNotifier
{
    Task PublishCameraUpdateAsync(object payload, CancellationToken cancellationToken = default);
    Task PublishFallDetectedAsync(object payload, CancellationToken cancellationToken = default);
}
