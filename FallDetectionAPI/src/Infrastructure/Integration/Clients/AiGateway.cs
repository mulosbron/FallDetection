using System.Text.Json;
using System.Text.Json.Serialization;
using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Application.Models;
using FallDetectionAPI.Integration.Configuration;
using Microsoft.Extensions.Options;

namespace FallDetectionAPI.Integration.Clients;

public class AiGateway : IAiGateway
{
    private readonly HttpClient _httpClient;

    public AiGateway(HttpClient httpClient, IOptions<AiServiceOptions> options)
    {
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri(options.Value.BaseUrl);
        _httpClient.Timeout = TimeSpan.FromSeconds(30);
    }

    public async Task<AiResultDto> DetectFallAsync(byte[] imageBytes, int cameraIndex, CancellationToken cancellationToken = default)
    {
        using var content = new MultipartFormDataContent();
        content.Add(new StreamContent(new MemoryStream(imageBytes)), "file", "frame.jpg");
        content.Add(new StringContent(cameraIndex.ToString()), "camera_index");

        var response = await _httpClient.PostAsync("/v1/inference/fall-detection", content, cancellationToken);
        response.EnsureSuccessStatusCode();
        var raw = await DeserializeAsync<AiInferenceRawResponse>(response, cancellationToken);

        return new AiResultDto
        {
            ImageHash = string.Empty,
            Result = NormalizeResult(raw.Result),
            ProcessingTimeMs = raw.LatencyMs,
            Cached = false,
            CameraIndex = cameraIndex
        };
    }

    public async Task<AiBatchResultDto> DetectFallBatchAsync(IEnumerable<byte[]> imageBytesList, int cameraIndex, CancellationToken cancellationToken = default)
    {
        var results = new List<AiResultDto>();
        foreach (var imageBytes in imageBytesList)
        {
            var result = await DetectFallAsync(imageBytes, cameraIndex, cancellationToken);
            results.Add(result);
        }

        return new AiBatchResultDto { Results = results };
    }

    public async Task<AiStatisticsDto> GetStatisticsAsync(CancellationToken cancellationToken = default)
    {
        // New ai-service version has no dedicated statistics endpoint; healthy fallback.
        await GetHealthAsync(cancellationToken);
        return new AiStatisticsDto();
    }

    public async Task<AiResultDto?> GetResultAsync(string imageHash, CancellationToken cancellationToken = default)
    {
        // New ai-service version has no result-by-hash endpoint.
        await Task.CompletedTask;
        return null;
    }

    public async Task<AiHealthDto> GetHealthAsync(CancellationToken cancellationToken = default)
    {
        var response = await _httpClient.GetAsync("/health", cancellationToken);
        response.EnsureSuccessStatusCode();

        var raw = await DeserializeAsync<AiHealthV2RawResponse>(response, cancellationToken);
        return new AiHealthDto
        {
            Status = raw.Status,
            ModelLoaded = raw.LlamaServerReady && raw.ModelExists && raw.MmprojExists,
            DatabaseConnected = true,
            GpuAvailable = false
        };
    }

    private static string NormalizeResult(string? value)
    {
        return value?.Equals("fall_detected", StringComparison.OrdinalIgnoreCase) == true ? "Yes" : "No";
    }

    private static async Task<T> DeserializeAsync<T>(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        var json = await response.Content.ReadAsStringAsync(cancellationToken);
        return JsonSerializer.Deserialize<T>(json)!;
    }

    private sealed class AiInferenceRawResponse
    {
        [JsonPropertyName("status")]
        public string? Status { get; set; }

        [JsonPropertyName("result")]
        public string? Result { get; set; }

        [JsonPropertyName("latency_ms")]
        public int? LatencyMs { get; set; }
    }

    private sealed class AiHealthV2RawResponse
    {
        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("llama_server_ready")]
        public bool LlamaServerReady { get; set; }

        [JsonPropertyName("model_exists")]
        public bool ModelExists { get; set; }

        [JsonPropertyName("mmproj_exists")]
        public bool MmprojExists { get; set; }
    }
}
