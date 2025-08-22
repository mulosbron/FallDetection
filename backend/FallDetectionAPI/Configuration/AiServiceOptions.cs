namespace FallDetectionAPI.Configuration;

public class AiServiceOptions
{
    public const string SectionName = "AiService";
    
    public string BaseUrl { get; set; } = string.Empty;
}
