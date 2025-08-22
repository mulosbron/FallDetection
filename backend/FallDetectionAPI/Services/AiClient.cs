using FallDetectionAPI.Models;
using FallDetectionAPI.Configuration;
using Microsoft.Extensions.Options;
using System.Text.Json;

namespace FallDetectionAPI.Services;

public class AiClient : IAiClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<AiClient> _logger;
    private readonly AiServiceOptions _options;

    public AiClient(HttpClient httpClient, IOptions<AiServiceOptions> options, ILogger<AiClient> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        _options = options.Value;
        
        _httpClient.BaseAddress = new Uri(_options.BaseUrl);
        _httpClient.Timeout = TimeSpan.FromSeconds(30);
        
        _logger.LogInformation("AiClient initialized with BaseUrl: {BaseUrl}", _options.BaseUrl);
    }

    public async Task<AiResult> DetectFallAsync(byte[] imageBytes, CancellationToken cancellationToken = default)
    {
        try
        {
            using var content = new MultipartFormDataContent();
            var stream = new MemoryStream(imageBytes);
            var imageContent = new StreamContent(stream);
            imageContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg");
            content.Add(imageContent, "file", "frame.jpg");

            var response = await _httpClient.PostAsync("/detect-fall/", content, cancellationToken);
            response.EnsureSuccessStatusCode();

            var jsonResponse = await response.Content.ReadAsStringAsync(cancellationToken);
            var result = JsonSerializer.Deserialize<AiResult>(jsonResponse);

            _logger.LogDebug("Single fall detection completed. Result: {Result}, Confidence: {Confidence}", 
                result?.Result, result?.Confidence);

            return result ?? throw new InvalidOperationException("Failed to deserialize AI response");
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "HTTP error during fall detection");
            throw;
        }
        catch (TaskCanceledException ex)
        {
            _logger.LogError(ex, "Request timeout during fall detection");
            throw;
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "JSON parsing error during fall detection");
            throw;
        }
    }

    public async Task<AiBatchResult> DetectFallBatchAsync(IEnumerable<byte[]> imageBytesList, CancellationToken cancellationToken = default)
    {
        try
        {
            using var content = new MultipartFormDataContent();
            var imageList = imageBytesList.ToList();
            
            if (imageList.Count > 10)
            {
                throw new ArgumentException("Maximum 10 images allowed per batch", nameof(imageBytesList));
            }

            for (int i = 0; i < imageList.Count; i++)
            {
                var stream = new MemoryStream(imageList[i]);
                var imageContent = new StreamContent(stream);
                imageContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg");
                // Her file için aynı "files" key kullan (multiple files with same key)
                content.Add(imageContent, "files", $"frame_{i}.jpg");
            }

            _logger.LogInformation("🚀 SENDING BATCH OF {Count} IMAGES TO AI SERVICE", imageList.Count);

            var response = await _httpClient.PostAsync("/detect-fall-batch/", content, cancellationToken);
            response.EnsureSuccessStatusCode();

            var jsonResponse = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogInformation("📥 AI SERVICE RAW RESPONSE: {Response}", jsonResponse);
            
            var result = JsonSerializer.Deserialize<AiBatchResult>(jsonResponse);
            _logger.LogInformation("✅ AI SERVICE PARSED {Count} RESULTS", result?.Results?.Count ?? 0);

            _logger.LogDebug("Batch fall detection completed. Processed {Count} images", result?.Results?.Count ?? 0);

            return result ?? throw new InvalidOperationException("Failed to deserialize AI batch response");
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "HTTP error during batch fall detection");
            throw;
        }
        catch (TaskCanceledException ex)
        {
            _logger.LogError(ex, "Request timeout during batch fall detection");
            throw;
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "JSON parsing error during batch fall detection");
            throw;
        }
    }

    public async Task<bool> HealthCheckAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await _httpClient.GetAsync("/health", cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "AI service health check failed");
            return false;
        }
    }

    public async Task<AiStatistics> GetStatisticsAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await _httpClient.GetAsync("/statistics", cancellationToken);
            response.EnsureSuccessStatusCode();

            var jsonResponse = await response.Content.ReadAsStringAsync(cancellationToken);
            var statistics = JsonSerializer.Deserialize<AiStatistics>(jsonResponse);

            _logger.LogDebug("Statistics retrieved successfully: {TotalProcessed} total processed", 
                statistics?.TotalProcessed);

            return statistics ?? throw new InvalidOperationException("Failed to deserialize statistics response");
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "HTTP error during statistics retrieval");
            throw;
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "JSON parsing error during statistics retrieval");
            throw;
        }
    }

    public async Task<AiResult?> GetResultAsync(string imageHash, CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await _httpClient.GetAsync($"/result/{imageHash}", cancellationToken);
            
            if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                return null;
            }
            
            response.EnsureSuccessStatusCode();

            var jsonResponse = await response.Content.ReadAsStringAsync(cancellationToken);
            var result = JsonSerializer.Deserialize<AiResult>(jsonResponse);

            _logger.LogDebug("Result retrieved for hash {ImageHash}: {Result}", 
                imageHash, result?.Result);

            return result;
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "HTTP error during result retrieval for hash: {ImageHash}", imageHash);
            throw;
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "JSON parsing error during result retrieval for hash: {ImageHash}", imageHash);
            throw;
        }
    }

    public async Task<AiHealth> GetHealthAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await _httpClient.GetAsync("/health", cancellationToken);
            response.EnsureSuccessStatusCode();

            var jsonResponse = await response.Content.ReadAsStringAsync(cancellationToken);
            var health = JsonSerializer.Deserialize<AiHealth>(jsonResponse);

            _logger.LogDebug("Health check completed: {Status}", health?.Status);

            return health ?? throw new InvalidOperationException("Failed to deserialize health response");
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "HTTP error during health check");
            throw;
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "JSON parsing error during health check");
            throw;
        }
    }
}
