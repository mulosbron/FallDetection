namespace FallDetectionAPI.Integration.Configuration;

public class MockCameraOptions
{
    public const string SectionName = "MockCamera";
    public string BaseUrl { get; set; } = "http://fall_detection_mock_stream_injector:8001";

    /// <summary>HLS reachability check from the server (WebAPI container) - Docker network host name.</summary>
    public string HlsBaseUrl { get; set; } = "http://localhost:8888";

    /// <summary>Manifest URL for browser/dashboard; if empty, <see cref="HlsBaseUrl"/> is used.</summary>
    public string? HlsPublicBaseUrl { get; set; }

    public string StreamPathPrefix { get; set; } = "/live";
    /// <summary>0 or negative: adaptive scan mode (upper bound uses an internal safe limit).</summary>
    public int MaxCameraProbe { get; set; } = 0;

    /// <summary>At least this many camera indexes are probed in adaptive scanning.</summary>
    public int MinCameraProbe { get; set; } = 8;

    /// <summary>Scanning stops when consecutive unreachable streams exceed this threshold.</summary>
    public int ConsecutiveMissStopThreshold { get; set; } = 4;
}
