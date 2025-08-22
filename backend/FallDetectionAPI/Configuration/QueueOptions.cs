namespace FallDetectionAPI.Configuration;

public class QueueOptions
{
    public const string SectionName = "Queue";
    
    public int Capacity { get; set; } = 200;
    public int FlushIntervalMs { get; set; } = 1000;
    public int MaxBatchSize { get; set; } = 10;
}
