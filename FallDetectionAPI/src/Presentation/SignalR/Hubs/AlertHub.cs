using Microsoft.AspNetCore.SignalR;

namespace FallDetectionAPI.SignalR.Hubs;

public class AlertHub : Hub
{
    private readonly ILogger<AlertHub> _logger;

    public AlertHub(ILogger<AlertHub> logger)
    {
        _logger = logger;
    }

    public override async Task OnConnectedAsync()
    {
        _logger.LogInformation("Client connected: {ConnectionId}", Context.ConnectionId);
        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _logger.LogInformation("Client disconnected: {ConnectionId}", Context.ConnectionId);
        await base.OnDisconnectedAsync(exception);
    }

    public async Task JoinAlerts()
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, "Alerts");
        await Clients.Caller.SendAsync("JoinedAlerts", "Successfully joined alerts group");
    }

    public async Task LeaveAlerts()
    {
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, "Alerts");
        await Clients.Caller.SendAsync("LeftAlerts", "Successfully left alerts group");
    }

    public async Task JoinCameraGroup(int cameraIndex)
    {
        var groupName = $"Camera_{cameraIndex}";
        await Groups.AddToGroupAsync(Context.ConnectionId, groupName);
        await Clients.Caller.SendAsync("JoinedCameraGroup", $"Joined camera {cameraIndex} group");
    }

    public async Task LeaveCameraGroup(int cameraIndex)
    {
        var groupName = $"Camera_{cameraIndex}";
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, groupName);
        await Clients.Caller.SendAsync("LeftCameraGroup", $"Left camera {cameraIndex} group");
    }
}
