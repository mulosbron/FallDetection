namespace FallDetectionAPI.Application.Models;

public class AiResultDto
{
    public string ImageHash { get; set; } = string.Empty;
    public string Result { get; set; } = string.Empty;
    public string? ImageSize { get; set; }
    public int? ProcessingTimeMs { get; set; }
    public bool Cached { get; set; }
    public int CameraIndex { get; set; }
}

public class AiBatchResultDto
{
    public List<AiResultDto> Results { get; set; } = new();
}

public class AiStatisticsDto
{
    public int TotalProcessed { get; set; }
    public int FallDetected { get; set; }
    public int NoFall { get; set; }
    public double AvgProcessingTimeMs { get; set; }
    public int DaysActive { get; set; }
}

public class AiHealthDto
{
    public string Status { get; set; } = string.Empty;
    public bool ModelLoaded { get; set; }
    public bool DatabaseConnected { get; set; }
    public bool GpuAvailable { get; set; }
}

public class QueueStatusDto
{
    public int QueueSize { get; set; }
    public IReadOnlyDictionary<int, int> CameraCounters { get; set; } = new Dictionary<int, int>();
}

public class CameraStreamDto
{
    public int CameraIndex { get; set; }
    public string CameraId { get; set; } = string.Empty;
    public string CameraName { get; set; } = string.Empty;
    public string HlsUrl { get; set; } = string.Empty;
    public bool IsActive { get; set; }
}
