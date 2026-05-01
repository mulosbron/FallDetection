using FallDetectionAPI.SignalR.Hubs;
using FallDetectionAPI.SignalR.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;

namespace FallDetectionAPI.SignalR.Controllers;

[ApiController]
[Route("internal/notify")]
public class InternalNotificationsController : ControllerBase
{
    private readonly IHubContext<AlertHub> _hubContext;
    private readonly ILogger<InternalNotificationsController> _logger;

    public InternalNotificationsController(IHubContext<AlertHub> hubContext, ILogger<InternalNotificationsController> logger)
    {
        _hubContext = hubContext;
        _logger = logger;
    }

    [HttpPost("camera-update")]
    public async Task<IActionResult> PublishCameraUpdate([FromBody] CameraUpdateEvent payload)
    {
        var cameraGroup = $"Camera_{ParseCameraIndex(payload.CameraId)}";
        _logger.LogInformation(
            "Publishing CameraUpdate cameraId={CameraId} yes={YesCount} total={TotalCount} result={Result}",
            payload.CameraId, payload.YesCount, payload.TotalCount, payload.Result);
        await _hubContext.Clients.All.SendAsync("CameraUpdate", payload);
        await _hubContext.Clients.Group(cameraGroup).SendAsync("CameraUpdate", payload);
        return Ok(new { published = true });
    }

    [HttpPost("fall-detected")]
    public async Task<IActionResult> PublishFallDetected([FromBody] FallDetectedEvent payload)
    {
        var cameraGroup = $"Camera_{ParseCameraIndex(payload.CameraId)}";
        _logger.LogInformation(
            "Publishing FallDetected cameraId={CameraId} yes={YesCount} total={TotalCount} message={Message}",
            payload.CameraId, payload.YesCount, payload.TotalCount, payload.Message);
        await _hubContext.Clients.All.SendAsync("FallDetected", payload);
        await _hubContext.Clients.Group("Alerts").SendAsync("FallDetected", payload);
        await _hubContext.Clients.Group(cameraGroup).SendAsync("FallDetected", payload);
        return Ok(new { published = true });
    }

    private static int ParseCameraIndex(string cameraId)
    {
        if (cameraId.StartsWith("cam-", StringComparison.OrdinalIgnoreCase) &&
            int.TryParse(cameraId[4..], out var parsed))
        {
            return parsed;
        }

        return 0;
    }
}
