using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Application.Models;
using MediatR;

namespace FallDetectionAPI.Application.Features.Results;

public record GetAiStatisticsQuery() : IRequest<AiStatisticsDto>;
public record GetAiHealthQuery() : IRequest<AiHealthDto>;
public record GetResultByHashQuery(string ImageHash) : IRequest<AiResultDto?>;
public record GetAllHashesQuery() : IRequest<IReadOnlyList<string>>;
public record GetIncidentsQuery(int Page, int PageSize, string? Status, string? Type) : IRequest<IncidentsResponse>;
public record GetNetApiHealthQuery() : IRequest<NetApiHealthResponse>;

public class IncidentsResponse
{
    public IReadOnlyList<object> Incidents { get; init; } = Array.Empty<object>();
    public int TotalCount { get; init; }
    public int NewIncidents { get; init; }
    public int ResolvedIncidents { get; init; }
    public int Page { get; init; }
    public int PageSize { get; init; }
}

public class NetApiHealthResponse
{
    public string Status { get; init; } = "healthy";
    public string Service { get; init; } = ".NET Fall Detection API";
    public string Version { get; init; } = "2.0.0";
    public string Environment { get; init; } = "Production";
    public long UptimeSeconds { get; init; }
    public long MemoryMb { get; init; }
}

public class GetAiStatisticsQueryHandler : IRequestHandler<GetAiStatisticsQuery, AiStatisticsDto>
{
    private readonly IAiGateway _aiGateway;
    public GetAiStatisticsQueryHandler(IAiGateway aiGateway) => _aiGateway = aiGateway;
    public Task<AiStatisticsDto> Handle(GetAiStatisticsQuery request, CancellationToken cancellationToken) =>
        _aiGateway.GetStatisticsAsync(cancellationToken);
}

public class GetAiHealthQueryHandler : IRequestHandler<GetAiHealthQuery, AiHealthDto>
{
    private readonly IAiGateway _aiGateway;
    public GetAiHealthQueryHandler(IAiGateway aiGateway) => _aiGateway = aiGateway;
    public Task<AiHealthDto> Handle(GetAiHealthQuery request, CancellationToken cancellationToken) =>
        _aiGateway.GetHealthAsync(cancellationToken);
}

public class GetResultByHashQueryHandler : IRequestHandler<GetResultByHashQuery, AiResultDto?>
{
    private readonly IAiGateway _aiGateway;
    public GetResultByHashQueryHandler(IAiGateway aiGateway) => _aiGateway = aiGateway;
    public Task<AiResultDto?> Handle(GetResultByHashQuery request, CancellationToken cancellationToken) =>
        _aiGateway.GetResultAsync(request.ImageHash, cancellationToken);
}

public class GetAllHashesQueryHandler : IRequestHandler<GetAllHashesQuery, IReadOnlyList<string>>
{
    private readonly IFallDetectionRepository _repository;
    public GetAllHashesQueryHandler(IFallDetectionRepository repository) => _repository = repository;
    public Task<IReadOnlyList<string>> Handle(GetAllHashesQuery request, CancellationToken cancellationToken) =>
        _repository.GetAllHashesAsync(cancellationToken);
}

public class GetIncidentsQueryHandler : IRequestHandler<GetIncidentsQuery, IncidentsResponse>
{
    private readonly IFallDetectionRepository _repository;

    public GetIncidentsQueryHandler(IFallDetectionRepository repository)
    {
        _repository = repository;
    }

    public async Task<IncidentsResponse> Handle(GetIncidentsQuery request, CancellationToken cancellationToken)
    {
        var incidents = await _repository.GetIncidentsAsync(request.Page, request.PageSize, request.Status, request.Type, cancellationToken);
        var totalCount = await _repository.GetTotalCountAsync(cancellationToken);
        var newCount = await _repository.GetResultCountAsync("Yes", cancellationToken);
        var resolvedCount = await _repository.GetResultCountAsync("No", cancellationToken);

        var mapped = incidents.Select(i => (object)new
        {
            id = i.Id.ToString(),
            cameraId = $"cam-{i.CameraIndex:D3}",
            cameraName = $"Camera {i.CameraIndex}",
            location = $"Video File {i.CameraIndex + 1}",
            timestamp = i.CreatedAt.ToString("yyyy-MM-dd HH:mm:ss"),
            type = i.Result == "Yes" ? "Fall" : "Normal Activity",
            severity = i.Result == "Yes" ? "HIGH" : "LOW",
            status = i.Result == "Yes" ? "New" : "Resolved",
            isAcknowledged = i.Result == "No",
            frameUrl = $"/api/frames/image/{i.ImageHash}",
            imageHash = i.ImageHash,
            processingTime = i.ProcessingTimeMs,
            result = i.Result
        }).ToList();

        return new IncidentsResponse
        {
            Incidents = mapped,
            TotalCount = totalCount,
            NewIncidents = newCount,
            ResolvedIncidents = resolvedCount,
            Page = request.Page,
            PageSize = request.PageSize
        };
    }
}

public class GetNetApiHealthQueryHandler : IRequestHandler<GetNetApiHealthQuery, NetApiHealthResponse>
{
    public Task<NetApiHealthResponse> Handle(GetNetApiHealthQuery request, CancellationToken cancellationToken)
    {
        return Task.FromResult(new NetApiHealthResponse
        {
            Environment = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Production",
            UptimeSeconds = Environment.TickCount64 / 1000,
            MemoryMb = GC.GetTotalMemory(false) / 1024 / 1024
        });
    }
}
