using Microsoft.AspNetCore.Mvc;
using FallDetectionAPI.Application.Features.Results;
using FallDetectionAPI.Data;
using MediatR;

namespace FallDetectionAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ResultsController : ControllerBase
{
    private readonly IMediator _mediator;
    private readonly ILogger<ResultsController> _logger;

    public ResultsController(
        IMediator mediator,
        ILogger<ResultsController> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    [HttpGet("statistics/ai-service")]
    public async Task<IActionResult> GetAiServiceStatistics()
    {
        try
        {
            _logger.LogInformation("📊 Fetching statistics from AI service");
            
            var statistics = await _mediator.Send(new GetAiStatisticsQuery());
            
            _logger.LogInformation("✅ Statistics retrieved successfully: {TotalProcessed} total, {FallDetected} falls, {NoFall} no falls", 
                statistics.TotalProcessed, statistics.FallDetected, statistics.NoFall);
            
            return Ok(new {
                source = "AI Service Database",
                timestamp = DateTime.UtcNow,
                statistics = statistics
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "❌ Failed to retrieve statistics from AI service");
            return StatusCode(503, new { 
                error = "Failed to retrieve statistics", 
                details = "AI service unavailable or statistics endpoint failed",
                timestamp = DateTime.UtcNow
            });
        }
    }

    [HttpGet("result/{imageHash}")]
    public async Task<IActionResult> GetResult(string imageHash)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(imageHash) || imageHash.Length < 8)
            {
                return BadRequest(new { error = "Invalid image hash format" });
            }

            _logger.LogInformation("🔍 Querying result for image hash: {ImageHash}", imageHash);
            
            var result = await _mediator.Send(new GetResultByHashQuery(imageHash));
            
            if (result == null)
            {
                _logger.LogWarning("⚠️ No result found for image hash: {ImageHash}", imageHash);
                return NotFound(new { 
                    error = "Result not found", 
                    imageHash = imageHash,
                    timestamp = DateTime.UtcNow
                });
            }
            
            _logger.LogInformation("✅ Result found for image hash {ImageHash}: {Result}", 
                imageHash, result.Result);
            
            return Ok(new {
                source = "AI Service Database",
                timestamp = DateTime.UtcNow,
                result = result
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "❌ Failed to retrieve result for image hash: {ImageHash}", imageHash);
            return StatusCode(503, new { 
                error = "Failed to retrieve result", 
                details = "AI service unavailable or result query failed",
                imageHash = imageHash,
                timestamp = DateTime.UtcNow
            });
        }
    }

    [HttpGet("hashes")]
    public async Task<IActionResult> GetAllHashes()
    {
        try
        {
            _logger.LogInformation("🔍 Fetching all image hashes from database");
            
            var hashes = await _mediator.Send(new GetAllHashesQuery());
            
            _logger.LogInformation("✅ Retrieved {Count} image hashes from database", hashes.Count);
            
            return Ok(new {
                source = ".NET API Database",
                timestamp = DateTime.UtcNow,
                total_hashes = hashes.Count,
                hashes = hashes
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "❌ Failed to retrieve image hashes from database");
            return StatusCode(500, new { 
                error = "Failed to retrieve image hashes", 
                details = ex.Message,
                timestamp = DateTime.UtcNow
            });
        }
    }

    [HttpGet("health/ai-service")]
    public async Task<IActionResult> GetAiServiceHealth()
    {
        try
        {
            _logger.LogInformation("🏥 Checking AI service health");
            
            var health = await _mediator.Send(new GetAiHealthQuery());
            
            _logger.LogInformation("✅ AI service health check completed: {Status}", health.Status);
            
            return Ok(new {
                source = "AI Service Health Check",
                timestamp = DateTime.UtcNow,
                health = new {
                    status = health.Status,
                    model_loaded = health.ModelLoaded,
                    database_connected = health.DatabaseConnected,
                    gpu_available = health.GpuAvailable
                }
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "❌ AI service health check failed");
            return StatusCode(503, new { 
                error = "AI service health check failed", 
                details = "Service unavailable or health endpoint failed",
                timestamp = DateTime.UtcNow
            });
        }
    }

    [HttpGet("incidents")]
    public async Task<IActionResult> GetAllIncidents([FromQuery] int? page = 1, [FromQuery] int? pageSize = 10, [FromQuery] string? status = null, [FromQuery] string? type = null)
    {
        try
        {
            _logger.LogInformation("📋 Fetching incidents from database - Page: {Page}, Size: {PageSize}, Status: {Status}, Type: {Type}", 
                page, pageSize, status, type);

            var data = await _mediator.Send(
                new GetIncidentsQuery(page ?? 1, pageSize ?? 10, status, type));

            var response = new
            {
                incidents = data.Incidents,
                pagination = new
                {
                    page = data.Page,
                    pageSize = data.PageSize,
                    totalCount = data.TotalCount,
                    totalPages = (int)Math.Ceiling((double)data.TotalCount / data.PageSize)
                },
                summary = new
                {
                    total = data.TotalCount,
                    newIncidents = data.NewIncidents,
                    investigating = 0,
                    resolved = data.ResolvedIncidents
                },
                source = ".NET API Database",
                timestamp = DateTime.UtcNow
            };

            _logger.LogInformation("✅ Retrieved {Count} incidents from database (Total: {Total})",
                data.Incidents.Count, data.TotalCount);

            return Ok(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "❌ Failed to retrieve incidents from database");
            return StatusCode(500, new
            {
                error = "Failed to retrieve incidents",
                details = ex.Message,
                timestamp = DateTime.UtcNow
            });
        }
    }

    [HttpGet("health/net-api")]
    public async Task<IActionResult> GetNetApiHealth()
    {
        try
        {
            _logger.LogInformation("🏥 .NET API health check requested");
            var healthStatus = await _mediator.Send(new GetNetApiHealthQuery());
            var snapshot = new HealthSnapshot(
                healthStatus.Service,
                healthStatus.Status,
                DateTime.UtcNow,
                healthStatus.Environment,
                healthStatus.UptimeSeconds,
                healthStatus.MemoryMb);
            
            _logger.LogInformation("✅ .NET API health check completed successfully");
            
            return Ok(new {
                source = ".NET API Health Check",
                timestamp = DateTime.UtcNow,
                health = snapshot
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "❌ .NET API health check failed");
            return StatusCode(500, new { 
                error = ".NET API health check failed", 
                details = ex.Message,
                timestamp = DateTime.UtcNow
            });
        }
    }
}
