using FallDetectionAPI.Domain.Entities;

namespace FallDetectionAPI.Application.Abstractions;

public interface IFallDetectionRepository
{
    Task AddAsync(FallDetectionRecord record, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<string>> GetAllHashesAsync(CancellationToken cancellationToken = default);
    Task<int> GetTotalCountAsync(CancellationToken cancellationToken = default);
    Task<int> GetResultCountAsync(string result, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<FallDetectionRecord>> GetIncidentsAsync(int page, int pageSize, string? status, string? type, CancellationToken cancellationToken = default);
    Task<IReadOnlyDictionary<int, int>> GetCameraCountsAsync(CancellationToken cancellationToken = default);
}
