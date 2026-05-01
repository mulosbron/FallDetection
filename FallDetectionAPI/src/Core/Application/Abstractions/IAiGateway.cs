using FallDetectionAPI.Application.Models;

namespace FallDetectionAPI.Application.Abstractions;

public interface IAiGateway
{
    Task<AiResultDto> DetectFallAsync(byte[] imageBytes, int cameraIndex, CancellationToken cancellationToken = default);
    Task<AiBatchResultDto> DetectFallBatchAsync(IEnumerable<byte[]> imageBytesList, int cameraIndex, CancellationToken cancellationToken = default);
    Task<AiStatisticsDto> GetStatisticsAsync(CancellationToken cancellationToken = default);
    Task<AiResultDto?> GetResultAsync(string imageHash, CancellationToken cancellationToken = default);
    Task<AiHealthDto> GetHealthAsync(CancellationToken cancellationToken = default);
}
