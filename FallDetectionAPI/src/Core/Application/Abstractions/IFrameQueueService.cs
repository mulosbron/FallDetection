using FallDetectionAPI.Application.Models;

namespace FallDetectionAPI.Application.Abstractions;

public interface IFrameQueueService
{
    Task<bool> EnqueueFrameAsync(byte[] imageData, int cameraIndex, string fileName, CancellationToken cancellationToken = default);
    QueueStatusDto GetQueueStatus();
}
