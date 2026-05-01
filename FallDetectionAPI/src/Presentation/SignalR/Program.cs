using FallDetectionAPI.SignalR.Hubs;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddSignalR(options =>
{
    options.EnableDetailedErrors = true;
    options.HandshakeTimeout = TimeSpan.FromSeconds(30);
    options.KeepAliveInterval = TimeSpan.FromSeconds(15);
    options.ClientTimeoutInterval = TimeSpan.FromSeconds(60);
    options.MaximumReceiveMessageSize = 1024 * 1024;
});

builder.Services.AddCors(options =>
{
    options.AddPolicy("SignalRCors", policy =>
    {
        var origins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>() ?? [];
        // SignalR negotiate uses credentialed requests; wildcard ACAO (*) is invalid with credentials.
        if (origins.Length == 0)
        {
            origins =
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173"
            ];
        }

        policy.WithOrigins(origins).AllowAnyHeader().AllowAnyMethod().AllowCredentials();
    });
});

var app = builder.Build();
app.UseCors("SignalRCors");
app.MapControllers();
app.MapHub<AlertHub>("/alertHub");
app.MapGet("/health", () => new
{
    status = "healthy",
    service = "FallDetection SignalR Host",
    timestamp = DateTime.UtcNow
});

app.Run();
