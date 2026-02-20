import cv2
import time
import math
import subprocess
import csv
import mediapipe as mp
from collections import deque
from threading import Thread

# CONFIG + TIMING
W_CAM, H_CAM = 640, 480       
CONFIDENCE_FRAMES = 4        
ACTION_COOLDOWN = 0.7         
VOL_DELAY = 0.15              
SEEK_DELAY = 0.75           

class JetsonCam:
    def __init__(self):
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, W_CAM)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H_CAM)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.grabbed, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            self.grabbed, self.frame = self.cap.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

def send_key(key_command):
    try:
        subprocess.run(["xdotool", "key", key_command])
    except Exception:
        pass

# PIPELINE
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,      
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)
mp_draw = mp.solutions.drawing_utils

def main():
    cam = JetsonCam().start()
    time.sleep(2.0)

    gesture_buffer = deque(maxlen=CONFIDENCE_FRAMES)
    fps_buffer = deque(maxlen=10) 
    
    last_action_time = 0
    last_vol_time = 0
    last_seek_time = 0
    p_time = time.time()

    
    csv_file = open('jetson_performance_data.csv', 'w', newline='')
    writer = csv.writer(csv_file)
    writer.writerow(["Timestamp", "FPS", "Inference_Latency_ms", "Gesture_Detected", "Confidence_Score"])

    while True:
        img = cam.read()
        if img is None: continue
        img = cv2.flip(img, 1)

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        
        inf_start = time.time()
        results = hands.process(img_rgb)
        inf_end = time.time()
        
        inference_ms = (inf_end - inf_start) * 1000

        current_raw_gesture = "NEUTRAL"
        ui_color = (150, 150, 150)
        confidence_score = 0.0 

        if results.multi_hand_landmarks:

            if results.multi_handedness:
                confidence_score = results.multi_handedness[0].classification[0].score

            for hand_lms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                h, w, _ = img.shape
                lm = [[int(l.x * w), int(l.y * h)] for l in hand_lms.landmark]

                fingers = []
                if len(lm) > 20:
                    # SCALE-INVARIANT LOGIC
                 
                    palm_size = math.hypot(lm[0][0]-lm[9][0], lm[0][1]-lm[9][1])
                    
                  thumb_dist = math.hypot(lm[4][0]-lm[17][0], lm[4][1]-lm[17][1])
                    
                    fingers.append(1 if thumb_dist > (palm_size * 0.9) else 0)

                
                    for tip, pip in [(8,6), (12,10), (16,14), (20,18)]:
                        fingers.append(1 if lm[tip][1] < lm[pip][1] else 0)

                    count = fingers.count(1)
                    
                    # MAPPING LOGIC

                    if count == 0: current_raw_gesture = "MUTE"
                    elif count == 1: current_raw_gesture = "VOL UP"
                    elif count == 2: current_raw_gesture = "VOL DOWN"
                    elif count == 3: current_raw_gesture = "SEEK FWD"
                    elif count == 4: current_raw_gesture = "SEEK BWD"
                    elif count == 5: current_raw_gesture = "PLAY/PAUSE"

        # TEMPORAL FILTERING 
        gesture_buffer.append(current_raw_gesture)
        current_stable_gesture = "NEUTRAL"
        
        if gesture_buffer.count(current_raw_gesture) == CONFIDENCE_FRAMES:
            current_stable_gesture = current_raw_gesture
            t = time.time()
            
            if current_stable_gesture in ["PLAY/PAUSE", "MUTE"]:
                if (t - last_action_time) > ACTION_COOLDOWN:
                    if current_stable_gesture == "PLAY/PAUSE":
                        send_key("space")
                        ui_color = (0, 255, 0)
                    elif current_stable_gesture == "MUTE":
                        send_key("m")
                        ui_color = (0, 0, 255)
                    last_action_time = t
                    gesture_buffer.clear() 

            elif current_stable_gesture in ["VOL UP", "VOL DOWN"]:
                if (t - last_vol_time) > VOL_DELAY:
                    send_key("0") if current_stable_gesture == "VOL UP" else send_key("9")
                    ui_color = (0, 255, 255)
                    last_vol_time = t

            elif current_stable_gesture in ["SEEK FWD", "SEEK BWD"]:
                if (t - last_seek_time) > SEEK_DELAY:
                    send_key("Right") if current_stable_gesture == "SEEK FWD" else send_key("Left")
                    ui_color = (255, 0, 255)
                    last_seek_time = t

        # UI & LOGGING 
        c_time = time.time()
        raw_fps = 1 / (c_time - p_time) if p_time > 0 else 0
        p_time = c_time
        fps_buffer.append(raw_fps)
        avg_fps = sum(fps_buffer) / len(fps_buffer)
        
        writer.writerow([time.strftime("%H:%M:%S"), round(avg_fps, 2), round(inference_ms, 2), current_stable_gesture, round(confidence_score, 3)])

        cv2.rectangle(img, (0, 0), (640, 60), (30, 30, 30), -1)
        cv2.putText(img, f"FPS: {int(avg_fps)} | Inf: {int(inference_ms)}ms", (15, 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 2)
        
        if current_stable_gesture != "NEUTRAL":
            cv2.putText(img, f"CMD: {current_stable_gesture}", (320, 40), cv2.FONT_HERSHEY_DUPLEX, 0.8, ui_color, 2)

        cv2.imshow("NVIDIA Jetson TX2 - Touchless HCI", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cam.stop()
    csv_file.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()