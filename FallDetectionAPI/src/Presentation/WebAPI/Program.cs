using FallDetectionAPI.Application;
using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Configuration;
using FallDetectionAPI.Persistence;
using FallDetectionAPI.Persistence.Data;
using FallDetectionAPI.Integration;
using FallDetectionAPI.Services;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// Add Swagger/OpenAPI
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Add Controllers
builder.Services.AddControllers();
builder.Services.Configure<CorsOptions>(builder.Configuration.GetSection(CorsOptions.SectionName));

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        var allowedOrigins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>() ?? [];
        if (allowedOrigins.Length == 0)
        {
            policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod();
        }
        else
        {
            policy.WithOrigins(allowedOrigins).AllowAnyHeader().AllowAnyMethod().AllowCredentials();
        }
    });
});

builder.Services.AddApplication();
builder.Services.AddPersistence(builder.Configuration);
builder.Services.AddIntegration(builder.Configuration);
builder.Services.AddSingleton<ICameraAlertService, CameraAlertService>();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.EnsureCreated();
}

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// HTTPS redirection disabled for Docker/local development
// app.UseHttpsRedirection();

// Use CORS
app.UseCors("AllowAll");

// Serve static files
app.UseStaticFiles();

// Health check endpoint
app.MapGet("/api/health", () => new {
    status = "healthy", 
    service = "FallDetection Backend API",
    timestamp = DateTime.UtcNow,
    signalr = "external-host"
});

app.MapControllers();

app.Run();

public partial class Program { }