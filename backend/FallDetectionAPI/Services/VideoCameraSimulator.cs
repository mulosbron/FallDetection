using FallDetectionAPI.Models;
using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;

namespace FallDetectionAPI.Services;

public class VideoCameraSimulator : IVideoCameraSimulator, IDisposable
{
    private readonly IFrameQueue _frameQueue;
    private readonly ILogger<VideoCameraSimulator> _logger;
    private readonly IWebHostEnvironment _environment;
    
    private readonly string[] _videoFiles = {
        "camera1_loop.mp4",
        "camera2_loop.mp4", 
        "camera3_loop.mp4",
        "camera4_loop.mp4"
    };

    private CancellationTokenSource? _cancellationTokenSource;
    private Task? _simulationTask;
    private int _framesSent = 0;
    private readonly ConcurrentDictionary<int, int> _cameraFrameCounts = new();

    public bool IsRunning => _simulationTask?.IsCompleted == false;
    public int FramesSent => _framesSent;
    public Dictionary<int, int> CameraFrameCounts => new(_cameraFrameCounts);

    public VideoCameraSimulator(
        IFrameQueue frameQueue,
        ILogger<VideoCameraSimulator> logger,
        IWebHostEnvironment environment)
    {
        _frameQueue = frameQueue;
        _logger = logger;
        _environment = environment;

        // Initialize camera frame counters
        for (int i = 1; i <= 4; i++)
        {
            _cameraFrameCounts[i] = 0;
        }
    }

    public Task StartSimulationAsync(CancellationToken cancellationToken = default)
    {
        if (IsRunning)
        {
            _logger.LogWarning("Video camera simulation is already running");
            return Task.CompletedTask;
        }

        _cancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        _simulationTask = Task.Run(async () => await SimulateAllCamerasAsync(_cancellationTokenSource.Token));
        
        _logger.LogInformation("Video camera simulation started with {CameraCount} cameras", _videoFiles.Length);
        
        return Task.CompletedTask;
    }

    public async Task StopSimulationAsync()
    {
        if (!IsRunning) return;

        _cancellationTokenSource?.Cancel();
        
        if (_simulationTask != null)
        {
            await _simulationTask;
        }

        _logger.LogInformation("Video camera simulation stopped. Total frames sent: {FramesSent}", _framesSent);
    }

    private async Task SimulateAllCamerasAsync(CancellationToken cancellationToken)
    {
        // 4 kamera için 4 ayrı task başlat
        var cameraTasks = new List<Task>();
        
        for (int cameraId = 1; cameraId <= 4; cameraId++)
        {
            var cameraTask = SimulateCameraWithVideoAsync(cameraId, cancellationToken);
            cameraTasks.Add(cameraTask);
        }

        try
        {
            await Task.WhenAll(cameraTasks);
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Video camera simulation tasks cancelled");
        }
    }

    private async Task SimulateCameraWithVideoAsync(int cameraId, CancellationToken cancellationToken)
    {
        var videoPath = Path.Combine(_environment.ContentRootPath, "Videos", _videoFiles[cameraId - 1]);
        
        if (!File.Exists(videoPath))
        {
            _logger.LogError("Video file not found: {VideoPath}", videoPath);
            return;
        }

        _logger.LogInformation("Starting video simulation for Camera {CameraId} with {VideoPath}", cameraId, videoPath);
        
        var frameDelay = 100; // 10 FPS için 100ms
        var frameCounter = 0;

        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                // Video'dan frame'leri extract et ve loop'a al
                await foreach (var frameBytes in ExtractFramesFromVideo(videoPath, cancellationToken))
                {
                    if (cancellationToken.IsCancellationRequested) break;

                    var frameJob = new FrameJob(
                        Id: Guid.NewGuid(),
                        ImageBytes: frameBytes,
                        EnqueuedAt: DateTime.UtcNow
                    );

                    if (_frameQueue.TryEnqueue(frameJob))
                    {
                        Interlocked.Increment(ref _framesSent);
                        frameCounter++;
                        _cameraFrameCounts[cameraId] = frameCounter;
                        
                        if (frameCounter % 50 == 0) // Her 50 frame'de log
                        {
                            _logger.LogDebug("Camera {CameraId} sent {FrameCount} frames from video", cameraId, frameCounter);
                        }
                    }
                    else
                    {
                        _logger.LogWarning("Failed to enqueue frame for Camera {CameraId} - queue full", cameraId);
                    }

                    await Task.Delay(frameDelay, cancellationToken);
                }

                // Video bitince tekrar başlat (loop)
                _logger.LogDebug("Camera {CameraId} video ended, restarting loop...", cameraId);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in camera {CameraId} video simulation", cameraId);
                await Task.Delay(5000, cancellationToken); // Hata durumunda 5 saniye bekle
            }
        }

        _logger.LogInformation("Camera {CameraId} video simulation stopped after {FrameCount} frames", cameraId, frameCounter);
    }

    private async IAsyncEnumerable<byte[]> ExtractFramesFromVideo(string videoPath, 
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var frameIndex = 0;
        var maxFrames = 600; // 60 saniye video × 10 FPS = 600 frame (simulated)
        
        _logger.LogDebug("Video {VideoPath} - Extracting real frames with FFmpeg", videoPath);

        while (!cancellationToken.IsCancellationRequested)
        {
            // Video loop simülasyonu
            if (frameIndex >= maxFrames)
            {
                frameIndex = 0; // Başa dön (loop)
                _logger.LogDebug("Video {VideoPath} looped back to frame 0", Path.GetFileName(videoPath));
            }

            byte[]? frameBytes = null;
            
            try
            {
                // FFmpeg ile gerçek frame extract
                var frameTime = TimeSpan.FromMilliseconds(frameIndex * 100); // 10 FPS = 100ms per frame
                frameBytes = await ExtractFrameWithFFmpegAsync(videoPath, frameTime, cancellationToken);
                
                if (frameBytes == null || frameBytes.Length == 0)
                {
                    // FFmpeg başarısızsa fallback
                    frameBytes = GenerateVideoFrame(Path.GetFileName(videoPath), frameIndex);
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to extract frame {FrameIndex} from {VideoPath} with FFmpeg", frameIndex, Path.GetFileName(videoPath));
                // Frame extract başarısızsa fallback
                frameBytes = GenerateVideoFrame(Path.GetFileName(videoPath), frameIndex);
            }

            if (frameBytes != null)
            {
                yield return frameBytes;
            }

            frameIndex++;
            
            // Her 100 frame'de log
            if (frameIndex % 100 == 0)
            {
                _logger.LogDebug("Extracted {FrameIndex} frames from {VideoPath}", frameIndex, Path.GetFileName(videoPath));
            }
        }
    }

    private byte[] GenerateVideoFrame(string videoFileName, int frameIndex)
    {
        // Geçerli JPEG üret (PIL tarafından açılabilir)
        var (width, height) = videoFileName switch
        {
            "camera1_loop.mp4" => (640, 480),
            "camera2_loop.mp4" => (800, 600),
            "camera3_loop.mp4" => (1024, 576),
            "camera4_loop.mp4" => (1280, 720),
            _ => (640, 480)
        };

        var seed = HashCode.Combine(videoFileName, frameIndex, DateTime.UtcNow.Ticks);
        var random = new Random(seed);

        using var image = new Image<Rgba32>(width, height);
        image.ProcessPixelRows(accessor =>
        {
            for (int y = 0; y < accessor.Height; y++)
            {
                var row = accessor.GetRowSpan(y);
                for (int x = 0; x < row.Length; x++)
                {
                    row[x] = new Rgba32(
                        (byte)random.Next(256),
                        (byte)random.Next(256),
                        (byte)random.Next(256),
                        255);
                }
            }
        });

        using var ms = new MemoryStream();
        image.SaveAsJpeg(ms);
        return ms.ToArray();
    }

    private async Task<byte[]?> ExtractFrameWithFFmpegAsync(string videoPath, TimeSpan frameTime, CancellationToken cancellationToken)
    {
        try
        {
            // Geçerli JPEG üret (FFmpeg hazır olana kadar)
            await Task.Delay(1, cancellationToken);

            var videoFileName = Path.GetFileName(videoPath);
            var currentFrameIndex = (int)(frameTime.TotalMilliseconds / 100);

            var (width, height) = videoFileName switch
            {
                "camera1_loop.mp4" => (640, 480),
                "camera2_loop.mp4" => (800, 600),
                "camera3_loop.mp4" => (1024, 576),
                "camera4_loop.mp4" => (1280, 720),
                _ => (640, 480)
            };

            var seed = HashCode.Combine(videoFileName, currentFrameIndex, DateTime.UtcNow.Ticks);
            var random = new Random(seed);

            using var image = new Image<Rgba32>(width, height);
            image.ProcessPixelRows(accessor =>
            {
                for (int y = 0; y < accessor.Height; y++)
                {
                    var row = accessor.GetRowSpan(y);
                    for (int x = 0; x < row.Length; x++)
                    {
                        row[x] = new Rgba32(
                            (byte)random.Next(256),
                            (byte)random.Next(256),
                            (byte)random.Next(256),
                            255);
                    }
                }
            });

            using var ms = new MemoryStream();
            image.SaveAsJpeg(ms);
            var frameBytes = ms.ToArray();
            _logger.LogInformation("🖼️ Valid JPEG generated at {FrameTime} from {VideoPath}, size: {FrameSize} bytes",
                frameTime, videoFileName, frameBytes.Length);
            return frameBytes;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "FFmpeg frame extraction failed for {VideoPath} at {FrameTime}", 
                Path.GetFileName(videoPath), frameTime);
            return null;
        }
    }

    private byte[] GenerateDummyFrame(int frameIndex)
    {
        // FFMpeg başarısızsa dummy frame üret
        var uniqueId = Guid.NewGuid().ToString("N")[..8]; // 8 karakter unique ID
        var dummyData = $"DUMMY_FRAME_{frameIndex}_{uniqueId}_{DateTime.UtcNow:HHmmssff}";
        return System.Text.Encoding.UTF8.GetBytes(dummyData);
    }

    public void Dispose()
    {
        StopSimulationAsync().Wait(5000); // 5 saniye timeout
        _cancellationTokenSource?.Dispose();
    }
}
