using FallDetectionAPI.Data;
using FallDetectionAPI.Models;
using FallDetectionAPI.Configuration;
using Microsoft.Extensions.Options;
using Microsoft.EntityFrameworkCore;

namespace FallDetectionAPI.Services;

public class FrameProcessor : BackgroundService
{
    private readonly IFrameQueue _frameQueue;
    private readonly IAiClient _aiClient;
    private readonly IServiceProvider _serviceProvider;
    private readonly ILogger<FrameProcessor> _logger;
    private readonly QueueOptions _queueOptions;

    public FrameProcessor(
        IFrameQueue frameQueue,
        IAiClient aiClient,
        IServiceProvider serviceProvider,
        IOptions<QueueOptions> queueOptions,
        ILogger<FrameProcessor> logger)
    {
        _frameQueue = frameQueue;
        _aiClient = aiClient;
        _serviceProvider = serviceProvider;
        _logger = logger;
        _queueOptions = queueOptions.Value;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("🔥 FrameProcessor is starting...");

        while (!stoppingToken.IsCancellationRequested)
        {
            _logger.LogDebug("📌 ENTERED MAIN LOOP ITERATION");

            try
            {
                await ProcessBatch(stoppingToken);
                _logger.LogDebug("📌 COMPLETED BATCH PROCESSING");
                
                // Sonraki batch için bekle (eğer batch boşsa daha kısa bekle)
                await Task.Delay(50, stoppingToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "❌ Error in FrameProcessor loop");
                
                // Hata durumunda kısa süre bekle
                await Task.Delay(1000, stoppingToken);
            }
        }
        
        _logger.LogInformation("🛑 FrameProcessor is stopping...");
    }

    private async Task ProcessBatch(CancellationToken cancellationToken)
    {
        _logger.LogInformation("📌 ENTERED ProcessBatch - Attempting to collect batch");

        var frameJobs = new List<FrameJob>();
        var timeout = TimeSpan.FromMilliseconds(100); // Kısa timeout ile batch topla
        
        // En fazla MaxBatchSize kadar frame topla
        for (int i = 0; i < _queueOptions.MaxBatchSize; i++)
        {
            _logger.LogDebug("📌 DEQUEUE ATTEMPT {Attempt}/{Max}", i+1, _queueOptions.MaxBatchSize);
            
            try
            {
                using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                timeoutCts.CancelAfter(timeout);
                
                var frameJob = await _frameQueue.DequeueAsync(timeoutCts.Token);
                frameJobs.Add(frameJob);
                _logger.LogInformation("✅ DEQUEUED FRAME {Id} SUCCESSFULLY", frameJob.Id);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                _logger.LogWarning("❌ PROCESS BATCH CANCELLED BY MAIN TOKEN");
                throw; // Ana cancellation token iptal edilmişse yukarı fırlat
            }
            catch (OperationCanceledException)
            {
                _logger.LogDebug("⏳ TIMEOUT - No more frames, breaking with {Count} frames", frameJobs.Count);
                // Timeout - başka frame yok, mevcut batch'i işle
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "❌ ERROR DURING DEQUEUE");
            }
        }

        if (frameJobs.Count > 0)
        {
            _logger.LogInformation("🚀 COLLECTED {Count} FRAMES - CALLING ProcessFrameBatch", frameJobs.Count);
            await ProcessFrameBatch(frameJobs, cancellationToken);
        }
        else
        {
            _logger.LogDebug("📭 NO FRAMES COLLECTED IN THIS BATCH");
        }
    }

    private async Task ProcessFrameBatch(List<FrameJob> frameJobs, CancellationToken cancellationToken)
    {
                    _logger.LogInformation("🔥 PROCESSING BATCH OF {Count} FRAMES 🔥", frameJobs.Count);
        
        const int maxRetries = 3;
        
        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                // AI servisine gönder  
                var imageBytesList = frameJobs.Select(job => job.ImageBytes);
                _logger.LogInformation("🚀 SENDING {Count} FRAMES TO AI SERVICE", frameJobs.Count);
                var batchResult = await _aiClient.DetectFallBatchAsync(imageBytesList, cancellationToken);
                _logger.LogInformation("✅ AI SERVICE RETURNED {Count} RESULTS", batchResult.Results.Count);
                
                // DB yazımını backend'de devre dışı bırak – AI service sonuçları zaten DB'ye yazıyor
                _logger.LogInformation("💾 Skipping backend DB write; AI service persists results to shared database");
                
                _logger.LogDebug("Successfully processed batch of {Count} frames", frameJobs.Count);
                return; // Başarılı, retry'a gerek yok
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Attempt {Attempt}/{MaxRetries} failed for batch processing", attempt, maxRetries);
                
                if (attempt == maxRetries)
                {
                    _logger.LogError(ex, "Failed to process batch after {MaxRetries} attempts", maxRetries);
                    // TODO: Dead letter queue'ya at veya başka hata yönetimi
                }
                else
                {
                    // Exponential backoff
                    var delay = TimeSpan.FromMilliseconds(Math.Pow(2, attempt) * 1000);
                    await Task.Delay(delay, cancellationToken);
                }
            }
        }
    }

    private async Task SaveResults(List<FrameJob> frameJobs, AiBatchResult batchResult, CancellationToken cancellationToken)
    {
        using var scope = _serviceProvider.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();

        var fallDetections = new List<FallDetection>();

        for (int i = 0; i < frameJobs.Count && i < batchResult.Results.Count; i++)
        {
            var frameJob = frameJobs[i];
            var aiResult = batchResult.Results[i];

            var fallDetection = new FallDetection
            {
                ImageHash = aiResult.ImageHash,
                Result = aiResult.Result,
                Confidence = aiResult.Confidence,
                CreatedAt = DateTime.SpecifyKind(DateTime.Now, DateTimeKind.Unspecified) // PostgreSQL için Kind=Unspecified
                // ProcessingTimeMs batch response'da yok, tek request'de var
            };

            fallDetections.Add(fallDetection);
        }

        dbContext.FallDetections.AddRange(fallDetections);
        
        try
        {
            await dbContext.SaveChangesAsync(cancellationToken);
            _logger.LogInformation("💾 SAVED {Count} FALL DETECTION RESULTS TO DATABASE", fallDetections.Count);
        }
        catch (DbUpdateException ex) when (ex.InnerException?.Message?.Contains("duplicate key value violates unique constraint") == true)
        {
            // Duplicate hash - ignore and continue (AI service already processed this image)
            _logger.LogWarning("Duplicate image hash detected, skipping {Count} results (AI service cache hit)", fallDetections.Count);
        }
    }
}
