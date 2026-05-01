using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Threading.Channels;
using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Application.Models;
using FallDetectionAPI.Domain.Entities;
using FallDetectionAPI.Integration.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace FallDetectionAPI.Integration.Services;

public class FrameQueueService : BackgroundService, IFrameQueueService
{
    private sealed class QueuedFrame
    {
        public required byte[] ImageData { get; init; }
        public required int CameraIndex { get; init; }
        public required string FileName { get; init; }
    }

    private readonly IAiGateway _aiGateway;
    private readonly ICameraAlertService _cameraAlertService;
    private readonly QueueOptions _options;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<FrameQueueService> _logger;
    private readonly Channel<QueuedFrame> _frameChannel;
    private readonly ConcurrentDictionary<int, int> _cameraCounters = new();
    private readonly List<QueuedFrame> _batchBuffer = [];
    private readonly object _bufferLock = new();

    public FrameQueueService(
        IAiGateway aiGateway,
        ICameraAlertService cameraAlertService,
        IOptions<QueueOptions> options,
        IServiceScopeFactory scopeFactory,
        ILogger<FrameQueueService> logger)
    {
        _aiGateway = aiGateway;
        _cameraAlertService = cameraAlertService;
        _options = options.Value;
        _scopeFactory = scopeFactory;
        _logger = logger;
        _frameChannel = Channel.CreateBounded<QueuedFrame>(new BoundedChannelOptions(_options.Capacity)
        {
            FullMode = BoundedChannelFullMode.Wait
        });
    }

    public async Task<bool> EnqueueFrameAsync(byte[] imageData, int cameraIndex, string fileName, CancellationToken cancellationToken = default)
    {
        var frame = new QueuedFrame
        {
            ImageData = imageData,
            CameraIndex = cameraIndex,
            FileName = fileName
        };

        var canWrite = await _frameChannel.Writer.WaitToWriteAsync(cancellationToken);
        if (!canWrite)
        {
            return false;
        }

        await _frameChannel.Writer.WriteAsync(frame, cancellationToken);
        return true;
    }

    public QueueStatusDto GetQueueStatus() =>
        new()
        {
            QueueSize = _frameChannel.Reader.Count,
            CameraCounters = new Dictionary<int, int>(_cameraCounters)
        };

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            while (_frameChannel.Reader.TryRead(out var frame))
            {
                lock (_bufferLock)
                {
                    _batchBuffer.Add(frame);
                }

                _cameraCounters.AddOrUpdate(frame.CameraIndex, 1, (_, current) => current + 1);
            }

            await FlushBatchAsync(stoppingToken);
            await Task.Delay(_options.FlushIntervalMs, stoppingToken);
        }
    }

    private async Task FlushBatchAsync(CancellationToken cancellationToken)
    {
        List<QueuedFrame> current;
        lock (_bufferLock)
        {
            if (_batchBuffer.Count == 0)
            {
                return;
            }

            current = [.. _batchBuffer];
            _batchBuffer.Clear();
        }

        if (current.Count == 1)
        {
            var only = current[0];
            await ProcessFrameAsync(only, cancellationToken);
            return;
        }

        var chunks = current
            .Chunk(_options.MaxBatchSize)
            .Select(c => c.ToList());

        foreach (var chunk in chunks)
        {
            foreach (var frame in chunk)
            {
                await ProcessFrameAsync(frame, cancellationToken);
            }
        }
    }

    private async Task ProcessFrameAsync(QueuedFrame frame, CancellationToken cancellationToken)
    {
        try
        {
            var result = await _aiGateway.DetectFallAsync(frame.ImageData, frame.CameraIndex, cancellationToken);
            var imageHash = ComputeImageHash(frame.ImageData, frame.CameraIndex);

            await _cameraAlertService.UpdateCameraCountersAsync(frame.CameraIndex, result.Result);

            try
            {
                await SaveDetectionRecordAsync(frame, result, imageHash, cancellationToken);
                await PersistFallSnapshotIfNeededAsync(frame, result, imageHash, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Persistence failed for camera {CameraIndex}", frame.CameraIndex);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Frame processing failed for camera {CameraIndex}", frame.CameraIndex);
        }
    }

    private async Task SaveDetectionRecordAsync(QueuedFrame frame, AiResultDto result, string imageHash, CancellationToken cancellationToken)
    {
        using var scope = _scopeFactory.CreateScope();
        var repository = scope.ServiceProvider.GetRequiredService<IFallDetectionRepository>();
        var record = new FallDetectionRecord
        {
            ImageHash = imageHash,
            Result = result.Result,
            CameraIndex = frame.CameraIndex,
            CreatedAt = DateTime.SpecifyKind(DateTime.UtcNow, DateTimeKind.Unspecified),
            ImageSize = frame.ImageData.Length.ToString(),
            ProcessingTimeMs = result.ProcessingTimeMs
        };
        await repository.AddAsync(record, cancellationToken);
    }

    private async Task PersistFallSnapshotIfNeededAsync(QueuedFrame frame, AiResultDto result, string imageHash, CancellationToken cancellationToken)
    {
        if (!result.Result.Equals("Yes", StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        var directory = Path.Combine(AppContext.BaseDirectory, "fall-snapshots");
        Directory.CreateDirectory(directory);
        var outputPath = Path.Combine(directory, $"{imageHash}.jpg");
        if (!File.Exists(outputPath))
        {
            await File.WriteAllBytesAsync(outputPath, frame.ImageData, cancellationToken);
        }
    }

    private static string ComputeImageHash(byte[] data, int cameraIndex)
    {
        var entropy = BitConverter.GetBytes(DateTime.UtcNow.Ticks)
            .Concat(BitConverter.GetBytes(cameraIndex))
            .ToArray();
        var material = new byte[data.Length + entropy.Length];
        Buffer.BlockCopy(data, 0, material, 0, data.Length);
        Buffer.BlockCopy(entropy, 0, material, data.Length, entropy.Length);
        var hash = SHA256.HashData(material);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}
