using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using FallDetectionAPI.Services;
using FallDetectionAPI.Data;
using FallDetectionAPI.Models;
using System.Text.Json;

namespace FallDetectionAPI.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ResultsController : ControllerBase
{
    private readonly IAiClient _aiClient;
    private readonly AppDbContext _dbContext;
    private readonly ILogger<ResultsController> _logger;

    public ResultsController(
        IAiClient aiClient,
        AppDbContext dbContext,
        ILogger<ResultsController> logger)
    {
        _aiClient = aiClient;
        _dbContext = dbContext;
        _logger = logger;
    }

    [HttpGet("statistics/ai-service")]
    public async Task<IActionResult> GetAiServiceStatistics()
    {
        try
        {
            _logger.LogInformation("📊 Fetching statistics from AI service");
            
            var statistics = await _aiClient.GetStatisticsAsync();
            
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
            
            var result = await _aiClient.GetResultAsync(imageHash);
            
            if (result == null)
            {
                _logger.LogWarning("⚠️ No result found for image hash: {ImageHash}", imageHash);
                return NotFound(new { 
                    error = "Result not found", 
                    imageHash = imageHash,
                    timestamp = DateTime.UtcNow
                });
            }
            
            _logger.LogInformation("✅ Result found for image hash {ImageHash}: {Result} (confidence: {Confidence})", 
                imageHash, result.Result, result.Confidence);
            
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
            
            var hashes = await _dbContext.FallDetections
                .Select(fd => fd.ImageHash)
                .ToListAsync();
            
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
            
            var health = await _aiClient.GetHealthAsync();
            
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

    [HttpGet("health/net-api")]
    public IActionResult GetNetApiHealth()
    {
        try
        {
            _logger.LogInformation("🏥 .NET API health check requested");
            
            var healthStatus = new {
                status = "healthy",
                service = ".NET Fall Detection API",
                version = "1.0.0",
                timestamp = DateTime.UtcNow,
                environment = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Production",
                uptime = Environment.TickCount64 / 1000,
                memory = GC.GetTotalMemory(false) / 1024 / 1024
            };
            
            _logger.LogInformation("✅ .NET API health check completed successfully");
            
            return Ok(new {
                source = ".NET API Health Check",
                timestamp = DateTime.UtcNow,
                health = healthStatus
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
