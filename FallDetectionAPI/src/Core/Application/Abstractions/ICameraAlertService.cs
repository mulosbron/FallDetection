namespace FallDetectionAPI.Application.Abstractions;

public interface ICameraAlertService
{
    Task UpdateCameraCountersAsync(int cameraIndex, string result);
    IReadOnlyDictionary<int, (int YesCount, int TotalCount)> GetCameraCounters();
}
