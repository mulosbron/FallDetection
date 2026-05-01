using FallDetectionAPI.Application.Abstractions;
using FallDetectionAPI.Persistence.Data;
using FallDetectionAPI.Persistence.Repositories;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace FallDetectionAPI.Persistence;

public static class DependencyInjection
{
    public static IServiceCollection AddPersistence(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddDbContext<AppDbContext>(options =>
            options.UseNpgsql(configuration.GetConnectionString("Default")));

        services.AddScoped<IFallDetectionRepository, FallDetectionRepository>();
        return services;
    }
}
