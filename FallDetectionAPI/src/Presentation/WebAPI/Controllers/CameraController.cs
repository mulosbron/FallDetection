using FallDetectionAPI.Application.Features.Camera;
using MediatR;
using Microsoft.AspNetCore.Mvc;

namespace FallDetectionAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class CameraController : ControllerBase
{
    private readonly IMediator _mediator;
    private readonly ILogger<CameraController> _logger;

    public CameraController(IMediator mediator, ILogger<CameraController> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    [HttpPost("start")]
    public async Task<IActionResult> StartSimulation()
    {
        try
        {
            var ok = await _mediator.Send(new StartSimulationCommand());
            if (!ok) return StatusCode(503, new { error = "Failed to start camera simulation" });

            return Ok(new
            {
                message = "Camera simulation started",
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start camera simulation");
            return StatusCode(503, new { error = "Camera simulation service unavailable" });
        }
    }

    [HttpPost("stop")]
    public async Task<IActionResult> StopSimulation()
    {
        try
        {
            var ok = await _mediator.Send(new StopSimulationCommand());
            if (!ok) return StatusCode(503, new { error = "Failed to stop camera simulation" });

            return Ok(new
            {
                message = "Camera simulation stopped",
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to stop camera simulation");
            return StatusCode(503, new { error = "Camera simulation service unavailable" });
        }
    }

    [HttpGet("status")]
    public async Task<IActionResult> GetCameraStatus()
    {
        try
        {
            var result = await _mediator.Send(new GetCameraStatusQuery());
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get camera status");
            return StatusCode(503, new { error = "Camera service unavailable" });
        }
    }

    [HttpGet("videos")]
    public async Task<IActionResult> GetCameraVideos()
    {
        try
        {
            var result = await _mediator.Send(new GetCameraVideosQuery());
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get camera videos");
            return StatusCode(503, new { error = "Camera service unavailable" });
        }
    }

    [HttpGet("inventory")]
    public async Task<IActionResult> GetCameraInventory()
    {
        try
        {
            var cameras = await _mediator.Send(new GetCameraInventoryQuery());
            return Ok(new
            {
                cameras,
                total = cameras.Count,
                active = cameras.Count(x => x.IsActive),
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get camera inventory");
            return StatusCode(503, new { error = "Camera inventory unavailable" });
        }
    }

    [HttpGet("simulation-status")]
    public async Task<IActionResult> GetSimulationStatus()
    {
        try
        {
            var simulation = await _mediator.Send(new GetSimulationStatusQuery());
            var alerts = await _mediator.Send(new GetAlertStatusQuery());
            return Ok(new
            {
                simulation,
                alertStatus = alerts,
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get simulation status");
            return StatusCode(503, new { error = "Camera service unavailable" });
        }
    }

    [HttpGet("metrics")]
    public async Task<IActionResult> GetSimulationMetrics()
    {
        try
        {
            var camerasStatus = await _mediator.Send(new GetCameraStatusQuery());
            var counters = await _mediator.Send(new GetAlertStatusQuery());

            return Ok(new
            {
                type = "mock_camera_service",
                cameraStatus = camerasStatus,
                alertCounters = counters,
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get simulation metrics");
            return StatusCode(503, new { error = "Camera service unavailable" });
        }
    }

    [HttpGet("alert-status")]
    public async Task<IActionResult> GetAlertStatus()
    {
        var status = await _mediator.Send(new GetAlertStatusQuery());
        return Ok(new
        {
            Cameras = status,
            AlertThreshold = 1,
            ResetThreshold = 10,
            TotalCameras = status.Count,
            timestamp = DateTime.UtcNow
        });
    }

    [HttpGet("all-cameras-status")]
    public async Task<IActionResult> GetAllCamerasStatus()
    {
        var data = await _mediator.Send(new GetAllCamerasStatusQuery());
        return Ok(new
        {
            Summary = new
            {
                TotalCameras = data.Cameras.Count,
                TotalProcessed = data.TotalProcessed
            },
            Cameras = data.Cameras,
            Timestamp = DateTime.UtcNow
        });
    }

    [HttpGet("health")]
    public IActionResult GetHealth()
    {
        return Ok(new
        {
            Status = "Healthy",
            Service = "Camera Controller",
            AlertSystem = "Active",
            Timestamp = DateTime.UtcNow
        });
    }
}
