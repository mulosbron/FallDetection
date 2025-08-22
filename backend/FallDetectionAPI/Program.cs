using Microsoft.EntityFrameworkCore;
using FallDetectionAPI.Data;
using FallDetectionAPI.Configuration;
using FallDetectionAPI.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

// Add Controllers
builder.Services.AddControllers();

// Add Entity Framework
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("Default")));

// Add Configuration Options
builder.Services.Configure<AiServiceOptions>(
    builder.Configuration.GetSection(AiServiceOptions.SectionName));
builder.Services.Configure<QueueOptions>(
    builder.Configuration.GetSection(QueueOptions.SectionName));

// Add Custom Services
builder.Services.AddSingleton<IFrameQueue, FrameQueue>();
builder.Services.AddSingleton<IVideoCameraSimulator, VideoCameraSimulator>(); // Video-based camera simulator
builder.Services.AddHostedService<FrameProcessor>();

// Add HttpClient for AiClient (single registration)
builder.Services.AddHttpClient<IAiClient, AiClient>();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();
app.MapControllers();

app.Run();
