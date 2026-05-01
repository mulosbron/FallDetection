namespace FallDetectionAPI.Data;

public record HealthSnapshot(
    string Service,
    string Status,
    DateTime Timestamp,
    string Environment,
    long UptimeSeconds,
    long MemoryMb);
