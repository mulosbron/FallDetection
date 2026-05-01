using System.Text.Json;
using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Application.Models;
using FallDetectionAPI.Integration.Configuration;
using Microsoft.Extensions.Options;

namespace FallDetectionAPI.Integration.Clients;

public class MockCameraGateway : IMockCameraGateway
{
    private readonly HttpClient _httpClient;
    private readonly MockCameraOptions _options;

    public MockCameraGateway(HttpClient httpClient, IOptions<MockCameraOptions> options)
    {
        _options = options.Value;
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri(_options.BaseUrl);
        _httpClient.Timeout = TimeSpan.FromSeconds(15);
    }

    public Task<bool> StartSimulationAsync(CancellationToken cancellationToken = default) =>
        PostAsBooleanAsync("/simulation/start", cancellationToken);

    public Task<bool> StopSimulationAsync(CancellationToken cancellationToken = default) =>
        PostAsBooleanAsync("/simulation/stop", cancellationToken);

    public Task<JsonElement> GetCameraStatusAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync("/cameras/status", cancellationToken);

    public Task<JsonElement> GetCameraVideosAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync("/cameras/videos", cancellationToken);

    public Task<JsonElement> GetSimulationStatusAsync(CancellationToken cancellationToken = default) =>
        GetJsonAsync("/simulation/status", cancellationToken);

    public async Task<IReadOnlyList<CameraStreamDto>> GetCameraInventoryAsync(CancellationToken cancellationToken = default)
    {
        var cameras = new List<CameraStreamDto>();
        var probeBase = _options.HlsBaseUrl.TrimEnd('/');
        var clientBase = string.IsNullOrWhiteSpace(_options.HlsPublicBaseUrl)
            ? probeBase
            : _options.HlsPublicBaseUrl.TrimEnd('/');
        var normalizedPrefix = NormalizeStreamPathPrefix(_options.StreamPathPrefix);
        var maxProbe = _options.MaxCameraProbe > 0 ? Math.Clamp(_options.MaxCameraProbe, 1, 256) : 256;
        var minProbe = Math.Clamp(_options.MinCameraProbe, 1, maxProbe);
        var consecutiveMissStopThreshold = Math.Clamp(_options.ConsecutiveMissStopThreshold, 1, 16);
        var consecutiveMiss = 0;

        for (var cameraIndex = 1; cameraIndex <= maxProbe; cameraIndex++)
        {
            var cameraId = $"cam-{cameraIndex:D3}";
            var hlsPath = $"{normalizedPrefix}/camera{cameraIndex}/index.m3u8";
            var probeUrl = $"{probeBase}{hlsPath}";
            var isActive = await IsHlsReachableAsync(probeUrl, cancellationToken);
            var hlsUrlForClient = $"{clientBase}{hlsPath}";

            if (isActive)
            {
                consecutiveMiss = 0;
                cameras.Add(new CameraStreamDto
                {
                    CameraIndex = cameraIndex,
                    CameraId = cameraId,
                    CameraName = $"Camera {cameraIndex}",
                    HlsUrl = hlsUrlForClient,
                    IsActive = true
                });
                continue;
            }

            consecutiveMiss++;
            if (cameraIndex >= minProbe && consecutiveMiss >= consecutiveMissStopThreshold && cameras.Count > 0)
            {
                break;
            }
        }

        return cameras;
    }

    private async Task<bool> PostAsBooleanAsync(string path, CancellationToken cancellationToken)
    {
        var response = await _httpClient.PostAsync(path, null, cancellationToken);
        return response.IsSuccessStatusCode;
    }

    private async Task<JsonElement> GetJsonAsync(string path, CancellationToken cancellationToken)
    {
        var response = await _httpClient.GetAsync(path, cancellationToken);
        response.EnsureSuccessStatusCode();
        using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(cancellationToken));
        return doc.RootElement.Clone();
    }

    private static string NormalizeStreamPathPrefix(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "/live";
        }

        var prefixed = value.StartsWith('/') ? value : $"/{value}";
        return prefixed.TrimEnd('/');
    }

    private async Task<bool> IsHlsReachableAsync(string hlsUrl, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Head, hlsUrl);
        using var response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);

        if (response.IsSuccessStatusCode)
        {
            return true;
        }

        // Some proxy/serving layers do not support HEAD; fallback to GET.
        if (response.StatusCode is System.Net.HttpStatusCode.MethodNotAllowed or System.Net.HttpStatusCode.NotFound)
        {
            using var getResponse = await _httpClient.GetAsync(hlsUrl, cancellationToken);
            return getResponse.IsSuccessStatusCode;
        }

        return false;
    }
}
