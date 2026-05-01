using System.Text.Json;
using FallDetectionAPI.Application.Models;

namespace FallDetectionAPI.Application.Abstractions;

public interface IMockCameraGateway
{
    Task<bool> StartSimulationAsync(CancellationToken cancellationToken = default);
    Task<bool> StopSimulationAsync(CancellationToken cancellationToken = default);
    Task<JsonElement> GetCameraStatusAsync(CancellationToken cancellationToken = default);
    Task<JsonElement> GetCameraVideosAsync(CancellationToken cancellationToken = default);
    Task<JsonElement> GetSimulationStatusAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<CameraStreamDto>> GetCameraInventoryAsync(CancellationToken cancellationToken = default);
}
