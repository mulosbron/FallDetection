namespace FallDetectionAPI.Integration.Configuration;

public class AiServiceOptions
{
    public const string SectionName = "AiService";
    public string BaseUrl { get; set; } = "http://ai-service:8000";
}
