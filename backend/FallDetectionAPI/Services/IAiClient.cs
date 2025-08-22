using FallDetectionAPI.Models;

namespace FallDetectionAPI.Services;

public interface IAiClient
{
    Task<AiResult> DetectFallAsync(byte[] imageBytes, CancellationToken cancellationToken = default);
    Task<AiBatchResult> DetectFallBatchAsync(IEnumerable<byte[]> imageBytesList, CancellationToken cancellationToken = default);
    Task<bool> HealthCheckAsync(CancellationToken cancellationToken = default);
    
    // New methods for results and statistics
    Task<AiStatistics> GetStatisticsAsync(CancellationToken cancellationToken = default);
    Task<AiResult?> GetResultAsync(string imageHash, CancellationToken cancellationToken = default);
    Task<AiHealth> GetHealthAsync(CancellationToken cancellationToken = default);
}
