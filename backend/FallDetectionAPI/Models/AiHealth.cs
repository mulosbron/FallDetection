using System.Text.Json.Serialization;

namespace FallDetectionAPI.Models;

public class AiHealth
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;
    
    [JsonPropertyName("model_loaded")]
    public bool ModelLoaded { get; set; }
    
    [JsonPropertyName("database_connected")]
    public bool DatabaseConnected { get; set; }
    
    [JsonPropertyName("gpu_available")]
    public bool GpuAvailable { get; set; }
    
    [JsonPropertyName("statistics")]
    public AiStatistics? Statistics { get; set; }
}
