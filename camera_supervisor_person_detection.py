import time
import datetime
import sys
import os
import cv2
from ultralytics import YOLO

def send_detect_events(camera_id, password, ip_address, port, stream=1):
    # Constants
    FRAME_SKIP = 3  # Run detection every N frames to save CPU
    
    print(f"Starting detection on rtsp://{camera_id}:***@{ip_address}:{port}/stream{stream}")
    
    try:
        model = YOLO("yolov8n.pt")
        model.verbose = False
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        return

    url = f"rtsp://{camera_id}:{password}@{ip_address}:{port}/stream{stream}"
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cap.isOpened():
        print(f"Error: Could not open video stream at {url}")
        return

    # Output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
    os.makedirs(output_dir, exist_ok=True)

    # State variables
    video_writer = None
    is_recording = False
    recording_start_time = None
    frame_count = 0
    person_found = False

    print("Detection loop started. Press 'q' to stop.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Stream ended or failed to read frame.")
            break

        # Resize for consistent processing speed
        frame_h, frame_w = frame.shape[:2]
        new_h = int(frame_h * 640 / frame_w)
        frame = cv2.resize(frame, (640, new_h))
        
        # Run detection only every FRAME_SKIP frames
        frame_count += 1
        if frame_count % FRAME_SKIP == 0:
            results = model(frame, conf=0.5, verbose=False)
            
            # Check for person class (Class ID 0 in COCO dataset)
            person_found = False
            for r in results:
                for cls in r.boxes.cls:
                    if int(cls) == 0:  # 0 is 'person'
                        person_found = True
                        break
        
        # --- Recording Logic ---
        if person_found and not is_recording:
            is_recording = True
            recording_start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"person_detect_{recording_start_time}_rec.avi")
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
            if fps > 60: fps = 20.0
            
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            video_writer = cv2.VideoWriter(filename, fourcc, fps, (640, new_h))
            print(f"[REC] Started: {filename}")
        
        elif not person_found and is_recording:
            is_recording = False
            if video_writer:
                video_writer.release()
                video_writer = None
            
            # Rename file to include end time
            end_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            old_path = os.path.join(output_dir, f"person_detect_{recording_start_time}_rec.avi")
            new_path = os.path.join(output_dir, f"person_detect_{recording_start_time}_to_{end_time}.avi")
            try:
                os.rename(old_path, new_path)
                print(f"[REC] Saved: {new_path}")
            except OSError:
                pass # safely ignore if rename fails, original file still exists

        # Write frame if recording
        if is_recording and video_writer:
            video_writer.write(frame)
            # Add visual indicator on the frame
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1) # Red dot
            cv2.putText(frame, "REC", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Show frame
        cv2.imshow("Person Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    if video_writer:
        video_writer.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 person_detection.py <camera_id> <password> <ip_address> <port>")
        sys.exit(1)
    
    try:
        send_detect_events(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)
