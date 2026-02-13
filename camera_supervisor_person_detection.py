import time
import datetime
import sys
import os
import cv2

from ultralytics import YOLO

from pyutils.py_common_includes import *


def send_detect_events(camera_id, password, ip_address, port, stream=1):
    TOPIC_NAME, FRAME_INTERVAL = "DETECT_EVENTS", 3
    DETECT_TIME, NO_DETECT, MESSAGE_INTERVAL = 7, 15, 20

    model = YOLO("yolov8n.pt")
    # Reduce logging noise
    model.verbose = False
    
    url = f"rtsp://{camera_id}:{password}@{ip_address}:{port}/stream{stream}"
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Recording setup
    video_writer = None
    is_recording = False
    recording_start_time = None
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
    os.makedirs(output_dir, exist_ok=True)

    present_count = not_present_count = 0
    last_process_time = last_message_time = time.monotonic()
    person_found = False

    while cap.isOpened():
        current_time = time.monotonic()
        run_detection = (current_time - last_process_time >= FRAME_INTERVAL)

        # Optimize: skip frames if we don't need to detect AND we are not recording
        if not run_detection and not is_recording:
            cap.grab()
            continue

        ret, frame = cap.read()
        if (not ret):
            continue

        # Resize logic (consistent with original)
        frame_h, frame_w = frame.shape[:2]
        new_h = int(frame_h * 640 / frame_w)
        frame = cv2.resize(frame, (640, new_h))
        
        if run_detection:
            last_process_time = current_time
            
            # Detect
            results = model(frame, conf=0.5, verbose=False)
            person_found = any(model.names[int(cls)] == "person"
                               for r in results for cls in r.boxes.cls)

            if person_found:
                present_count += 1
                not_present_count = 0
            else:
                present_count = 0
                not_present_count += 1

            # Message Logic
            if current_time - last_message_time >= MESSAGE_INTERVAL:
                timestamp = datetime.datetime.now().strftime(s_timestamp_format)
                detection_data = {s_detection: False, s_camera_id: camera_id, "updated_at": timestamp}

                if present_count >= DETECT_TIME // FRAME_INTERVAL:
                    detection_data[s_detection] = True
                    msgbroker_publish(topic=TOPIC_NAME, data=detection_data)
                    present_count = 0
                elif not_present_count >= NO_DETECT // FRAME_INTERVAL:
                    msgbroker_publish(topic=TOPIC_NAME, data=detection_data)
                    not_present_count = 0
                last_message_time = current_time

            # Recording Logic
            if person_found and not is_recording:
                is_recording = True
                recording_start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_filename = os.path.join(output_dir, f"person_detect_{recording_start_time}_rec.avi")
                
                fps = cap.get(cv2.CAP_PROP_FPS)
                if not fps or fps > 60: fps = 20.0
                
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                video_writer = cv2.VideoWriter(temp_filename, fourcc, fps, (640, new_h))
                print(f"Recording started: {temp_filename}")
            
            elif not person_found and is_recording:
                is_recording = False
                if video_writer:
                    video_writer.release()
                    video_writer = None
                
                # Rename with end timestamp
                end_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                old_path = os.path.join(output_dir, f"person_detect_{recording_start_time}_rec.avi")
                new_path = os.path.join(output_dir, f"person_detect_{recording_start_time}_to_{end_time}.avi")
                try:
                    os.rename(old_path, new_path)
                    print(f"Recording saved: {new_path}")
                except OSError as e:
                    print(f"Error renaming video file: {e}")

        # Write frame if recording
        if is_recording and video_writer:
            video_writer.write(frame)

        if (cv2.waitKey(1) & (0xFF == ord("q"))):
            break

    if video_writer:
        video_writer.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 person_detection.py <camera_id> <password> <ip_address> <port>")
        sys.exit(1)

    
    if not all([camera_id, password, ip_address, port]):
        print("Error: All arguments must have non-empty values")
        sys.exit(1)

    try:
        send_detect_events(camera_id, password, ip_address, port)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)
