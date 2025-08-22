using System.ComponentModel.DataAnnotations.Schema;
using System.Text.Json.Serialization;

namespace FallDetectionAPI.Models;

public class FallDetection
{
    public int Id { get; set; }
    
    [Column("image_hash")]
    [JsonPropertyName("image_hash")]
    public string ImageHash { get; set; } = string.Empty;
    
    [JsonPropertyName("result")]
    public string Result { get; set; } = string.Empty;
    
    [JsonPropertyName("confidence")]
    public double? Confidence { get; set; }
    
    [Column("created_at")]
    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; }
    
    [Column("image_size")]
    [JsonPropertyName("image_size")]
    public string? ImageSize { get; set; }
    
    [Column("processing_time_ms")]
    [JsonPropertyName("processing_time_ms")]
    public int? ProcessingTimeMs { get; set; }
}
