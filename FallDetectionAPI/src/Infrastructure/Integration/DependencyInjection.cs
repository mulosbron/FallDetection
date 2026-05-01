using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Integration.Clients;
using FallDetectionAPI.Integration.Configuration;
using FallDetectionAPI.Integration.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace FallDetectionAPI.Integration;

public static class DependencyInjection
{
    public static IServiceCollection AddIntegration(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<AiServiceOptions>(configuration.GetSection(AiServiceOptions.SectionName));
        services.Configure<MockCameraOptions>(configuration.GetSection(MockCameraOptions.SectionName));
        services.Configure<SignalRHostOptions>(configuration.GetSection(SignalRHostOptions.SectionName));
        services.Configure<QueueOptions>(configuration.GetSection(QueueOptions.SectionName));

        services.AddHttpClient<IAiGateway, AiGateway>();
        services.AddHttpClient<IMockCameraGateway, MockCameraGateway>();
        services.AddHttpClient<IRealtimeNotifier, SignalRHostNotifier>();

        services.AddSingleton<FrameQueueService>();
        services.AddSingleton<IFrameQueueService>(sp => sp.GetRequiredService<FrameQueueService>());
        services.AddHostedService(sp => sp.GetRequiredService<FrameQueueService>());

        return services;
    }
}
