using System.Text.Json.Serialization;

namespace FallDetectionAPI.Models;

public class AiResult
{
    [JsonPropertyName("image_hash")]
    public string ImageHash { get; set; } = string.Empty;
    
    [JsonPropertyName("result")]
    public string Result { get; set; } = string.Empty;
    
    [JsonPropertyName("confidence")]
    public double? Confidence { get; set; }
    
    [JsonPropertyName("image_size")]
    public string? ImageSize { get; set; }
    
    [JsonPropertyName("processing_time_ms")]
    public int? ProcessingTimeMs { get; set; }
    
    [JsonPropertyName("cached")]
    public bool Cached { get; set; }
}
