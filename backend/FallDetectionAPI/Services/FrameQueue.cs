using System.Threading.Channels;
using FallDetectionAPI.Models;
using FallDetectionAPI.Configuration;
using Microsoft.Extensions.Options;

namespace FallDetectionAPI.Services;

public class FrameQueue : IFrameQueue
{
    private readonly Channel<FrameJob> _channel;
    private readonly ILogger<FrameQueue> _logger;

    public FrameQueue(IOptions<QueueOptions> options, ILogger<FrameQueue> logger)
    {
        _logger = logger;
        var queueOptions = options.Value;
        
        var channelOptions = new BoundedChannelOptions(queueOptions.Capacity)
        {
            FullMode = BoundedChannelFullMode.DropOldest,
            SingleReader = true,
            SingleWriter = false
        };

        _channel = Channel.CreateBounded<FrameJob>(channelOptions);
        
        _logger.LogInformation("FrameQueue initialized with capacity: {Capacity}", queueOptions.Capacity);
    }

    public bool TryEnqueue(FrameJob job)
    {
        var success = _channel.Writer.TryWrite(job);
        
        if (success)
        {
            _logger.LogDebug("Frame job {JobId} enqueued successfully", job.Id);
        }
        else
        {
            _logger.LogWarning("Failed to enqueue frame job {JobId} - queue is full", job.Id);
        }
        
        return success;
    }

    public async ValueTask<FrameJob> DequeueAsync(CancellationToken cancellationToken)
    {
        try
        {
            var job = await _channel.Reader.ReadAsync(cancellationToken);
            _logger.LogDebug("Frame job {JobId} dequeued successfully", job.Id);
            return job;
        }
        catch (InvalidOperationException)
        {
            _logger.LogError("Channel was closed while reading");
            throw;
        }
    }

    public int Count => _channel.Reader.Count;
}
