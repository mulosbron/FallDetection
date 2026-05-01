namespace FallDetectionAPI.Integration.Configuration;

public class SignalRHostOptions
{
    public const string SectionName = "SignalRHost";
    public string BaseUrl { get; set; } = "http://fall_detection_signalr:8081";
}
