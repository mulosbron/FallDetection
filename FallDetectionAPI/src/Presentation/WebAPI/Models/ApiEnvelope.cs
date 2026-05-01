namespace FallDetectionAPI.Models;

public record ApiEnvelope<T>(T Data, DateTime Timestamp, string Source);
