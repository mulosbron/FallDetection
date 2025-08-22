using System.Text.Json.Serialization;

namespace FallDetectionAPI.Models;

public class AiStatistics
{
    [JsonPropertyName("total_processed")]
    public int TotalProcessed { get; set; }
    
    [JsonPropertyName("fall_detected")]
    public int FallDetected { get; set; }
    
    [JsonPropertyName("no_fall")]
    public int NoFall { get; set; }
    
    [JsonPropertyName("avg_processing_time_ms")]
    public double AvgProcessingTimeMs { get; set; }
    
    [JsonPropertyName("days_active")]
    public int DaysActive { get; set; }
}
