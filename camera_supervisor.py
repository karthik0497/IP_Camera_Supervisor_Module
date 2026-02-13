from camera_supervisor_helper import *
from camera_supervisor_components import *
from camera_supervisor_constants import *

def main():
    print("==========================================")
    print("   Camera Supervisor - Simple Tester      ")
    print("==========================================")
    
    camera_data = load_data_from_yaml(CAMERA_CONFIG_PATH)
    
    # Defaults
    d_ip, d_user, d_pass, d_onvif, d_stream, d_port = None, None, None, 2020, "stream1", 554

    if camera_data and "camera_details" in camera_data:
        try:
            target_key = "test_Shuttle_1" # Default to this specific camera for testing
            
            if target_key in camera_data["camera_details"]:
                cam_key = target_key
            else:
                cam_key = next(iter(camera_data["camera_details"]))
                
            cam_conf = camera_data["camera_details"][cam_key]
            d_ip = cam_conf.get("camera_ip")
            d_user = cam_conf.get("camera_username")
            d_pass = cam_conf.get("camera_password")
            d_onvif = cam_conf.get("onvif_port", 2020)
            d_stream = cam_conf.get("stream_path", "stream1")
            d_port = cam_conf.get("camera_port", 554)
            print(f"Loaded defaults from camera: {cam_key}")
        except Exception as e:
            print(f"Error reading defaults from config: {e}")
    else:
        print("Failed to load camera data from YAML file or no 'camera_details' found.")

    # 1. Configuration
    print("\nPlease enter camera details:")
    ip = get_input("Camera IP", d_ip)
    user = get_input("Username", d_user)
    pwd = get_input("Password", d_pass)
    onvif_p = get_input("ONVIF Port", d_onvif)
    stream = get_input("Stream Path", d_stream)
    camera_p = get_input("Camera Port", d_port)
    
    tester = CameraSupervisor(ip, user, pwd, camera_port=int(camera_p), onvif_port=int(onvif_p), stream_path=stream)
    
    # 2. Interactive Menu
    while True:
        print("\n---------------- MENU ----------------")
        print("1. Ping Camera (Check Connection)")
        print("2. Capture Single Image")
        print("3. Start Video Recording")
        print("4. Stop Video Recording")
        print("5. Check Motion Detection (10s)")
        print("6. View Live Stream")
        if ONVIF_AVAILABLE:
            print("7. [ONVIF] Move Left")
            print("8. [ONVIF] Move Right")
            print("9. [ONVIF] Move Up")
            print("10. [ONVIF] Move Down")
            print("11. [ONVIF] Reboot Camera")
        print("12. Start Person Detection & Recording")
        print("0. Exit")
        print("--------------------------------------")
        
        choice = input("Select an option: ")
        
        if choice == '1':
            tester.ping_camera()
            
        elif choice == '2':
            tester.capture_image()
            
        elif choice == '3':
            dur = input("Enter duration in seconds (leave empty for manual stop): ")
            duration = int(dur) if dur.isdigit() else None
            tester.start_video_recording(duration=duration)
            
        elif choice == '4':
            tester.stop_video_recording()

        elif choice == '5':
            tester.detect_motion(duration=10)

        elif choice == '6':
            tester.view_live_stream()

        elif choice == '0':
            if tester.process:
                tester.stop_video_recording()
            print("Exiting...")
            break
            
        elif choice == '12':
            tester.start_person_detection_recording()

        # ONVIF Controls
        elif ONVIF_AVAILABLE:
            if choice == '7': tester.move_ptz(-0.5, 0) # Left
            elif choice == '8': tester.move_ptz(0.5, 0)  # Right
            elif choice == '9': tester.move_ptz(0, 0.5)  # Up
            elif choice == '10': tester.move_ptz(0, -0.5) # Down
            elif choice == '11': tester.reboot_camera() # Reboot
            else: print("Invalid ONVIF option.")
            
        else:
            print("Invalid selection. Try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
