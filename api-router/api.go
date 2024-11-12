package main

import (
    "io"
    "fmt"
    "context"
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"

    "github.com/gorilla/mux"
    "github.com/gorilla/websocket"
)

type APIRouter struct {
    deviceManagerURL string
    rtmpServerURL    string
    router          *mux.Router
    upgrader        websocket.Upgrader
}

type StreamInfo struct {
    Name       string    `json:"name"`
    Status     string    `json:"status"`
    StartTime  time.Time `json:"start_time,omitempty"`
    Resolution string    `json:"resolution,omitempty"`
    Bitrate    int      `json:"bitrate,omitempty"`
}

type DeviceStatus struct {
    ID       string `json:"id"`
    Type     string `json:"type"`
    Name     string `json:"name"`
    Status   string `json:"status"`
    Address  string `json:"address"`
    LastSeen string `json:"last_seen"`
}

func NewAPIRouter() *APIRouter {
    return &APIRouter{
        deviceManagerURL: os.Getenv("DEVICE_MANAGER_URL"),
        rtmpServerURL:    os.Getenv("RTMP_SERVER_URL"),
        router:          mux.NewRouter(),
        upgrader: websocket.Upgrader{
            CheckOrigin: func(r *http.Request) bool {
                return true // Allow all origins in local network
            },
        },
    }
}

func (ar *APIRouter) SetupRoutes() {
    // Stream management routes
    ar.router.HandleFunc("/api/streams", ar.handleListStreams).Methods("GET")
    ar.router.HandleFunc("/api/streams/{name}", ar.handleStreamControl).Methods("POST")
    ar.router.HandleFunc("/api/streams/{name}/clip", ar.handleCreateClip).Methods("POST")
    
    // Device management routes
    ar.router.HandleFunc("/api/devices", ar.handleListDevices).Methods("GET")
    ar.router.HandleFunc("/api/devices/{id}/reconnect", ar.handleDeviceReconnect).Methods("POST")
    
    // WebSocket for real-time updates
    ar.router.HandleFunc("/ws", ar.handleWebSocket)
    
    // Recording management
    ar.router.HandleFunc("/api/recordings", ar.handleListRecordings).Methods("GET")
    ar.router.HandleFunc("/api/recordings/{id}", ar.handleRecordingOperation).Methods("POST")
}

func (ar *APIRouter) handleListDevices(w http.ResponseWriter, r *http.Request) {
    resp, err := http.Get(fmt.Sprintf("%s/devices", ar.deviceManagerURL))
    if err != nil {
        http.Error(w, "Failed to get devices: "+err.Error(), http.StatusInternalServerError)
        return
    }
    defer resp.Body.Close()

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(resp.StatusCode)
    if _, err := io.Copy(w, resp.Body); err != nil {
        log.Printf("Error copying response: %v", err)
    }
}

func (ar *APIRouter) handleDeviceReconnect(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    deviceID := vars["id"]

    req, err := http.NewRequest("POST", fmt.Sprintf("%s/devices/%s/reconnect", ar.deviceManagerURL, deviceID), r.Body)
    if err != nil {
        http.Error(w, "Failed to create request: "+err.Error(), http.StatusInternalServerError)
        return
    }
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        http.Error(w, "Failed to reconnect device: "+err.Error(), http.StatusInternalServerError)
        return
    }
    defer resp.Body.Close()

    w.WriteHeader(resp.StatusCode)
    if _, err := io.Copy(w, resp.Body); err != nil {
        log.Printf("Error copying response: %v", err)
    }
}

func (ar *APIRouter) handleListRecordings(w http.ResponseWriter, r *http.Request) {
    resp, err := http.Get(fmt.Sprintf("%s/recordings", ar.deviceManagerURL))
    if err != nil {
        http.Error(w, "Failed to get recordings: "+err.Error(), http.StatusInternalServerError)
        return
    }
    defer resp.Body.Close()

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(resp.StatusCode)
    if _, err := io.Copy(w, resp.Body); err != nil {
        log.Printf("Error copying response: %v", err)
    }
}

func (ar *APIRouter) handleRecordingOperation(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    recordingID := vars["id"]

    req, err := http.NewRequest("POST", fmt.Sprintf("%s/recordings/%s", ar.deviceManagerURL, recordingID), r.Body)
    if err != nil {
        http.Error(w, "Failed to create request: "+err.Error(), http.StatusInternalServerError)
        return
    }
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        http.Error(w, "Failed to perform operation on recording: "+err.Error(), http.StatusInternalServerError)
        return
    }
    defer resp.Body.Close()

    w.WriteHeader(resp.StatusCode)
    if _, err := io.Copy(w, resp.Body); err != nil {
        log.Printf("Error copying response: %v", err)
    }
}

func (ar *APIRouter) handleListStreams(w http.ResponseWriter, r *http.Request) {
    // Query RTMP server stats
    streams, err := ar.getRTMPStats()
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    json.NewEncoder(w).Encode(streams)
}

func (ar *APIRouter) handleStreamControl(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    streamName := vars["name"]
    
    var action struct {
        Command string `json:"command"` // start, stop, restart
    }
    
    if err := json.NewDecoder(r.Body).Decode(&action); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // Forward command to device manager
    resp, err := http.Post(
        ar.deviceManagerURL + "/control/" + streamName,
        "application/json",
        r.Body,
    )
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    defer resp.Body.Close()
    
    w.WriteHeader(resp.StatusCode)
}

func (ar *APIRouter) handleCreateClip(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    streamName := vars["name"]
    
    var clipRequest struct {
        Duration int    `json:"duration"`
        Title    string `json:"title,omitempty"`
    }
    
    if err := json.NewDecoder(r.Body).Decode(&clipRequest); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // Forward to device manager
    resp, err := http.Post(
        ar.deviceManagerURL + "/clip/" + streamName,
        "application/json",
        r.Body,
    )
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    defer resp.Body.Close()
    
    w.WriteHeader(resp.StatusCode)
}

func (ar *APIRouter) handleWebSocket(w http.ResponseWriter, r *http.Request) {
    conn, err := ar.upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Printf("Failed to upgrade connection: %v", err)
        return
    }
    defer conn.Close()
    
    // Create a context that's cancelled when the connection closes
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()
    
    // Start status update goroutine
    go ar.streamStatusUpdates(ctx, conn)
}

func (ar *APIRouter) streamStatusUpdates(ctx context.Context, conn *websocket.Conn) {
    ticker := time.NewTicker(time.Second)
    defer ticker.Stop()
    
    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            streams, err := ar.getRTMPStats()
            if err != nil {
                log.Printf("Error getting RTMP stats: %v", err)
                continue
            }
            
            if err := conn.WriteJSON(streams); err != nil {
                log.Printf("Error writing to WebSocket: %v", err)
                return
            }
        }
    }
}

func (ar *APIRouter) getRTMPStats() ([]StreamInfo, error) {
    resp, err := http.Get(ar.rtmpServerURL + "/stat")
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var stats []StreamInfo
    if err := json.NewDecoder(resp.Body).Decode(&stats); err != nil {
        return nil, err
    }
    
    return stats, nil
}

func main() {
    router := NewAPIRouter()
    router.SetupRoutes()
    
    srv := &http.Server{
        Handler:      router.router,
        Addr:         ":8000",
        WriteTimeout: 15 * time.Second,
        ReadTimeout:  15 * time.Second,
    }
    
    log.Printf("Starting API router on :8000")
    log.Fatal(srv.ListenAndServe())
}