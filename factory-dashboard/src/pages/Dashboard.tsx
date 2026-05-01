import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Hls from "hls.js";
import {
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  CssBaseline,
  Dialog,
  DialogContent,
  Divider,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Paper,
  Toolbar,
  Typography
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import ErrorIcon from "@mui/icons-material/Error";
import VideocamIcon from "@mui/icons-material/Videocam";
import WarningIcon from "@mui/icons-material/Warning";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import * as signalR from "@microsoft/signalr";

const WEB_API_BASE = process.env.REACT_APP_WEB_API_BASE ?? "http://localhost:5000";
const SIGNALR_URL = process.env.REACT_APP_SIGNALR_URL ?? "http://localhost:5001/alertHub";
/** Duration of red alert border/overlay after FallDetected (ms). */
const FALL_ALERT_DURATION_MS = 3000;

const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#90caf9" },
    secondary: { main: "#f48fb1" },
    background: { default: "#121212", paper: "#1e1e1e" }
  }
});

type LogType = "info" | "error" | "success" | "warning";

interface LogEntry {
  id: number;
  time: string;
  message: string;
  type: LogType;
  cameraId?: string;
  cameraName?: string;
  eventTimestamp?: string;
  imageUrl?: string;
  source?: "signalr" | "polling";
}

interface CameraInventoryItem {
  cameraIndex: number;
  cameraId: string;
  cameraName: string;
  hlsUrl: string;
  isActive: boolean;
}

interface CameraInventoryResponse {
  cameras: CameraInventoryItem[];
  total: number;
  active: number;
  timestamp: string;
}

interface CameraAlertStatusItem {
  CameraIndex: number;
  YesCount: number;
  TotalCount: number;
}

interface CameraAlertStatusResponse {
  Cameras?: CameraAlertStatusItem[] | Record<string, CameraAlertStatusItem>;
  cameras?: CameraAlertStatusItem[] | Record<string, CameraAlertStatusItem>;
}

interface CameraRuntimeState {
  lastResult: string;
  yesCount: number;
  totalCount: number;
  lastUpdated?: string;
  alertUntil?: number;
}

interface CameraUpdateEvent {
  cameraId: string;
  cameraName: string;
  timestamp: string;
  result: string;
  yesCount: number;
  totalCount: number;
  threshold: number;
}

interface FallDetectedEvent {
  cameraId: string;
  cameraName: string;
  timestamp: string;
  message: string;
  yesCount: number;
  totalCount: number;
}

interface IncidentItem {
  id: string;
  cameraId: string;
  cameraName: string;
  timestamp: string;
  type: string;
  frameUrl?: string;
  imageHash?: string;
  result?: string;
}

interface IncidentsResponse {
  incidents?: IncidentItem[];
}

function parseCameraIndex(cameraId: string): number {
  const match = cameraId.match(/cam-(\d+)/i);
  if (!match) {
    return 0;
  }

  return Number.parseInt(match[1], 10);
}

function normalizeCameraUpdate(payload: any): CameraUpdateEvent {
  return {
    cameraId: payload.cameraId ?? payload.CameraId ?? "cam-000",
    cameraName: payload.cameraName ?? payload.CameraName ?? "Camera",
    timestamp: payload.timestamp ?? payload.Timestamp ?? new Date().toISOString(),
    result: payload.result ?? payload.Result ?? "Unknown",
    yesCount: Number(payload.yesCount ?? payload.YesCount ?? 0),
    totalCount: Number(payload.totalCount ?? payload.TotalCount ?? 0),
    threshold: Number(payload.threshold ?? payload.Threshold ?? 1)
  };
}

function normalizeFallDetected(payload: any): FallDetectedEvent {
  return {
    cameraId: payload.cameraId ?? payload.CameraId ?? "cam-000",
    cameraName: payload.cameraName ?? payload.CameraName ?? "Camera",
    timestamp: payload.timestamp ?? payload.Timestamp ?? new Date().toISOString(),
    message: payload.message ?? payload.Message ?? "Fall detected",
    yesCount: Number(payload.yesCount ?? payload.YesCount ?? 0),
    totalCount: Number(payload.totalCount ?? payload.TotalCount ?? 0)
  };
}

function normalizeAlertStatusRows(payload: CameraAlertStatusResponse): CameraAlertStatusItem[] {
  const raw = payload.Cameras ?? payload.cameras ?? [];
  if (Array.isArray(raw)) {
    return raw;
  }

  if (raw && typeof raw === "object") {
    return Object.values(raw);
  }

  return [];
}

function toAbsoluteWebApiUrl(urlOrPath: string | undefined): string | undefined {
  if (!urlOrPath) {
    return undefined;
  }

  if (/^https?:\/\//i.test(urlOrPath)) {
    return urlOrPath;
  }

  return `${WEB_API_BASE.replace(/\/$/, "")}/${urlOrPath.replace(/^\//, "")}`;
}

function CameraHlsPlayer({ hlsUrl, hasAlert }: { hlsUrl: string; hasAlert: boolean }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const videoElement = videoRef.current;
    if (!videoElement) {
      return;
    }

    if (videoElement.canPlayType("application/vnd.apple.mpegurl")) {
      videoElement.src = hlsUrl;
      void videoElement.play().catch(() => undefined);
      return () => {
        videoElement.removeAttribute("src");
        videoElement.load();
      };
    }

    if (!Hls.isSupported()) {
      return undefined;
    }

    const hls = new Hls({
      lowLatencyMode: true,
      liveSyncDurationCount: 2
    });

    hls.loadSource(hlsUrl);
    hls.attachMedia(videoElement);
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      void videoElement.play().catch(() => undefined);
    });

    return () => {
      hls.destroy();
    };
  }, [hlsUrl]);

  return (
    <Box
      sx={{
        position: "relative",
        width: "100%",
        paddingTop: "56.25%",
        backgroundColor: hasAlert ? "#3d0000" : "#000",
        borderRadius: 1,
        overflow: "hidden",
        border: hasAlert ? "2px solid #f44336" : "1px solid #263238"
      }}
    >
      <video
        ref={videoRef}
        muted
        autoPlay
        playsInline
        controls={false}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover"
        }}
      />
      {hasAlert && (
        <Box
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(244, 67, 54, 0.22)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: "bold" }}>
            FALL DETECTED
          </Typography>
        </Box>
      )}
    </Box>
  );
}

function Dashboard() {
  const [inventory, setInventory] = useState<CameraInventoryItem[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isCameraConnected, setIsCameraConnected] = useState(false);
  const [isSignalRConnected, setIsSignalRConnected] = useState(false);
  const [cameraState, setCameraState] = useState<Record<number, CameraRuntimeState>>({});
  const [lastDataSource, setLastDataSource] = useState<"signalr" | "polling" | "none">("none");
  const [selectedCamera, setSelectedCamera] = useState<CameraInventoryItem | null>(null);
  const [selectedIncidentImage, setSelectedIncidentImage] = useState<{
    url: string;
    title: string;
    subtitle: string;
  } | null>(null);
  const [recentIncidents, setRecentIncidents] = useState<IncidentItem[]>([]);
  const connectionRef = useRef<signalR.HubConnection | null>(null);
  const knownIncidentIdsRef = useRef<Set<string>>(new Set());
  /** React Strict Mode (dev): cleanup can close negotiate; do not treat as an error. */
  const signalRClosingRef = useRef(false);

  const addLog = useCallback((message: string, type: LogType = "info", extra?: Partial<LogEntry>) => {
    const time = new Date().toLocaleTimeString("en-US");
    setLogs((prev) => [{ id: Date.now() + Math.random(), time, message, type, ...extra }, ...prev.slice(0, 149)]);
  }, []);

  const fetchInventory = useCallback(async () => {
    try {
      const response = await fetch(`${WEB_API_BASE.replace(/\/$/, "")}/api/camera/inventory`);
      if (!response.ok) {
        throw new Error(`inventory status ${response.status}`);
      }

      const data = (await response.json()) as CameraInventoryResponse;
      setInventory(data.cameras ?? []);
      setIsCameraConnected((data.cameras ?? []).length > 0);
    } catch (error) {
      setIsCameraConnected(false);
      addLog(`Camera inventory fetch failed: ${error}`, "error");
    }
  }, [addLog]);

  const fetchAlertStatus = useCallback(async () => {
    try {
      const response = await fetch(`${WEB_API_BASE.replace(/\/$/, "")}/api/camera/alert-status`);
      if (!response.ok) {
        throw new Error(`alert-status ${response.status}`);
      }

      const data = (await response.json()) as CameraAlertStatusResponse;
      const rows = normalizeAlertStatusRows(data);

      setCameraState((prev) => {
        const next = { ...prev };
        for (const row of rows) {
          const cameraIndex = Number((row as any).CameraIndex ?? (row as any).cameraIndex ?? 0);
          if (!Number.isFinite(cameraIndex) || cameraIndex <= 0) {
            continue;
          }

          const yesCount = Number((row as any).YesCount ?? (row as any).yesCount ?? 0);
          const totalCount = Number((row as any).TotalCount ?? (row as any).totalCount ?? 0);
          const current = next[cameraIndex];
          const shouldApply = !current || current.totalCount <= totalCount;
          if (!shouldApply) {
            continue;
          }

          next[cameraIndex] = {
            ...current,
            lastResult: yesCount > 0 ? current?.lastResult ?? "Yes" : current?.lastResult ?? "No",
            yesCount,
            totalCount,
            lastUpdated: current?.lastUpdated ?? new Date().toISOString()
          };
        }

        return next;
      });

      setLastDataSource("polling");
    } catch (error) {
      addLog(`Alert status polling failed: ${error}`, "warning");
    }
  }, [addLog]);

  const fetchLatestIncidents = useCallback(async () => {
    try {
      const response = await fetch(
        `${WEB_API_BASE.replace(/\/$/, "")}/api/results/incidents?page=1&pageSize=25&type=Fall`
      );
      if (!response.ok) {
        throw new Error(`incidents ${response.status}`);
      }

      const data = (await response.json()) as IncidentsResponse;
      const incidents = Array.isArray(data.incidents) ? data.incidents : [];
      setRecentIncidents(incidents);

      if (knownIncidentIdsRef.current.size === 0) {
        for (const incident of incidents) {
          knownIncidentIdsRef.current.add(String(incident.id));
        }
        return;
      }

      const unseen = incidents
        .filter((incident) => !knownIncidentIdsRef.current.has(String(incident.id)))
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      for (const incident of unseen) {
        const frameImageUrl = toAbsoluteWebApiUrl(incident.frameUrl);
        addLog(
          `ALERT ${incident.cameraName} (${incident.cameraId}) - ${incident.type}`,
          "warning",
          {
            cameraId: incident.cameraId,
            cameraName: incident.cameraName,
            eventTimestamp: incident.timestamp,
            imageUrl: frameImageUrl,
            source: "polling"
          }
        );
      }

      for (const incident of incidents) {
        knownIncidentIdsRef.current.add(String(incident.id));
      }

      if (unseen.length > 0) {
        setLastDataSource("polling");
      }
    } catch (error) {
      addLog(`Incident polling failed: ${error}`, "warning");
    }
  }, [addLog]);

  useEffect(() => {
    addLog("Dashboard started", "success");
    fetchInventory();
    void fetchAlertStatus();
    void fetchLatestIncidents();

    const inventoryTimer = setInterval(fetchInventory, 7000);
    const alertStatusTimer = setInterval(() => {
      void fetchAlertStatus();
    }, 4000);
    const incidentTimer = setInterval(() => {
      void fetchLatestIncidents();
    }, 3000);

    return () => {
      clearInterval(inventoryTimer);
      clearInterval(alertStatusTimer);
      clearInterval(incidentTimer);
    };
  }, [addLog, fetchAlertStatus, fetchInventory, fetchLatestIncidents]);

  useEffect(() => {
    signalRClosingRef.current = false;

    const connection = new signalR.HubConnectionBuilder()
      .withUrl(SIGNALR_URL, { withCredentials: false })
      .withAutomaticReconnect([0, 2000, 5000, 10000, 30000])
      .configureLogging(signalR.LogLevel.Warning)
      .build();

    connectionRef.current = connection;

    connection.on("CameraUpdate", (rawPayload) => {
      const payload = normalizeCameraUpdate(rawPayload);
      const cameraIndex = parseCameraIndex(payload.cameraId);

      setCameraState((prev) => ({
        ...prev,
        [cameraIndex]: {
          ...prev[cameraIndex],
          lastResult: payload.result,
          yesCount: payload.yesCount,
          totalCount: payload.totalCount,
          lastUpdated: payload.timestamp
        }
      }));

      setLastDataSource("signalr");
      addLog(
        `CameraUpdate ${payload.cameraId} @ ${payload.timestamp}: ${payload.result} (${payload.yesCount}/${payload.totalCount})`,
        "info"
      );
    });

    connection.on("FallDetected", (rawPayload) => {
      const payload = normalizeFallDetected(rawPayload);
      const cameraIndex = parseCameraIndex(payload.cameraId);
      const alertUntil = Date.now() + FALL_ALERT_DURATION_MS;

      addLog(
        `FALL ALARM: ${payload.cameraName} — ${FALL_ALERT_DURATION_MS / 1000}s red highlight`,
        "error"
      );

      setCameraState((prev) => ({
        ...prev,
        [cameraIndex]: {
          ...prev[cameraIndex],
          lastResult: "FALL",
          yesCount: payload.yesCount,
          totalCount: payload.totalCount,
          lastUpdated: payload.timestamp,
          alertUntil
        }
      }));

      setLastDataSource("signalr");
      addLog(
        `FallDetected ${payload.cameraId} @ ${payload.timestamp}: ${payload.message} (${payload.yesCount}/${payload.totalCount})`,
        "warning",
        {
          cameraId: payload.cameraId,
          cameraName: payload.cameraName,
          eventTimestamp: payload.timestamp,
          source: "signalr"
        }
      );

      window.setTimeout(() => {
        setCameraState((prev) => {
          const current = prev[cameraIndex];
          if (!current || !current.alertUntil || current.alertUntil > Date.now()) {
            return prev;
          }

          return {
            ...prev,
            [cameraIndex]: {
              ...current,
              alertUntil: undefined
            }
          };
        });
      }, FALL_ALERT_DURATION_MS + 200);
    });

    connection.on("JoinedAlerts", (message: string) => {
      addLog(`SignalR: ${message}`, "success");
    });

    connection.onreconnecting(() => {
      setIsSignalRConnected(false);
      addLog("SignalR reconnecting - waiting for transport recovery", "warning");
    });

    connection.onreconnected(async () => {
      setIsSignalRConnected(true);
      addLog("SignalR reconnected", "success");
      await connection.invoke("JoinAlerts");
    });

    connection.onclose(() => {
      setIsSignalRConnected(false);
      if (!signalRClosingRef.current) {
        addLog("SignalR connection closed unexpectedly", "error");
      }
    });

    // @types/node + dom: setTimeout signature can be NodeJS.Timeout / number
    let retryTimer: ReturnType<typeof globalThis.setTimeout> | undefined;

    const start = async () => {
      try {
        await connection.start();
        if (signalRClosingRef.current) {
          await connection.stop().catch(() => undefined);
          return;
        }

        await connection.invoke("JoinAlerts");
        if (signalRClosingRef.current) {
          await connection.stop().catch(() => undefined);
          return;
        }

        setIsSignalRConnected(true);
        addLog("SignalR connection established", "success");
      } catch (error) {
        if (signalRClosingRef.current) {
          return;
        }

        setIsSignalRConnected(false);
        addLog(`SignalR connection failed: ${error}`, "error");
        retryTimer = globalThis.setTimeout(() => {
          void start();
        }, 4000);
      }
    };

    void start();

    return () => {
      if (retryTimer !== undefined) {
        globalThis.clearTimeout(retryTimer);
      }

      signalRClosingRef.current = true;
      void connection.stop().catch(() => undefined);
    };
  }, [addLog]);

  const summary = useMemo(() => {
    const total = inventory.length;
    const active = inventory.filter((camera) => camera.isActive).length;
    const transientAlertCount = inventory.filter((camera) => {
      const state = cameraState[camera.cameraIndex];
      return Boolean(state?.alertUntil && state.alertUntil > Date.now());
    }).length;
    const camerasWithAlerts = inventory.filter((camera) => {
      const state = cameraState[camera.cameraIndex];
      return (state?.yesCount ?? 0) > 0;
    }).length;
    const alertCount = inventory.reduce((sum, camera) => {
      const state = cameraState[camera.cameraIndex];
      return sum + Math.max(0, state?.yesCount ?? 0);
    }, 0);

    return { total, active, alertCount, transientAlertCount, camerasWithAlerts };
  }, [inventory, cameraState]);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <AppBar position="static" color="default" elevation={1}>
          <Toolbar>
            <VideocamIcon sx={{ mr: 2 }} />
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Factory Camera Dashboard
            </Typography>
            <Chip
              icon={isCameraConnected ? <CheckCircleIcon /> : <ErrorIcon />}
              label={isCameraConnected ? "Camera inventory loaded" : "Camera inventory unavailable"}
              color={isCameraConnected ? "success" : "error"}
              variant="outlined"
              size="small"
              sx={{ mr: 1 }}
            />
            <Chip
              icon={isSignalRConnected ? <CheckCircleIcon /> : <WarningIcon />}
              label={isSignalRConnected ? "SignalR connected" : "SignalR disconnected"}
              color={isSignalRConnected ? "success" : "warning"}
              variant="outlined"
              size="small"
            />
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ mt: 3, mb: 3, flexGrow: 1 }}>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, lg: 9 }}>
              <Typography variant="h5" gutterBottom>
                Cameras ({summary.total}) - Active: {summary.active} - Alerts: {summary.alertCount}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                Cameras with alerts: {summary.camerasWithAlerts} - Instant SignalR alerts (3s): {summary.transientAlertCount}
              </Typography>
              <Grid container spacing={2}>
                {inventory.length === 0 ? (
                  <Grid size={{ xs: 12 }}>
                    <Paper sx={{ p: 4, textAlign: "center" }}>
                      <Typography color="text.secondary">No cameras found. Check HLS endpoints.</Typography>
                    </Paper>
                  </Grid>
                ) : (
                  inventory.map((camera) => {
                    const runtime = cameraState[camera.cameraIndex];
                    const hasAlert = Boolean(runtime?.alertUntil && runtime.alertUntil > Date.now());

                    return (
                      <Grid size={{ xs: 12, sm: 6, md: 4 }} key={camera.cameraId}>
                        <Card
                          elevation={3}
                          sx={{
                            border: hasAlert ? "2px solid #f44336" : "1px solid #263238",
                            cursor: "pointer"
                          }}
                          onClick={() => setSelectedCamera(camera)}
                        >
                          <CardContent sx={{ p: 1.25, "&:last-child": { pb: 1.25 } }}>
                            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
                              <Typography variant="subtitle2" fontWeight="bold">
                                {camera.cameraName}
                              </Typography>
                              <Chip
                                size="small"
                                label={hasAlert ? "ALERT" : camera.isActive ? "Active" : "Inactive"}
                                color={hasAlert ? "error" : camera.isActive ? "success" : "default"}
                              />
                            </Box>
                            <CameraHlsPlayer hlsUrl={camera.hlsUrl} hasAlert={hasAlert} />
                            <Box sx={{ display: "flex", justifyContent: "space-between", mt: 1 }}>
                              <Typography variant="caption" color="text.secondary">
                                Result: {runtime?.lastResult ?? "N/A"}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Yes/Total: {runtime?.yesCount ?? 0}/{runtime?.totalCount ?? 0}
                              </Typography>
                            </Box>
                            <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 0.5 }}>
                              <Typography variant="caption" color="text.secondary">
                                {runtime?.lastUpdated ? new Date(runtime.lastUpdated).toLocaleTimeString("en-US") : "No updates yet"}
                              </Typography>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    );
                  })
                )}
              </Grid>
            </Grid>

            <Grid size={{ xs: 12, lg: 3 }}>
              <Typography variant="h5" gutterBottom>
                Event Logs
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                Last data source: {lastDataSource === "none" ? "-" : lastDataSource === "signalr" ? "SignalR" : "Polling"}
              </Typography>
              <Paper elevation={3} sx={{ height: "calc(100vh - 200px)", overflow: "auto", backgroundColor: "#0d1117" }}>
                <List dense>
                  {logs.length === 0 ? (
                    <ListItem>
                      <ListItemText secondary="No logs yet" sx={{ textAlign: "center" }} />
                    </ListItem>
                  ) : (
                    logs.map((log, index) => (
                      <React.Fragment key={log.id}>
                        <ListItem sx={{ py: 0.5 }}>
                          <ListItemText
                            primary={
                              <Box>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontFamily: "monospace",
                                    fontSize: "0.8rem",
                                    color:
                                      log.type === "error"
                                        ? "#f44336"
                                        : log.type === "success"
                                          ? "#4caf50"
                                          : log.type === "warning"
                                            ? "#ff9800"
                                            : "#90caf9"
                                  }}
                                >
                                  [{log.time}] {log.message}
                                </Typography>
                                {(log.eventTimestamp || log.cameraName || log.source || log.imageUrl) && (
                                  <Box sx={{ mt: 0.5 }}>
                                    {log.eventTimestamp && (
                                      <Typography variant="caption" sx={{ color: "#9e9e9e", display: "block" }}>
                                        Event time: {new Date(log.eventTimestamp).toLocaleString("en-US")}
                                      </Typography>
                                    )}
                                    {log.cameraName && (
                                      <Typography variant="caption" sx={{ color: "#9e9e9e", display: "block" }}>
                                        Camera: {log.cameraName} ({log.cameraId ?? "N/A"})
                                      </Typography>
                                    )}
                                    {log.source && (
                                      <Typography variant="caption" sx={{ color: "#9e9e9e", display: "block" }}>
                                        Source: {log.source === "signalr" ? "SignalR" : "Polling"}
                                      </Typography>
                                    )}
                                    {log.imageUrl && (
                                      <Button
                                        size="small"
                                        variant="outlined"
                                        sx={{ mt: 0.75 }}
                                        onClick={() =>
                                          setSelectedIncidentImage({
                                            url: log.imageUrl!,
                                            title: `${log.cameraName ?? "Camera"} Snapshot`,
                                            subtitle: log.eventTimestamp
                                              ? new Date(log.eventTimestamp).toLocaleString("en-US")
                                              : "Unknown event time"
                                          })
                                        }
                                      >
                                        Alert Image
                                      </Button>
                                    )}
                                  </Box>
                                )}
                              </Box>
                            }
                          />
                        </ListItem>
                        {index < logs.length - 1 && <Divider component="li" />}
                      </React.Fragment>
                    ))
                  )}
                </List>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12 }}>
              <Typography variant="h5" gutterBottom>
                Saved Alert Images
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                Latest fall incidents ({recentIncidents.length}) from stored snapshots
              </Typography>
              {recentIncidents.length === 0 ? (
                <Paper sx={{ p: 2, textAlign: "center", backgroundColor: "#0d1117" }}>
                  <Typography variant="body2" color="text.secondary">
                    No saved alert image yet.
                  </Typography>
                </Paper>
              ) : (
                <Grid container spacing={2}>
                  {recentIncidents.slice(0, 12).map((incident) => {
                    const frameImageUrl = toAbsoluteWebApiUrl(incident.frameUrl);
                    return (
                      <Grid key={incident.id} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
                        <Card sx={{ backgroundColor: "#0d1117", border: "1px solid #263238" }}>
                          <CardContent sx={{ p: 1.25, "&:last-child": { pb: 1.25 } }}>
                            <Typography variant="subtitle2" fontWeight="bold">
                              {incident.cameraName}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                              {new Date(incident.timestamp).toLocaleString("en-US")}
                            </Typography>
                            {frameImageUrl ? (
                              <Box
                                component="img"
                                src={frameImageUrl}
                                alt={`${incident.cameraName} alert snapshot`}
                                sx={{
                                  width: "100%",
                                  height: 140,
                                  objectFit: "cover",
                                  borderRadius: 1,
                                  border: "1px solid #37474f",
                                  cursor: "pointer"
                                }}
                                onClick={() =>
                                  setSelectedIncidentImage({
                                    url: frameImageUrl,
                                    title: `${incident.cameraName} Snapshot`,
                                    subtitle: new Date(incident.timestamp).toLocaleString("en-US")
                                  })
                                }
                              />
                            ) : (
                              <Paper sx={{ p: 1.5, textAlign: "center", backgroundColor: "#111827" }}>
                                <Typography variant="caption" color="text.secondary">
                                  Snapshot not available
                                </Typography>
                              </Paper>
                            )}
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                              {incident.cameraId} • {incident.type}
                            </Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                    );
                  })}
                </Grid>
              )}
            </Grid>
          </Grid>
        </Container>

        <Dialog open={Boolean(selectedCamera)} onClose={() => setSelectedCamera(null)} maxWidth="lg" fullWidth>
          {selectedCamera && (
            <DialogContent sx={{ p: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
                <Typography variant="h6" fontWeight="bold">
                  {selectedCamera.cameraName}
                </Typography>
                <IconButton onClick={() => setSelectedCamera(null)} size="small" aria-label="close">
                  <CloseIcon />
                </IconButton>
              </Box>
              <CameraHlsPlayer
                hlsUrl={selectedCamera.hlsUrl}
                hasAlert={(cameraState[selectedCamera.cameraIndex]?.alertUntil ?? 0) > Date.now()}
              />
            </DialogContent>
          )}
        </Dialog>

        <Dialog
          open={Boolean(selectedIncidentImage)}
          onClose={() => setSelectedIncidentImage(null)}
          maxWidth="md"
          fullWidth
        >
          {selectedIncidentImage && (
            <DialogContent sx={{ p: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
                <Box>
                  <Typography variant="h6" fontWeight="bold">
                    {selectedIncidentImage.title}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {selectedIncidentImage.subtitle}
                  </Typography>
                </Box>
                <IconButton onClick={() => setSelectedIncidentImage(null)} size="small" aria-label="close">
                  <CloseIcon />
                </IconButton>
              </Box>
              <Box
                component="img"
                src={selectedIncidentImage.url}
                alt={selectedIncidentImage.title}
                sx={{
                  width: "100%",
                  borderRadius: 1,
                  border: "1px solid #263238",
                  backgroundColor: "#000"
                }}
              />
            </DialogContent>
          )}
        </Dialog>
      </Box>
    </ThemeProvider>
  );
}

export default Dashboard;
