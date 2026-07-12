from flask import Flask, jsonify
import RPi.GPIO as GPIO
import time
import multiprocessing
import cv2
import numpy as np

app = Flask(__name__)

# ==========================================
# CONFIG
# ==========================================

PINS_STEPPER = [26, 19, 13, 6]  
PIN_BUTTON = 16
PIN_LIMIT_SWITCH = 2

STEPS_PER_BLOCK = 47      
STEP_DELAY = 0.005         
ACTION_DURATION = 1.0      
TOTAL_INSTRUCTIONS = 10   

STEP_SEQUENCE = [
    [1, 0, 0, 1],  
    [1, 1, 0, 0],  
    [0, 1, 1, 0],  
    [0, 0, 1, 1]   
]

COLORS = {
    1: {"lower": (0, 100, 100),   "upper": (10, 255, 255)},   # Red
    2: {"lower": (110, 100, 100), "upper": (130, 255, 255)},  # Blue
    3: {"lower": (50, 100, 100),  "upper": (70, 255, 255)},   # Green
    4: {"lower": (20, 100, 100),  "upper": (30, 255, 255)},   # Yellow
    5: {"lower": (140, 100, 100), "upper": (160, 255, 255)},  # Purple
    6: {"lower": (10, 100, 100),  "upper": (20, 255, 255)},   # Orange
    7: {"lower": (0, 0, 0),       "upper": (180, 255, 50)},   # Black
    8: {"lower": (0, 0, 200),     "upper": (180, 30, 255)}    # White
}

shared_action = multiprocessing.Value('i', 0)

#icl this is so buns
def setup_gpio():
    print("[DEBUG] Initializing GPIO configurations...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_LIMIT_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print(f"[DEBUG] Inputs Configured - Button Pin: {PIN_BUTTON}, Limit Switch Pin: {PIN_LIMIT_SWITCH}")
    
    for pin in PINS_STEPPER:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    print(f"[DEBUG] Stepper Output Pins Configured: {PINS_STEPPER}")

def move_stepper(steps, direction, current_phase_list):
    dir_str = "FORWARD" if direction == 1 else "BACKWARD"
    print(f"[DEBUG] [MOTOR] Moving {steps} steps {dir_str}...")
    
    for s in range(steps):
        current_phase_list[0] = (current_phase_list[0] + direction) % len(STEP_SEQUENCE)
        phase = current_phase_list[0]
        
        for pin_index, state in enumerate(STEP_SEQUENCE[phase]):
            GPIO.output(PINS_STEPPER[pin_index], state)
            
        time.sleep(STEP_DELAY)
    print(f"[DEBUG] [MOTOR] Finished moving {steps} steps.")

def home_stepper(current_phase_list):
    #debug statements hard carry
    print("[DEBUG] [HOMING] Starting homing sequence...")
    step_count = 0
    while GPIO.input(PIN_LIMIT_SWITCH) == GPIO.HIGH: 
        move_stepper(1, -1, current_phase_list)
        step_count += 1
        if step_count % 50 == 0:
            print(f"[DEBUG] [HOMING] Still searching for limit switch... Steps taken: {step_count}")
    print(f"[DEBUG] [HOMING] Limit switch triggered successfully after {step_count} steps.")

def read_color(camera):
    print("[DEBUG] [CAMERA] Capturing frame...")
    ret, frame = camera.read()
    if not ret:
        print("[DEBUG] [CAMERA] [ERROR] Failed to grab frame from camera.")
        return 0
    
    h, w, _ = frame.shape
    #straight from online tutorial
    roi = frame[h//2-20:h//2+20, w//2-20:w//2+20]
    
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    avg_hsv = np.median(hsv, axis=(0,1))
    print(f"[DEBUG] [CAMERA] Processed ROI Median HSV: H={avg_hsv[0]:.1f}, S={avg_hsv[1]:.1f}, V={avg_hsv[2]:.1f}")
    
    for code, bounds in COLORS.items():
        lower = np.array(bounds["lower"])
        upper = np.array(bounds["upper"])
        if cv2.inRange(np.uint8([[avg_hsv]]), lower, upper)[0][0] == 255:
            print(f"[DEBUG] [CAMERA] Match Found! Code: {code}")
            return code
            
    print("[DEBUG] [CAMERA] No matching color range found. Defaulting to 0.")
    return 0

def scanner_loop_process(action_variable):
    print("[DEBUG] [CORE-2] Hardware Scanner Process Started on separate core.")
    setup_gpio()
    
    print("[DEBUG] [CORE-2] Initializing Camera Interface...")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("[DEBUG] [CORE-2] [CRITICAL] Camera failed to open!")
    
    step_phase_tracker = [0]

    while True:
        if GPIO.input(PIN_BUTTON) == GPIO.LOW:
            print("[DEBUG] [INPUT] Physical Button Press Detected! Launching routine...")
            time.sleep(0.5)
            
            home_stepper(step_phase_tracker)
            
            loop_stack = [] # cs reference???
            current_index = 0
            print(f"[DEBUG] [ROUTINE] Main execution loop started. Target blocks: {TOTAL_INSTRUCTIONS}")
            
            while current_index < TOTAL_INSTRUCTIONS:
                print(f"\n--- [ROUTINE] Processing Block Index: {current_index}/{TOTAL_INSTRUCTIONS-1} ---")
                
                move_stepper(STEPS_PER_BLOCK, 1, step_phase_tracker)
                time.sleep(0.2) 
                
                code = read_color(camera)
                print(f"[DEBUG] [ROUTINE] Index {current_index}: Final read evaluation code: {code}")
                
                if code in [1, 2, 3, 4, 5, 6]:
                    print(f"[DEBUG] [ACTION] Action registered. Setting Shared Value to {code}")
                    with action_variable.get_lock():
                        action_variable.value = code
                    print(f"[DEBUG] [ACTION] Sleeping for ACTION_DURATION ({ACTION_DURATION}s)...")
                    time.sleep(ACTION_DURATION) 
                    
                    with action_variable.get_lock():
                        if action_variable.value == code:
                            action_variable.value = 0
                            print("[DEBUG] [ACTION] Action cleared back to 0 automatically.")
                    
                elif code in [7, 8]:
                    is_loop_end = False
                    if len(loop_stack) > 0 and loop_stack[-1]['type'] == code:
                        is_loop_end = True
                    print(f"[DEBUG] [LOOP] Color evaluates to loop instruction. Is Loop End? {is_loop_end}")
                        
                    if not is_loop_end:
                        print(f"[DEBUG] [LOOP] Loop START ({code}) recorded at block index {current_index}")
                        loop_stack.append({
                            'type': code,
                            'start_index': current_index,
                            'remaining': 5 if code == 8 else 999 
                        })
                        print(f"[DEBUG] [LOOP] Current Stack Depth: {len(loop_stack)}")
                        time.sleep(ACTION_DURATION) 
                    else:
                        loop = loop_stack[-1]
                        loop['remaining'] -= 1
                        print(f"[DEBUG] [LOOP] Loop END detected. Iterations remaining: {loop['remaining']}")
                        
                        if loop['remaining'] > 0:
                            blocks_to_rewind = current_index - loop['start_index']
                            steps_to_rewind = blocks_to_rewind * STEPS_PER_BLOCK
                            print(f"[DEBUG] [LOOP] Loop repeating! Rewinding {blocks_to_rewind} blocks ({steps_to_rewind} steps) back to index {loop['start_index']}")
                            
                            move_stepper(steps_to_rewind, -1, step_phase_tracker)
                            current_index = loop['start_index'] 
                            print(f"[DEBUG] [LOOP] Software counter updated. Next active index will be: {current_index + 1}")
                        else:
                            print("[DEBUG] [LOOP] Termination condition reached. Popping loop from stack.")
                            loop_stack.pop()
                            print(f"[DEBUG] [LOOP] Current Stack Depth: {len(loop_stack)}")
                            
                        time.sleep(ACTION_DURATION)

                current_index += 1
            print("\n[DEBUG] [ROUTINE] Finished all instruction blocks. Awaiting next button event.")
                
        time.sleep(0.1)

@app.route('/consume_action', methods=['GET'])
def get_action():
    with shared_action.get_lock():
        action_to_send = shared_action.value
        shared_action.value = 0 
    
    if action_to_send != 0:
        print(f"[DEBUG] [API] /consume_action called. Dispatched Action: {action_to_send} and flushed data state.")
    return jsonify({"action": action_to_send})

if __name__ == '__main__':
    print("[DEBUG] [MAIN] Booting multi-core setup environment...")
    
    hardware_process = multiprocessing.Process(
        target=scanner_loop_process, 
        args=(shared_action,), 
        daemon=True
    )
    hardware_process.start()
    print(f"[DEBUG] [MAIN] Core 2 process successfully launched with PID: {hardware_process.pid}")

    print("[DEBUG] [MAIN] Deploying API Service on Core 1...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)