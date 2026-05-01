using FallDetectionAPI.Application.Abstractions;

namespace FallDetectionAPI.Services;

public class CameraAlertService : ICameraAlertService
{
    private readonly IRealtimeNotifier _realtimeNotifier;
    private readonly Dictionary<int, int> _cameraYesCounts = new();
    private readonly Dictionary<int, int> _cameraTotalCounts = new();
    private readonly object _lockObject = new();
    private const int AlertThreshold = 1;

    public CameraAlertService(IRealtimeNotifier realtimeNotifier)
    {
        _realtimeNotifier = realtimeNotifier;
    }

    public async Task UpdateCameraCountersAsync(int cameraIndex, string result)
    {
        var yesCount = 0;
        var totalCount = 0;
        var isFall = false;

        lock (_lockObject)
        {
            if (!_cameraYesCounts.ContainsKey(cameraIndex))
            {
                _cameraYesCounts[cameraIndex] = 0;
                _cameraTotalCounts[cameraIndex] = 0;
            }

            _cameraTotalCounts[cameraIndex]++;
            isFall = result.Equals("Yes", StringComparison.OrdinalIgnoreCase);
            if (isFall)
            {
                _cameraYesCounts[cameraIndex]++;
            }

            yesCount = _cameraYesCounts[cameraIndex];
            totalCount = _cameraTotalCounts[cameraIndex];

        }

        var cameraId = $"cam-{cameraIndex:D3}";
        var cameraUpdate = new
        {
            cameraId,
            cameraName = $"Camera {cameraIndex}",
            timestamp = DateTime.UtcNow.ToString("o"),
            result,
            yesCount,
            totalCount,
            threshold = AlertThreshold
        };

        await _realtimeNotifier.PublishCameraUpdateAsync(cameraUpdate);

        if (isFall && yesCount >= AlertThreshold)
        {
            var fallEvent = new
            {
                cameraId,
                cameraName = $"Camera {cameraIndex}",
                timestamp = DateTime.UtcNow.ToString("o"),
                confidence = 0.95,
                message = $"Fall detected on camera {cameraIndex}",
                yesCount,
                totalCount
            };

            await _realtimeNotifier.PublishFallDetectedAsync(fallEvent);
        }
    }

    public IReadOnlyDictionary<int, (int YesCount, int TotalCount)> GetCameraCounters()
    {
        lock (_lockObject)
        {
            return _cameraYesCounts.ToDictionary(
                kvp => kvp.Key,
                kvp => (kvp.Value, _cameraTotalCounts.GetValueOrDefault(kvp.Key)));
        }
    }
}
