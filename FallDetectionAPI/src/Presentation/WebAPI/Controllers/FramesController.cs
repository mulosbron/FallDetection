using Microsoft.AspNetCore.Mvc;
using FallDetectionAPI.Application.Features.Frames;
using MediatR;

namespace FallDetectionAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class FramesController : ControllerBase
{
    private readonly ILogger<FramesController> _logger;
    private readonly IMediator _mediator;

    public FramesController(ILogger<FramesController> logger, IMediator mediator)
    {
        _logger = logger;
        _mediator = mediator;
    }

    [HttpPost]
    public async Task<IActionResult> UploadFrame([FromForm] IFormFile image, [FromForm] int? cameraId = null)
    {
        try
        {
            if (image == null || image.Length == 0)
            {
                return BadRequest(new { error = "No image file provided" });
            }

            var cameraIndex = cameraId ?? 0;
            
            _logger.LogInformation($"📹 Received frame from camera {cameraIndex}, size: {image.Length} bytes");

            // Read image data
            using var memoryStream = new MemoryStream();
            await image.CopyToAsync(memoryStream);
            var imageData = memoryStream.ToArray();

            var command = new UploadFrameCommand(
                imageData,
                cameraIndex,
                image.FileName ?? $"camera_{cameraIndex}_{DateTimeOffset.UtcNow.ToUnixTimeSeconds()}.jpg");
            var enqueueResult = await _mediator.Send(command);
            
            if (enqueueResult.Success)
            {
                _logger.LogDebug($"✅ Frame enqueued successfully for camera {cameraIndex}");
                
                return Ok(new {
                    success = true,
                    camera_id = cameraIndex,
                    message = enqueueResult.Message,
                    queue_size = enqueueResult.QueueSize,
                    timestamp = DateTime.UtcNow
                });
            }
            else
            {
                _logger.LogWarning($"⚠️ Failed to enqueue frame for camera {cameraIndex} - queue is full");
                return StatusCode(503, new {
                    error = "Service unavailable",
                    camera_id = cameraIndex,
                    message = "Frame queue is full"
                });
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, $"❌ Error processing frame from camera {cameraId}");
            return StatusCode(500, new {
                error = "Internal server error",
                camera_id = cameraId,
                message = ex.Message
            });
        }
    }

    [HttpPost("raw")]
    public async Task<IActionResult> UploadRawFrame([FromQuery] int? cameraId = null)
    {
        try
        {
            if (Request.ContentLength is null or <= 0)
            {
                return BadRequest(new { error = "Empty body" });
            }

            var cameraIndex = cameraId ?? 0;
            using var memoryStream = new MemoryStream();
            await Request.Body.CopyToAsync(memoryStream);
            var imageData = memoryStream.ToArray();
            if (imageData.Length == 0)
            {
                return BadRequest(new { error = "Empty image payload" });
            }

            _logger.LogInformation("📹 Received RAW frame from camera {CameraIndex}, size: {Size} bytes", cameraIndex, imageData.Length);

            var command = new UploadFrameCommand(
                imageData,
                cameraIndex,
                $"camera_{cameraIndex}_{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}.jpg");
            var enqueueResult = await _mediator.Send(command);

            if (!enqueueResult.Success)
            {
                return StatusCode(503, new
                {
                    error = "Service unavailable",
                    camera_id = cameraIndex,
                    message = "Frame queue is full"
                });
            }

            return Ok(new
            {
                success = true,
                camera_id = cameraIndex,
                message = enqueueResult.Message,
                queue_size = enqueueResult.QueueSize,
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "❌ Error processing RAW frame from camera {CameraId}", cameraId);
            return StatusCode(500, new
            {
                error = "Internal server error",
                camera_id = cameraId,
                message = ex.Message
            });
        }
    }

    [HttpGet("queue/status")]
    public async Task<IActionResult> GetQueueStatus()
    {
        try
        {
            var status = await _mediator.Send(new GetQueueStatusQuery());
            
            return Ok(new {
                service = "frame-queue",
                queue_size = status.QueueSize,
                camera_counters = status.CameraCounters,
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get queue status");
            return StatusCode(500, new { error = "Failed to get queue status" });
        }
    }

    [HttpGet("image/{imageHash}")]
    public IActionResult GetFrameImage(string imageHash)
    {
        if (string.IsNullOrWhiteSpace(imageHash) || imageHash.Length != 64 || !IsHex(imageHash))
        {
            return BadRequest(new { error = "Invalid image hash" });
        }

        var normalized = imageHash.ToLowerInvariant();
        var baseDir = Path.Combine(AppContext.BaseDirectory, "fall-snapshots");
        var filePath = Path.Combine(baseDir, $"{normalized}.jpg");
        if (!System.IO.File.Exists(filePath))
        {
            return NotFound(new { error = "Image not found" });
        }

        return PhysicalFile(filePath, "image/jpeg");
    }

    private static bool IsHex(string value) => value.All(Uri.IsHexDigit);
}