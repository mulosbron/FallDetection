namespace FallDetectionAPI.Domain.Entities;

public class FallDetectionRecord
{
    public int Id { get; set; }
    public string ImageHash { get; set; } = string.Empty;
    public string Result { get; set; } = string.Empty;
    public int CameraIndex { get; set; }
    public DateTime CreatedAt { get; set; }
    public string? ImageSize { get; set; }
    public int? ProcessingTimeMs { get; set; }
}
