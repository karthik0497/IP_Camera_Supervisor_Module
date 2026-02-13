import cv2,time,subprocess,os,signal,sys,threading
from datetime import datetime
from camera_supervisor_person_detection import send_detect_events




# Check for ONVIF support
try:
    from onvif import ONVIFCamera
    ONVIF_AVAILABLE = True
except ImportError:
    ONVIF_AVAILABLE = False
    print("\n[WARNING] 'onvif-zeep' library not found. ONVIF features (PTZ, Reboot) will be disabled.")
    print("To enable, run: pip install onvif-zeep\n")

class CameraSupervisor:
    def __init__(camera, ip, username, password, camera_port, onvif_port, stream_path):
        camera.ip = ip
        camera.username = username
        camera.password = password
        camera.camera_port = camera_port
        camera.rtsp_url = f"rtsp://{username}:{password}@{ip}:{camera_port}/{stream_path}"  # Format: rtsp://user:pass@ip:port/path
        camera.process = None
        # ONVIF setup
        camera.onvif_port = onvif_port
        camera.camera_control = None    
        camera.media_service = None
        camera.ptz_service = None
        camera.profile_token = profiles[0].token if (camera.media_service and (profiles := camera.media_service.GetProfiles())) else None

        camera.image_dir = "images"
        camera.video_dir = "videos"
        os.makedirs(camera.image_dir, exist_ok=True)
        os.makedirs(camera.video_dir, exist_ok=True)
        print(f"Initialized CameraSupervisor for: {camera.rtsp_url}")
        print(f"Output directories: ./{camera.image_dir}, ./{camera.video_dir}")

    def ping_camera(camera):
        print(f"\n[PING] Testing connection to {camera.ip}...")
        try:
            cap = cv2.VideoCapture(camera.rtsp_url)
            if not cap.isOpened():print("[PING] Failed: Could not open video stream.");return False
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:print("[PING] Success: Camera is ONLINE and streaming.");return True
            else:print("[PING] Failed: Connected but could not read frame.");return False   
        except Exception as e:
            print(f"[PING] Error: {e}")
            return False

    def capture_image(camera, filename=None):
        print(f"\n[IMAGE] Capturing image...")
        if filename is None:filename = os.path.join(camera.image_dir, f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        try:
            cap = cv2.VideoCapture(camera.rtsp_url)
            if not cap.isOpened():print("[IMAGE] Failed: Could not open video stream.");return False
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:cv2.imwrite(filename, frame);print(f"[IMAGE] Success: Image saved to '{filename}'");return True
            else:print("[IMAGE] Failed: Could not read frame.");return False
        except Exception as e:
            print(f"[IMAGE] Error: {e}")
            return False

    def start_video_recording(camera, filename=None, duration=None):
        if camera.process:print("[VIDEO] Error: Recording is already in progress!");return False
        if filename is None:filename = os.path.join(camera.video_dir, f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        print(f"\n[VIDEO] Starting recording to '{filename}'...")
        # FFmpeg command to record RTSP stream to MP4 here used 'copy' for video codec to avoid re-encoding overhead (fastest),we can use 'libx264' (like in the main app) if compatibility issues arise.
        #ffmpeg -y -rtsp_transport tcp -i rtsp://testing_camera_tapoc210:ABCDEFGH@192.168.68.118:554/stream1 -c:v copy -c:a aac -f mp4 output.mp4
        command = ['ffmpeg','-y','-rtsp_transport', 'tcp','-i', camera.rtsp_url,'-c:v', 'copy','-c:a', 'aac','-f', 'mp4',filename]
        if duration:command.insert(1, '-t');command.insert(2, str(duration))
        try:
            camera.process = subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            print(f"[VIDEO] Recording started (PID: {camera.process.pid}).")
            return True
        except FileNotFoundError:
            print("[VIDEO] Error: 'ffmpeg' command not found. Please install ffmpeg.")
            return False
        except Exception as e:
            print(f"[VIDEO] Error starting recording: {e}")
            return False

    def stop_video_recording(camera):
        if not camera.process:print("[VIDEO] No recording in progress.");return
        print("\n[VIDEO] Stopping recording...")
        # Terminate the process gracefully
        try:
            camera.process.terminate()
            # Wait for it to finish safely
            try:
                camera.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("[VIDEO] Process did not exit, killing it...")
                camera.process.kill()
        except Exception as e:
            print(f"[VIDEO] Error stopping process: {e}")
            
        camera.process = None
        print("[VIDEO] Recording stopped.")

    # ---------------- ONVIF METHODS ----------------
    def connect_onvif(camera):
        """Initializes the ONVIF connection."""
        if not ONVIF_AVAILABLE:
            return False
            
        if camera.camera_control:
            return True

        print(f"\n[ONVIF] Connecting to {camera.ip}:{camera.onvif_port}...")
        try:
            camera.camera_control = ONVIFCamera(camera.ip, camera.onvif_port, camera.username, camera.password)
            camera.media_service = camera.camera_control.create_media_service()
            camera.ptz_service = camera.camera_control.create_ptz_service()
            
            # Get Media Profile Token once
            profiles = camera.media_service.GetProfiles()
            if profiles:
                camera.profile_token = profiles[0].token
                
            print("[ONVIF] Connection successful.")
            return True
        except Exception as e:
            print(f"[ONVIF] Connection failed: {e}")
            camera.camera_control = None
            return False

    def move_ptz(camera, x, y, duration=1.0):
        if not camera.connect_onvif() or not camera.profile_token:
            print("[PTZ] Cannot move: No ONVIF connection or Profile Token.")
            return
        print(f"[PTZ] Moving... x={x}, y={y}")
        try:
            request = camera.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = camera.profile_token
            request.Velocity = {'PanTilt': {'x': x, 'y': y}}
            
            camera.ptz_service.ContinuousMove(request)
            time.sleep(duration)
            camera.ptz_service.Stop({'ProfileToken': camera.profile_token, 'PanTilt': True, 'Zoom': True})
            print("[PTZ] Stopped.")
        except Exception as e:
            print(f"[PTZ] Error: {e}")

    def reboot_camera(camera):
        if not camera.connect_onvif():
            print("[REBOOT] Failed: Could not connect to ONVIF service.")
            return False

        print(f"\n[REBOOT] Sending reboot command to {camera.ip}...")
        try:
            device_management = camera.camera_control.create_devicemgmt_service()
            device_management.SystemReboot()
            print(f"[REBOOT] Success: Reboot command sent.")
            return True
        except Exception as e:
            print(f"[REBOOT] Error: {e}")
            return False

    def detect_motion(camera, duration=10):
        print(f"\n[MOTION] Starting motion detection for {duration} seconds...")
        cap = cv2.VideoCapture(camera.rtsp_url)
        
        if not cap.isOpened():
            print("[MOTION] Failed to open stream.")
            return

        start_time = time.time()
        ret, frame1 = cap.read()
        ret, frame2 = cap.read()
        
        motion_count = 0

        while cap.isOpened() and (time.time() - start_time < duration):
            diff = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            motion_detected = False
            for contour in contours:
                if cv2.contourArea(contour) < 900:
                    continue
                motion_detected = True
                
            if motion_detected:
                motion_count += 1
                # print(".", end="", flush=True) # Optional visual indicator

            frame1 = frame2
            ret, frame2 = cap.read()
            if not ret:
                break
        
        cap.release()
        print(f"\n[MOTION] Finished. Motion frames detected: {motion_count}")
        if motion_count > 5: # Threshold
            print("[MOTION] STATUS: Motion Detected!")
        else:
            print(f"[MOTION] STATUS: No significant motion.")

    def view_live_stream(camera):
        print(f"\n[LIVE] Opening live stream from {camera.rtsp_url}...")
        print("[LIVE] Controls:")
        print("  - Press 'q' to close the window.")
        print("  - Press 'c' to capture an image.")
        if ONVIF_AVAILABLE:
            print("  - Press 'w/a/s/d' to move Up/Left/Down/Right.")
        
        cap = cv2.VideoCapture(camera.rtsp_url)
        
        if not cap.isOpened():print("[LIVE] Failed: Could not open video stream.");return

        while True:
            ret, frame = cap.read()
            if not ret:print("[LIVE] Error: Could not read frame.");break
            # Text position (x, y): x is left-margin, y is top-margin (height adjustment)
            cv2.putText(frame, "q: Quit | c: Capture", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            if ONVIF_AVAILABLE:
                cv2.putText(frame, "w/a/s/d: Move Camera", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Live Stream', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):break
            elif key == ord('c'):camera.capture_image()
            if ONVIF_AVAILABLE:
                if key == ord('w'):threading.Thread(target=camera.move_ptz, args=(0, 0.5, 0.5)).start()
                elif key == ord('s'):threading.Thread(target=camera.move_ptz, args=(0, -0.5, 0.5)).start()
                elif key == ord('a'):threading.Thread(target=camera.move_ptz, args=(-0.5, 0, 0.5)).start()
                elif key == ord('d'):threading.Thread(target=camera.move_ptz, args=(0.5, 0, 0.5)).start()
        
        cap.release()
        cv2.destroyAllWindows()
        print("[LIVE] Stream closed.")

    def start_person_detection_recording(camera):
        print(f"\n[DETECT] Starting Person Detection & Recording...")
        print("[DETECT] Press 'q' in the window to stop.")
        
        # Try to extract stream number from stream_path (e.g. "stream1" -> 1)
        # This is a best-effort to match the expected input of send_detect_events
        stream_num = 1
        stream_path = getattr(camera, 'rtsp_url', '').split('/')[-1] # fallback logic
        # Actually camera has no stream_path attribute stored directly in __init__, wait.
        # Line 17: def __init__(camera, ip, username, password, camera_port, onvif_port, stream_path):
        # Line 22: camera.rtsp_url ...
        # It does not store stream_path in self.stream_path. I should rely on the caller or just hardcode/guess.
        # But wait, send_detect_events builds the URL from scratch.
        # Let's extract from the rtsp_url which is stored.
        try:
            import re
            # rtsp_url format: rtsp://user:pass@ip:port/stream_path
            path = camera.rtsp_url.split('/')[-1]
            match = re.search(r'\d+', path)
            if match:
                stream_num = int(match.group())
        except:
            pass

        try:
            # send_detect_events(camera_id, password, ip_address, port, stream=1)
            # using username as camera_id because the function uses it for URL construction
            send_detect_events(camera.username, camera.password, camera.ip, camera.camera_port, stream=stream_num)
        except Exception as e:
            print(f"[DETECT] Error: {e}")


        
