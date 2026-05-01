using FallDetectionAPI.Application.Abstractions;
using MediatR;

namespace FallDetectionAPI.Application.Features.Frames;

public record UploadFrameCommand(byte[] ImageData, int CameraId, string FileName) : IRequest<UploadFrameResult>;

public class UploadFrameResult
{
    public bool Success { get; init; }
    public int CameraId { get; init; }
    public int QueueSize { get; init; }
    public string Message { get; init; } = string.Empty;
}

public class UploadFrameCommandHandler : IRequestHandler<UploadFrameCommand, UploadFrameResult>
{
    private readonly IFrameQueueService _frameQueueService;

    public UploadFrameCommandHandler(IFrameQueueService frameQueueService)
    {
        _frameQueueService = frameQueueService;
    }

    public async Task<UploadFrameResult> Handle(UploadFrameCommand request, CancellationToken cancellationToken)
    {
        var ok = await _frameQueueService.EnqueueFrameAsync(
            request.ImageData,
            request.CameraId,
            request.FileName,
            cancellationToken);

        var status = _frameQueueService.GetQueueStatus();
        return new UploadFrameResult
        {
            Success = ok,
            CameraId = request.CameraId,
            QueueSize = status.QueueSize,
            Message = ok ? "Frame enqueued for processing" : "Frame queue is full"
        };
    }
}

public record GetQueueStatusQuery() : IRequest<QueueStatusResponse>;

public class QueueStatusResponse
{
    public int QueueSize { get; init; }
    public IReadOnlyDictionary<int, int> CameraCounters { get; init; } = new Dictionary<int, int>();
}

public class GetQueueStatusQueryHandler : IRequestHandler<GetQueueStatusQuery, QueueStatusResponse>
{
    private readonly IFrameQueueService _frameQueueService;

    public GetQueueStatusQueryHandler(IFrameQueueService frameQueueService)
    {
        _frameQueueService = frameQueueService;
    }

    public Task<QueueStatusResponse> Handle(GetQueueStatusQuery request, CancellationToken cancellationToken)
    {
        var status = _frameQueueService.GetQueueStatus();
        return Task.FromResult(new QueueStatusResponse
        {
            QueueSize = status.QueueSize,
            CameraCounters = status.CameraCounters
        });
    }
}
