# Fire and Emergency Detection System with Telegram Alerts
# This script detects fire and emergency situations using input from an Arduino and sends alerts via Telegram.
# It uses the Raspberry Pi camera to capture images when fire is detected and sends the image to a specified Telegram chat.
# It also continuously monitors for emergency button presses and sends text alerts to Telegram.
# The script includes a Tkinter-based GUI that shows the live camera feed.
# Necessary libraries: serial, tkinter, picamera2, cv2, threading, requests, datetime, os, PIL

# Install required libraries:
# pip install pyserial picamera2 opencv-python-headless requests pillow

import serial
import tkinter as tk
from picamera2 import Picamera2
import cv2
import threading
import requests
from datetime import datetime
import os
from PIL import Image, ImageTk

# Telegram bot details — replace with your own bot token and chat ID
# Get a token from @BotFather on Telegram
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
CHAT_ID = 'YOUR_CHAT_ID'

# Setup serial communication with Arduino
arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

# Initialize the camera
camera = Picamera2()
camera_config = camera.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
camera.configure(camera_config)
camera.set_controls({"FrameRate": 30})
camera.start()

# Function to send text message to Telegram
def send_telegram_text(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    r = requests.post(url, data=data)
    print(f"Telegram response: {r.json()}")

# Function to send image to Telegram
def send_telegram_image(image_path):
    message = 'Fire detected!'
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    files = {'photo': open(image_path, 'rb')}
    data = {'chat_id': CHAT_ID, 'caption': message}
    r = requests.post(url, files=files, data=data)
    print(f"Telegram response: {r.json()}")

# Function to handle fire and emergency button detection
def detection_handler():
    while True:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8').strip()
            if line == "FIRE":
                print("Fire detected! Sending alert to Telegram...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = f"/home/pi/fire_{timestamp}.jpg"
                camera.capture_file(image_path)
                send_telegram_image(image_path)
            elif line == "EMERGENCY":
                print("Emergency button pressed! Sending text alert to Telegram...")
                send_telegram_text("Emergency Alert! A button was pressed.")

# Function to update the GUI with the camera feed
def update_frame():
    frame = camera.capture_array()
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    img = Image.fromarray(frame)
    imgtk = ImageTk.PhotoImage(image=img)
    lmain.imgtk = imgtk
    lmain.configure(image=imgtk)
    lmain.after(10, update_frame)

# Setup the GUI
root = tk.Tk()
root.title("Fire and Emergency Detection System")

lmain = tk.Label(root)
lmain.pack()

# Start the detection handler thread
thread = threading.Thread(target=detection_handler)
thread.daemon = True
thread.start()

# Start the GUI loop
update_frame()
root.mainloop()
