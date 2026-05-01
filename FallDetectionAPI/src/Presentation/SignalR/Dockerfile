FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 8081
ENV ASPNETCORE_URLS=http://+:8081

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY ["FallDetectionAPI.sln", "."]
COPY ["src/Presentation/SignalR/FallDetectionAPI.SignalR.csproj", "src/Presentation/SignalR/"]
RUN dotnet restore "src/Presentation/SignalR/FallDetectionAPI.SignalR.csproj"

COPY ["src/", "src/"]
RUN dotnet publish "src/Presentation/SignalR/FallDetectionAPI.SignalR.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app

COPY --from=build /app/publish .

RUN groupadd --system appuser \
    && useradd --system --gid appuser --no-create-home --home-dir /nonexistent appuser \
    && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8081/health >/dev/null || exit 1

ENTRYPOINT ["dotnet", "FallDetectionAPI.SignalR.dll"]
