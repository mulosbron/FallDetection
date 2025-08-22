namespace FallDetectionAPI.Models;

public record FrameJob(
    Guid Id,
    byte[] ImageBytes,
    DateTime EnqueuedAt
);
