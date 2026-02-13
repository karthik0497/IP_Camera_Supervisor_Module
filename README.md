# Smart Camera Supervisor & AI Surveillance System | Python, OpenCV, YOLOv8, ONVIF, MQTT

## Automated AI Surveillance System
Designed and built a Python-based camera supervisor service for automated security monitoring. The system ingests RTSP feeds from networked cameras and utilizes YOLO models to detect human presence in real-time. Key features include intelligent bandwidth management (skipping frames when idle), automated event-triggered video recording, and full PTZ control via ONVIF integration. The solution serves as a central hub for smart security logic, bridging raw video feeds with actionable alert systems.

### Key Features
*   **Smart Camera Supervisor & AI Surveillance System:** Developed a comprehensive camera management system capable of handling multiple RTSP streams for real-time surveillance.
*   **Real-time Detection:** Integrated YOLOv8 for real-time person detection, implementing logic to automatically trigger video recording and save timestamped footage upon detection.
*   **Remote PTZ Control:** Implemented ONVIF protocol support to enable remote PTZ (Pan-Tilt-Zoom) control and device management (reboot/reset) directly from the application.
*   **Event-Driven Architecture:** Designed an event-driven architecture using MQTT to publish detection alerts and coordinate actions between microservices.
*   **Diagnostic Tools:** Built a CLI-based diagnostic tool for testing stream latency, connection stability, and verifying AI inference performance.

## Technical Deep Dive: Camera Supervisor Module
*   **Core Logic:** Threaded application managing connection state and health checks for IP cameras.
*   **Computer Vision:** Utilized ultralytics (YOLO) and OpenCV to perform inference on video frames, filtering for specific classes (e.g., "person") to minimize false positives.
*   **Automation:** Engineered "smart recording" logic that buffers and writes video to disk only when specific objects are detected, optimizing storage usage.
*   **IoT Protocols:** Implemented onvif-zeep for hardware control and standard RTSP libraries for low-latency streaming.
*   **Architecture:** Modular design with separate handlers for video acquisition, event processing, and external communication.

### Technologies
*   **Languages/Libraries:** Python, OpenCV (cv2), YOLOv8, NumPy, FFMPEG, ONVIF.
*   **Concepts:** Computer Vision, Object Detection, RTSP Streaming, Event-Driven Architecture, IoT, Real-time Processing.

---

## Setup & Installation

1.  **Create Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r camera_supervisor_requirements.txt
    ```

---

## Legacy Documentation & Usage

### Protocols Used

This tool leverages two primary protocols to interact with the camera:

#### 1. RTSP (Real-Time Streaming Protocol)
*   **Purpose**: Used for all video-related operations, including live viewing, recording, and image analytics.
*   **Implementation**: 
    *   **Live View & Capture**: Uses `opencv-python` (`cv2.VideoCapture`) to decode the RTSP stream directly.
    *   **Recording**: Uses `ffmpeg` (via `subprocess`) to copy the RTSP stream directly to an MP4 container without re-encoding, ensuring low CPU usage.
*   **Default Connection String**: `rtsp://<username>:<password>@<ip>:<port>/<stream_path>`

#### 2. ONVIF (Open Network Video Interface Forum)
*   **Purpose**: Used for camera control commands, specifically PTZ (Pan, Tilt, Zoom) movements.
*   **Implementation**: Uses the `onvif-zeep` Python library to communicate with the camera's ONVIF service.
*   **Port**: Defaults to port `2020` (can be customized).
*   **Features**: Enables the script to send `ContinuousMove` commands (PTZ) and `SystemReboot` commands to connected cameras.

---

### Running the Supervisor (CLI)

```bash
python camera_supervisor.py <ip> <username> <password>
```

**Example:**
```bash
python camera_supervisor.py 192.168.68.118 testing_camera_tapoc210 ABCDEFGH
```

### Menu Options & Workflow

#### Core Functions

1.  **Ping Camera (Check Connection)**
2.  **Capture Single Image**
3.  **Start Video Recording**
4.  **Stop Video Recording**
5.  **Check Motion Detection (10s)**
6.  **View Live Stream with ONVIF CONTROLS (PTZ)**

#### ONVIF Controls 

7.  **[ONVIF] Move Left**
8.  **[ONVIF] Move Right**
9.  **[ONVIF] Move Up**
10. **[ONVIF] Move Down**
11. **[ONVIF] Reboot Camera**

---

### Camera Supervisor Event Handler

This is the background service that automates camera operations based on MQTT messages.

#### What It Does
*   **Listens**: Subscribes to MQTT topics for real-time commands.
*   **Manages**: Controls multiple cameras simultaneously using a single configuration file (`data/camera_config.yml`).
*   **Executes**: Triggers recording, snapshots, and PTZ movements via the Supervisor component.
*   **Uploads**: Automatically uploads captured files to S3 (or local storage) and updates the API with the file URL.

#### Supported Events
1.  **`start_record`**: Begins video recording for a specified duration.
2.  **`stop_record`**: Stops recording, renames the file, and initiates upload.
3.  **`capture_snap`**: Takes an instant snapshot and uploads it.
4.  **`reposition_camera`**: Moves the camera to a predefined coordinate profile (x, y).
5.  **`reboot_camera`**: Remotely reboots the camera device.

#### Workflow
1.  **Receive**: MQTT message arrives -> Parsed by Handler.
2.  **Action**: Handler calls `CameraSupervisor` to perform the task (e.g., start ffmpeg).
3.  **Process**: File is generated (video/image).
4.  **Upload**: File is uploaded to S3 bucket or local storage.
5.  **Notify**: API is updated with the new file URL and status.
