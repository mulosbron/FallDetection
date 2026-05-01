namespace FallDetectionAPI.SignalR.Models;

public sealed class CameraUpdateEvent
{
    public string CameraId { get; set; } = string.Empty;
    public string CameraName { get; set; } = string.Empty;
    public string Timestamp { get; set; } = string.Empty;
    public string Result { get; set; } = string.Empty;
    public int YesCount { get; set; }
    public int TotalCount { get; set; }
    public int Threshold { get; set; }
}

public sealed class FallDetectedEvent
{
    public string CameraId { get; set; } = string.Empty;
    public string CameraName { get; set; } = string.Empty;
    public string Timestamp { get; set; } = string.Empty;
    public double Confidence { get; set; }
    public string Message { get; set; } = string.Empty;
    public int YesCount { get; set; }
    public int TotalCount { get; set; }
}
