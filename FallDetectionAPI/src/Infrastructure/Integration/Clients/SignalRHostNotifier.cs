using System.Net.Http.Json;
using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Integration.Configuration;
using Microsoft.Extensions.Options;

namespace FallDetectionAPI.Integration.Clients;

public class SignalRHostNotifier : IRealtimeNotifier
{
    private readonly HttpClient _httpClient;

    public SignalRHostNotifier(HttpClient httpClient, IOptions<SignalRHostOptions> options)
    {
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri(options.Value.BaseUrl);
        _httpClient.Timeout = TimeSpan.FromSeconds(10);
    }

    public async Task PublishCameraUpdateAsync(object payload, CancellationToken cancellationToken = default)
    {
        using var response = await _httpClient.PostAsJsonAsync("/internal/notify/camera-update", payload, cancellationToken);
        response.EnsureSuccessStatusCode();
    }

    public async Task PublishFallDetectedAsync(object payload, CancellationToken cancellationToken = default)
    {
        using var response = await _httpClient.PostAsJsonAsync("/internal/notify/fall-detected", payload, cancellationToken);
        response.EnsureSuccessStatusCode();
    }
}
