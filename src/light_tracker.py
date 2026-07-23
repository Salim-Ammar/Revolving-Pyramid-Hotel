# Light Tracker with PID Control
# This script tracks the brightest spot in the camera feed and controls a motor to align with the light source using a PID controller.
# It uses the Raspberry Pi camera to capture frames and processes them using OpenCV to find the brightest spot.
# The script then sends motor control commands to an Arduino based on the PID calculation.
# A Tkinter GUI displays the camera feed with the detected bright spot.
# Necessary libraries: tkinter, picamera2, cv2, PIL, numpy, serial, time

# Install required libraries:
# pip install picamera2 opencv-python-headless pillow numpy pyserial

import tkinter as tk
from picamera2 import Picamera2
import cv2
from PIL import Image, ImageTk
import numpy as np
import serial
import time

# Initialize the camera
camera = Picamera2()

# Camera configuration for lower resolution
camera_config = camera.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
camera.configure(camera_config)
camera.set_controls({"FrameRate": 30})
camera.start()

# Initialize the serial communication with Arduino
ser = serial.Serial('/dev/ttyACM0', 9600)
time.sleep(2)  # Wait for the serial connection to initialize

# PID controller parameters
Kp = 0.05
Ki = 0.005
Kd = 0.01
integral = 0
previous_error = 0
previous_output = 0
last_direction = None  # Track the last direction sent to the motor

# Function to send commands to Arduino
def send_motor_commands(speed, direction, rolls):
    global last_direction

    # Only send the direction command if it has changed
    if direction != last_direction:
        ser.write(f"D {direction}\n".encode())  # Set direction
        last_direction = direction

    ser.write(f"R {speed}\n".encode())      # Set speed (RPM)
    ser.write(f"S {rolls}\n".encode())      # Set number of rolls
    ser.write("START\n".encode())           # Start the motor

def detect_bright_light(frame):
    """
    Detect the brightest spot in the frame by thresholding the RGB values.
    """
    threshold_value = 253
    mask = cv2.inRange(frame, (threshold_value, threshold_value, threshold_value), (255, 255, 255))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        max_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(max_contour) >= 10:  # Filter out small contours
            x, y, w, h = cv2.boundingRect(max_contour)
            center_x = x + w // 2
            center_y = y + h // 2
            return (x, y, w, h, center_x, center_y)
    
    return None

# Function to update the GUI frame
def update_frame():
    global integral, previous_error, previous_output
    
    try:
        frame = camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        frame = cv2.flip(frame, 1)  # Mirror the frame horizontally
        light_rect = detect_bright_light(frame)

        if light_rect:
            x, y, w, h, center_x, center_y = light_rect
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)  # Draw rectangle around the light
            cv2.putText(frame, f"({center_x}, {center_y})", (center_x, center_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Set the direction based on the light's position in the frame
            if center_x < 320:
                direction = 1  # Clockwise
            else:
                direction = 0  # Counterclockwise

            error = center_x - 320  # Error relative to the center of the frame
            integral += error
            derivative = error - previous_error
            output = Kp * error + Ki * integral + Kd * derivative
            
            # Apply smoothing to the output to reduce jitter
            output = 0.8 * previous_output + 0.2 * output
            previous_output = output

            # Determine speed and rolls
            speed = min(abs(output), 20)  # Clamp the speed to a max of 20 RPM
            rolls = abs(output) / 320  # Rolls proportional to the error (relative to half the frame width)

            if abs(error) > 20:  # If the error is outside the threshold, move the motor
                send_motor_commands(speed, direction, rolls)
            else:
                ser.write("STOP\n".encode())  # Stop the motor if the light is centered

            previous_error = error

        else:
            ser.write("STOP\n".encode())  # Stop the motor if no light is detected

        resized_frame = cv2.resize(frame, (360, 120))
        img = Image.fromarray(resized_frame)
        imgtk = ImageTk.PhotoImage(image=img)
        lmain.imgtk = imgtk
        lmain.configure(image=imgtk)
        
    except Exception as e:
        print(f"Failed to grab frame: {e}")

    lmain.after(10, update_frame)

# Setup the GUI
root = tk.Tk()
root.title("Bright Light Tracker")
lmain = tk.Label(root)
lmain.pack()

# Start the GUI loop
update_frame()
root.mainloop()
