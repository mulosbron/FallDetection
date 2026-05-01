FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY ["FallDetectionAPI.sln", "."]
COPY ["src/Presentation/WebAPI/FallDetectionAPI.csproj", "src/Presentation/WebAPI/"]
COPY ["src/Core/Application/FallDetectionAPI.Application.csproj", "src/Core/Application/"]
COPY ["src/Core/Domain/FallDetectionAPI.Domain.csproj", "src/Core/Domain/"]
COPY ["src/Infrastructure/Persistence/FallDetectionAPI.Persistence.csproj", "src/Infrastructure/Persistence/"]
COPY ["src/Infrastructure/Integration/FallDetectionAPI.Integration.csproj", "src/Infrastructure/Integration/"]
RUN dotnet restore "src/Presentation/WebAPI/FallDetectionAPI.csproj"

COPY ["src/", "src/"]
RUN dotnet publish "src/Presentation/WebAPI/FallDetectionAPI.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
EXPOSE 8080

ENV ASPNETCORE_ENVIRONMENT=Production
ENV ASPNETCORE_URLS=http://+:8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --gid appuser --no-create-home --home-dir /nonexistent appuser

COPY --from=build /app/publish .
RUN chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/api/health >/dev/null || exit 1

ENTRYPOINT ["dotnet", "FallDetectionAPI.dll"]
