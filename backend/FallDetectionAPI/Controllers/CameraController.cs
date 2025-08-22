using Microsoft.AspNetCore.Mvc;
using FallDetectionAPI.Services;

namespace FallDetectionAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class CameraController : ControllerBase
{
    private readonly IVideoCameraSimulator _videoCameraSimulator;
    private readonly IFrameQueue _frameQueue;
    private readonly ILogger<CameraController> _logger;

    public CameraController(
        IVideoCameraSimulator videoCameraSimulator,
        IFrameQueue frameQueue,
        ILogger<CameraController> logger)
    {
        _videoCameraSimulator = videoCameraSimulator;
        _frameQueue = frameQueue;
        _logger = logger;
    }

    // === VIDEO SIMULATION ENDPOINTS ===
    
    [HttpPost("start")]
    public async Task<IActionResult> StartSimulation()
    {
        try
        {
            if (_videoCameraSimulator.IsRunning)
            {
                return BadRequest(new { error = "Video camera simulation is already running" });
            }

            await _videoCameraSimulator.StartSimulationAsync();
            
            _logger.LogInformation("Video camera simulation started via API");
            
            return Ok(new { 
                message = "Video camera simulation started",
                cameras = 4,
                videoSource = "MP4 files in Videos/ folder",
                targetFps = "~10 FPS per camera from video frames",
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start video camera simulation");
            return StatusCode(500, new { error = "Failed to start video camera simulation" });
        }
    }

    [HttpPost("stop")]
    public async Task<IActionResult> StopSimulation()
    {
        try
        {
            if (!_videoCameraSimulator.IsRunning)
            {
                return BadRequest(new { error = "Video camera simulation is not running" });
            }

            await _videoCameraSimulator.StopSimulationAsync();
            
            _logger.LogInformation("Video camera simulation stopped via API");
            
            return Ok(new { 
                message = "Video camera simulation stopped",
                totalFramesSent = _videoCameraSimulator.FramesSent,
                cameraFrameCounts = _videoCameraSimulator.CameraFrameCounts,
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to stop video camera simulation");
            return StatusCode(500, new { error = "Failed to stop video camera simulation" });
        }
    }

    [HttpGet("status")]
    public IActionResult GetSimulationStatus()
    {
        return Ok(new {
            isRunning = _videoCameraSimulator.IsRunning,
            framesSent = _videoCameraSimulator.FramesSent,
            cameraFrameCounts = _videoCameraSimulator.CameraFrameCounts,
            queueCount = _frameQueue.Count,
            cameras = new[] { 1, 2, 3, 4 },
            videoFiles = new[] { 
                "camera1_loop.mp4", 
                "camera2_loop.mp4", 
                "camera3_loop.mp4", 
                "camera4_loop.mp4" 
            },
            timestamp = DateTime.UtcNow
        });
    }

    [HttpGet("metrics")]
    public IActionResult GetSimulationMetrics()
    {
        var framesPerSecond = _videoCameraSimulator.IsRunning ? "~40 FPS total (4 video cameras * ~10 FPS)" : "0 FPS";
        
        return Ok(new {
            type = "video_simulation",
            totalCameras = 4,
            framesPerSecond = framesPerSecond,
            totalFramesSent = _videoCameraSimulator.FramesSent,
            cameraBreakdown = _videoCameraSimulator.CameraFrameCounts,
            queueStatus = new {
                count = _frameQueue.Count,
                status = _frameQueue.Count < 150 ? "normal" : "high_load"
            },
            simulationRunning = _videoCameraSimulator.IsRunning,
            videoSource = "Real MP4 files with FFmpeg frame extraction",
            timestamp = DateTime.UtcNow
        });
    }
}
