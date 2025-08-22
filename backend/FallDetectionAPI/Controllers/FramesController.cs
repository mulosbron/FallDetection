using Microsoft.AspNetCore.Mvc;
using FallDetectionAPI.Models;
using FallDetectionAPI.Services;

namespace FallDetectionAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class FramesController : ControllerBase
{
    private readonly IFrameQueue _frameQueue;
    private readonly ILogger<FramesController> _logger;

    public FramesController(IFrameQueue frameQueue, ILogger<FramesController> logger)
    {
        _frameQueue = frameQueue;
        _logger = logger;
    }

    [HttpPost]
    public async Task<IActionResult> UploadFrame([FromForm] IFormFile image, [FromForm] int? cameraId = null)
    {
        if (image == null || image.Length == 0)
        {
            return BadRequest(new { error = "Image file is required" });
        }

        // Dosya türü kontrolü
        var allowedTypes = new[] { "image/jpeg", "image/jpg", "image/png" };
        if (!allowedTypes.Contains(image.ContentType?.ToLower()))
        {
            return BadRequest(new { error = "Only JPEG and PNG images are allowed" });
        }

        // Dosya boyutu kontrolü (max 10MB)
        if (image.Length > 10 * 1024 * 1024)
        {
            return BadRequest(new { error = "Image file is too large (max 10MB)" });
        }

        try
        {
            // Dosyayı RAM'e kopyala
            using var memoryStream = new MemoryStream();
            await image.CopyToAsync(memoryStream);
            var imageBytes = memoryStream.ToArray();

            // FrameJob oluştur  
            var frameJob = new FrameJob(
                Id: Guid.NewGuid(),
                ImageBytes: imageBytes,
                EnqueuedAt: DateTime.UtcNow
            );

            // Kuyruğa ekle
            if (!_frameQueue.TryEnqueue(frameJob))
            {
                _logger.LogWarning("Queue is full, rejecting frame upload. Queue count: {Count}", _frameQueue.Count);
                return StatusCode(429, new { error = "Queue is full, please try again later" });
            }

            _logger.LogDebug("Frame {JobId} uploaded and queued successfully from camera {CameraId}", 
                frameJob.Id, cameraId);

            return Accepted(new { 
                jobId = frameJob.Id,
                enqueuedAt = frameJob.EnqueuedAt,
                queueCount = _frameQueue.Count
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing frame upload");
            return StatusCode(500, new { error = "Internal server error while processing frame" });
        }
    }

    [HttpGet("{jobId}")]
    public IActionResult GetFrameStatus(Guid jobId)
    {
        // Bu örnekte basit bir status döndürüyoruz
        // Gerçek implementasyonda job durumunu takip edebilirsiniz
        return Ok(new { 
            jobId = jobId,
            status = "queued", // queued, processing, completed, error
            message = "Frame is in processing queue"
        });
    }

    [HttpGet("queue/status")]
    public IActionResult GetQueueStatus()
    {
        return Ok(new {
            queueCount = _frameQueue.Count,
            timestamp = DateTime.UtcNow
        });
    }
}
