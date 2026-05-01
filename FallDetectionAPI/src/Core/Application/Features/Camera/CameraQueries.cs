using System.Text.Json;
using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Application.Models;
using MediatR;

namespace FallDetectionAPI.Application.Features.Camera;

public record StartSimulationCommand() : IRequest<bool>;
public record StopSimulationCommand() : IRequest<bool>;
public record GetCameraStatusQuery() : IRequest<JsonElement>;
public record GetCameraVideosQuery() : IRequest<JsonElement>;
public record GetSimulationStatusQuery() : IRequest<JsonElement>;
public record GetCameraInventoryQuery() : IRequest<IReadOnlyList<CameraStreamDto>>;
public record GetAlertStatusQuery() : IRequest<IReadOnlyList<object>>;
public record GetAllCamerasStatusQuery() : IRequest<AllCamerasStatusResponse>;

public class AllCamerasStatusResponse
{
    public IReadOnlyDictionary<int, object> Cameras { get; init; } = new Dictionary<int, object>();
    public int TotalProcessed { get; init; }
}

public class StartSimulationCommandHandler : IRequestHandler<StartSimulationCommand, bool>
{
    private readonly IMockCameraGateway _gateway;
    public StartSimulationCommandHandler(IMockCameraGateway gateway) => _gateway = gateway;
    public Task<bool> Handle(StartSimulationCommand request, CancellationToken cancellationToken) => _gateway.StartSimulationAsync(cancellationToken);
}

public class StopSimulationCommandHandler : IRequestHandler<StopSimulationCommand, bool>
{
    private readonly IMockCameraGateway _gateway;
    public StopSimulationCommandHandler(IMockCameraGateway gateway) => _gateway = gateway;
    public Task<bool> Handle(StopSimulationCommand request, CancellationToken cancellationToken) => _gateway.StopSimulationAsync(cancellationToken);
}

public class GetCameraStatusQueryHandler : IRequestHandler<GetCameraStatusQuery, JsonElement>
{
    private readonly IMockCameraGateway _gateway;
    public GetCameraStatusQueryHandler(IMockCameraGateway gateway) => _gateway = gateway;
    public Task<JsonElement> Handle(GetCameraStatusQuery request, CancellationToken cancellationToken) => _gateway.GetCameraStatusAsync(cancellationToken);
}

public class GetCameraVideosQueryHandler : IRequestHandler<GetCameraVideosQuery, JsonElement>
{
    private readonly IMockCameraGateway _gateway;
    public GetCameraVideosQueryHandler(IMockCameraGateway gateway) => _gateway = gateway;
    public Task<JsonElement> Handle(GetCameraVideosQuery request, CancellationToken cancellationToken) => _gateway.GetCameraVideosAsync(cancellationToken);
}

public class GetSimulationStatusQueryHandler : IRequestHandler<GetSimulationStatusQuery, JsonElement>
{
    private readonly IMockCameraGateway _gateway;
    public GetSimulationStatusQueryHandler(IMockCameraGateway gateway) => _gateway = gateway;
    public Task<JsonElement> Handle(GetSimulationStatusQuery request, CancellationToken cancellationToken) => _gateway.GetSimulationStatusAsync(cancellationToken);
}

public class GetCameraInventoryQueryHandler : IRequestHandler<GetCameraInventoryQuery, IReadOnlyList<CameraStreamDto>>
{
    private readonly IMockCameraGateway _gateway;

    public GetCameraInventoryQueryHandler(IMockCameraGateway gateway)
    {
        _gateway = gateway;
    }

    public Task<IReadOnlyList<CameraStreamDto>> Handle(GetCameraInventoryQuery request, CancellationToken cancellationToken) =>
        _gateway.GetCameraInventoryAsync(cancellationToken);
}

public class GetAlertStatusQueryHandler : IRequestHandler<GetAlertStatusQuery, IReadOnlyList<object>>
{
    private readonly ICameraAlertService _cameraAlertService;

    public GetAlertStatusQueryHandler(ICameraAlertService cameraAlertService)
    {
        _cameraAlertService = cameraAlertService;
    }

    public Task<IReadOnlyList<object>> Handle(GetAlertStatusQuery request, CancellationToken cancellationToken)
    {
        var rows = _cameraAlertService.GetCameraCounters()
            .Select(kvp => (object)new
            {
                CameraIndex = kvp.Key,
                YesCount = kvp.Value.YesCount,
                TotalCount = kvp.Value.TotalCount,
                AlertThreshold = 1,
                ResetThreshold = 10,
                AlertStatus = kvp.Value.YesCount >= 1 ? "🚨 ALERT READY" : "✅ NORMAL"
            })
            .ToList();

        return Task.FromResult<IReadOnlyList<object>>(rows);
    }
}

public class GetAllCamerasStatusQueryHandler : IRequestHandler<GetAllCamerasStatusQuery, AllCamerasStatusResponse>
{
    private readonly IFallDetectionRepository _repository;

    public GetAllCamerasStatusQueryHandler(IFallDetectionRepository repository)
    {
        _repository = repository;
    }

    public async Task<AllCamerasStatusResponse> Handle(GetAllCamerasStatusQuery request, CancellationToken cancellationToken)
    {
        var counts = await _repository.GetCameraCountsAsync(cancellationToken);
        var cameras = new Dictionary<int, object>();

        for (var i = 1; i <= 4; i++)
        {
            var count = counts.TryGetValue(i, out var value) ? value : 0;
            cameras[i] = new
            {
                CameraIndex = i,
                YesCount = 0,
                NoCount = count,
                TotalCount = count,
                AlertStatus = "✅ NORMAL"
            };
        }

        return new AllCamerasStatusResponse
        {
            Cameras = cameras,
            TotalProcessed = counts.Values.Sum()
        };
    }
}
