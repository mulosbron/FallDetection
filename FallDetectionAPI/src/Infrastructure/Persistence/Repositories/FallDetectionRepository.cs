using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Domain.Entities;
using FallDetectionAPI.Persistence.Data;
using Microsoft.EntityFrameworkCore;

namespace FallDetectionAPI.Persistence.Repositories;

public class FallDetectionRepository : IFallDetectionRepository
{
    private readonly AppDbContext _dbContext;

    public FallDetectionRepository(AppDbContext dbContext)
    {
        _dbContext = dbContext;
    }

    public async Task<IReadOnlyList<string>> GetAllHashesAsync(CancellationToken cancellationToken = default)
    {
        return await _dbContext.FallDetections
            .OrderByDescending(x => x.CreatedAt)
            .Select(x => x.ImageHash)
            .ToListAsync(cancellationToken);
    }

    public async Task AddAsync(FallDetectionRecord record, CancellationToken cancellationToken = default)
    {
        await _dbContext.FallDetections.AddAsync(record, cancellationToken);
        await _dbContext.SaveChangesAsync(cancellationToken);
    }

    public Task<int> GetTotalCountAsync(CancellationToken cancellationToken = default) =>
        _dbContext.FallDetections.CountAsync(cancellationToken);

    public Task<int> GetResultCountAsync(string result, CancellationToken cancellationToken = default) =>
        _dbContext.FallDetections.CountAsync(x => x.Result == result, cancellationToken);

    public async Task<IReadOnlyList<FallDetectionRecord>> GetIncidentsAsync(int page, int pageSize, string? status, string? type, CancellationToken cancellationToken = default)
    {
        var query = _dbContext.FallDetections.AsQueryable();

        if (!string.IsNullOrWhiteSpace(status) && status != "all")
        {
            if (status == "resolved") query = query.Where(f => f.Result == "No");
            else if (status is "new" or "investigating") query = query.Where(f => f.Result == "Yes");
        }

        if (!string.IsNullOrWhiteSpace(type) && type != "all")
        {
            query = query.Where(f => f.Result == "Yes");
        }

        return await query
            .OrderByDescending(f => f.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync(cancellationToken);
    }

    public async Task<IReadOnlyDictionary<int, int>> GetCameraCountsAsync(CancellationToken cancellationToken = default)
    {
        return await _dbContext.FallDetections
            .GroupBy(x => x.CameraIndex)
            .Select(g => new { CameraIndex = g.Key, Count = g.Count() })
            .ToDictionaryAsync(x => x.CameraIndex, x => x.Count, cancellationToken);
    }
}
