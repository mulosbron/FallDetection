using FallDetectionAPI.Models;

namespace FallDetectionAPI.Services;

public interface IFrameQueue
{
    bool TryEnqueue(FrameJob job);
    ValueTask<FrameJob> DequeueAsync(CancellationToken cancellationToken);
    int Count { get; }
}
