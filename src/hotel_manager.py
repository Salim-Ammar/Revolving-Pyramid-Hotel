# This script implements a hotel management system using face recognition.
# It uses the Raspberry Pi camera for live face detection and recognizes stored faces.
# The system interacts with customers through a Tkinter-based GUI, allowing booking, check-in, and check-out functionalities.
# The script also interfaces with an Arduino via serial communication to handle check-in and check-out with an RFID card.
# The face data and booking history are stored using pickle and JSON files.
# Necessary libraries: cv2, pickle, numpy, face_recognition, picamera2, tkinter, PIL, threading, time, uuid, json, serial

# Install required libraries:
# pip install opencv-python-headless numpy face_recognition picamera2 pillow pyserial

import cv2
import pickle
import numpy as np
import face_recognition
from picamera2 import Picamera2
import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import time
import uuid
import json
import serial

# Initialize the camera
camera = Picamera2()
camera_config = camera.create_preview_configuration(main={"size": (480, 360), "format": "RGB888"})
camera.configure(camera_config)
camera.set_controls({"FrameRate": 30})
camera.start()

# Initialize Serial Communication with Arduino
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)  # Adjust the port name as necessary
ser.flush()

# Load known faces and names
try:
    with open("face_data.pkl", "rb") as f:
        known_face_encodings, known_face_names = pickle.load(f)
except (FileNotFoundError, EOFError, ValueError):
    known_face_encodings = []
    known_face_names = []

# Load booking data
try:
    with open("booking_data.json", "r") as f:
        booking_history = json.load(f)
except (FileNotFoundError, EOFError, ValueError):
    booking_history = {}

# Initialize the Tkinter GUI
root = tk.Tk()
root.title("Advanced Hotel Management System")
root.geometry("1200x800")

# Style the GUI
style = ttk.Style()
style.configure("TLabel", font=("Helvetica", 12))
style.configure("TButton", font=("Helvetica", 12), padding=10)
style.configure("TFrame", padding=10)
style.configure("TEntry", font=("Helvetica", 12), padding=5)
style.configure("TNotebook", font=("Helvetica", 12))
style.configure("TNotebook.Tab", font=("Helvetica", 12))

# Main frame
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True)

label = ttk.Label(main_frame)
label.pack()

notebook = ttk.Notebook(main_frame)
notebook.pack(fill='both', expand=True)

# Tabs
reception_tab = ttk.Frame(notebook)
booking_tab = ttk.Frame(notebook)
checkin_tab = ttk.Frame(notebook)
checkout_tab = ttk.Frame(notebook)
status_tab = ttk.Frame(notebook)
faces_tab = ttk.Frame(notebook)
unknown_faces_tab = ttk.Frame(notebook)

notebook.add(reception_tab, text="Reception")
notebook.add(booking_tab, text="Booking")
notebook.add(checkin_tab, text="Check-in")
notebook.add(checkout_tab, text="Check-out")
notebook.add(status_tab, text="Status")
notebook.add(faces_tab, text="Faces")
notebook.add(unknown_faces_tab, text="Unknown Faces")

# Room and booking management
rooms = {
    '101': {'type': 'Single', 'price': 100, 'available': True, 'features': 'Single Bed, Free Wi-Fi, TV'},
    '102': {'type': 'Single', 'price': 100, 'available': True, 'features': 'Single Bed, Free Wi-Fi, TV'},
    '103': {'type': 'Single', 'price': 100, 'available': True, 'features': 'Single Bed, Free Wi-Fi, TV'},
    '201': {'type': 'Double', 'price': 150, 'available': True, 'features': 'Double Bed, Free Wi-Fi, TV, Mini Bar'},
    '202': {'type': 'Double', 'price': 150, 'available': True, 'features': 'Double Bed, Free Wi-Fi, TV, Mini Bar'},
    '203': {'type': 'Double', 'price': 150, 'available': True, 'features': 'Double Bed, Free Wi-Fi, TV, Mini Bar'},
    '301': {'type': 'Suite', 'price': 200, 'available': True, 'features': 'Suite, Free Wi-Fi, TV, Mini Bar, Balcony'},
    '302': {'type': 'Suite', 'price': 200, 'available': True, 'features': 'Suite, Free Wi-Fi, TV, Mini Bar, Balcony'},
    '303': {'type': 'Suite', 'price': 200, 'available': True, 'features': 'Suite, Free Wi-Fi, TV, Mini Bar, Balcony'}
}

# Store last detected times for known faces
recently_detected_faces = {}
detection_cooldown = 30  # seconds to avoid repeating the same face prompt

# State management
unknown_face_encodings = []
unknown_face_images = []
processing_new_face = False
checked_in_customers = {}  # Dictionary to track checked-in customers

# Define payment method
def process_payment(name, amount):
    # Simulate payment processing
    messagebox.showinfo("Payment Processed", f"{name}, your payment of ${amount} has been processed successfully!")

def add_new_face(face_encoding, face_image):
    global unknown_face_encodings, unknown_face_images
    unknown_face_encodings.append(face_encoding)
    unknown_face_images.append(face_image)
    update_unknown_faces_tab()

def name_unknown_face(index):
    global processing_new_face
    name = simpledialog.askstring("Input", "Enter the name of the person:", parent=root)
    if name:
        known_face_encodings.append(unknown_face_encodings[index])
        known_face_names.append(name)
        del unknown_face_encodings[index]
        del unknown_face_images[index]
        with open("face_data.pkl", "wb") as f:
            pickle.dump((known_face_encodings, known_face_names), f)
        update_faces_tab()
        update_unknown_faces_tab()
        update_reception_tab()
    # Unfreeze the camera
    processing_new_face = False
    root.after(10, update_frame)

def handle_unknown_face(face_encoding, face_image):
    if not any(np.array_equal(face_encoding, unknown_face) for unknown_face in unknown_face_encodings):
        add_new_face(face_encoding, face_image)
        return True  # Return True to indicate a new unknown face was detected
    return False  # Return False if the face is already known

def show_reservation_details(name):
    reservation_info = f"Hello, {name}! Welcome to our hotel.\n"
    reservation_info += "Here are the available rooms and prices:\n"

    for room, details in rooms.items():
        status = "Available" if details['available'] else "Booked"
        reservation_info += f"Room {room}: {details['type']} - ${details['price']} ({status})\nFeatures: {details['features']}\n"

    messagebox.showinfo("Reservation Details", reservation_info)

def book_room(name, room_number):
    if rooms[room_number]['available']:
        rooms[room_number]['available'] = False
        booking_id = str(uuid.uuid4())
        booking_history[booking_id] = {'name': name, 'room': room_number, 'price': rooms[room_number]['price']}
        with open("booking_data.json", "w") as f:
            json.dump(booking_history, f)
        messagebox.showinfo("Booking Successful", f"Room {room_number} booked successfully for {name}.")
        process_payment(name, rooms[room_number]['price'])
        send_notification(name, room_number, booking_id)
        update_status_tab()
        update_booking_tab()
    else:
        messagebox.showerror("Booking Error", f"Room {room_number} is already booked.")

def handle_reservation(name):
    if not messagebox.askyesno("Reservation", f"{name}, would you like to make a reservation?"):
        messagebox.showinfo("Thank You", "Feel free to explore other facilities!")
        return

    reservation_window = tk.Toplevel(root)
    reservation_window.title("Make a Reservation")

    tk.Label(reservation_window, text=f"Welcome {name}! Please select a room to book.").pack()

    for room, details in rooms.items():
        if details['available']:
            tk.Button(reservation_window, text=f"Book Room {room} (${details['price']})",
                      command=lambda r=room: [book_room(name, r), reservation_window.destroy()]).pack()

def send_notification(name, room_number, booking_id):
    # Simulate sending an email or SMS notification
    notification_message = f"Notification sent to {name}: Your room {room_number} is booked successfully. Booking ID: {booking_id}"
    messagebox.showinfo("Notification", notification_message)

def update_frame():
    global processing_new_face
    if processing_new_face:
        return  # Skip updating the frame if processing a new face

    frame = camera.capture_array()
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    detected_names = []

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        if matches and known_face_encodings:  # Check if known_face_encodings is not empty
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]

        if name == "Unknown":
            face_location = face_recognition.face_locations(rgb_frame, model="cnn")[0]
            face_image = rgb_frame[face_location[0]:face_location[2], face_location[3]:face_location[1]]
            if handle_unknown_face(face_encoding, face_image):
                processing_new_face = True
                return  # Exit update_frame to process the new face

        detected_names.append(name)

    for face_encoding, face_location, name in zip(face_encodings, face_locations, detected_names):
        top, right, bottom, left = face_location
        cv2.rectangle(rgb_frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.rectangle(rgb_frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(rgb_frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    img = Image.fromarray(rgb_frame)
    imgtk = ImageTk.PhotoImage(image=img)
    label.imgtk = imgtk
    label.configure(image=imgtk)

    # Process the next frame
    root.after(10, update_frame)

def update_reception_tab():
    for widget in reception_tab.winfo_children():
        widget.destroy()

    tk.Label(reception_tab, text="Reception - Serve Guests", font=("Helvetica", 16)).pack()

    if not known_face_names:
        tk.Label(reception_tab, text="No known faces stored.", font=("Helvetica", 12)).pack()
        return

    for name in known_face_names:
        frame = ttk.Frame(reception_tab)
        frame.pack(fill='x', padx=5, pady=5)
        tk.Label(frame, text=name, font=("Helvetica", 12)).pack(side='left')
        tk.Button(frame, text="Serve", command=lambda n=name: [show_reservation_details(n), handle_reservation(n)]).pack(side='right')

def update_faces_tab():
    for widget in faces_tab.winfo_children():
        widget.destroy()

    tk.Label(faces_tab, text="Stored Faces:", font=("Helvetica", 14)).pack()

    if not known_face_names:
        tk.Label(faces_tab, text="No faces stored.", font=("Helvetica", 12)).pack()
        return

    for name in known_face_names:
        frame = ttk.Frame(faces_tab)
        frame.pack(fill='x', padx=5, pady=5)
        tk.Label(frame, text=name, font=("Helvetica", 12)).pack(side='left')
        tk.Button(frame, text="Delete", command=lambda n=name: delete_face(n)).pack(side='right')

def update_unknown_faces_tab():
    for widget in unknown_faces_tab.winfo_children():
        widget.destroy()

    canvas = tk.Canvas(unknown_faces_tab)
    scrollbar = ttk.Scrollbar(unknown_faces_tab, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    tk.Label(scrollable_frame, text="Unknown Faces:", font=("Helvetica", 14)).pack()

    if not unknown_face_images:
        tk.Label(scrollable_frame, text="No unknown faces detected.", font=("Helvetica", 12)).pack()
        return

    for index, face_image in enumerate(unknown_face_images):
        frame = ttk.Frame(scrollable_frame)
        frame.pack(fill='x', padx=5, pady=5)
        im = Image.fromarray(face_image)
        imgtk = ImageTk.PhotoImage(image=im)
        panel = tk.Label(frame, image=imgtk)
        panel.image = imgtk
        panel.pack(side='left')
        tk.Button(frame, text=f"Name Unknown {index + 1}", command=lambda idx=index: name_unknown_face(idx)).pack(side='right')

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

def delete_face(name):
    index = known_face_names.index(name)
    del known_face_encodings[index]
    del known_face_names[index]
    with open("face_data.pkl", "wb") as f:
        pickle.dump((known_face_encodings, known_face_names), f)
    update_faces_tab()
    update_reception_tab()

def update_booking_tab():
    booking_text.config(state=tk.NORMAL)
    booking_text.delete(1.0, tk.END)
    for booking_id, details in booking_history.items():
        booking_text.insert(tk.END, f"Booking ID: {booking_id}\nName: {details['name']}\nRoom: {details['room']}\nPrice: ${details['price']}\n\n")
    booking_text.config(state=tk.DISABLED)

def reset_booking():
    global booking_history
    booking_history = {}
    with open("booking_data.json", "w") as f:
        json.dump(booking_history, f)
    messagebox.showinfo("Reset Booking", "All booking data has been reset.")
    update_booking_tab()

def update_status_tab():
    status_text.config(state=tk.NORMAL)
    status_text.delete(1.0, tk.END)
    for room, details in rooms.items():
        status = "Available" if details['available'] else "Booked"
        status_text.insert(tk.END, f"Room {room}: {details['type']} - ${details['price']} ({status})\nFeatures: {details['features']}\n\n")
    status_text.config(state=tk.DISABLED)

def handle_checkin():
    active_customers = [details['name'] for details in booking_history.values() if details['name'] not in checked_in_customers]
    if not active_customers:
        messagebox.showerror("No Active Customers", "There are no customers ready for check-in.")
        return

    customer_name = simpledialog.askstring("Check-in", f"Which customer wants to check in?\nActive customers: {', '.join(active_customers)}", parent=root)
    
    if customer_name not in active_customers:
        messagebox.showerror("Error", "Invalid customer name or customer has already checked in.")
        return

    messagebox.showinfo("Check-in", "Please sweep your card.")
    
    try:
        ser.write(b"check-in\n")
    except serial.SerialException as e:
        messagebox.showerror("Serial Communication Error", f"Failed to communicate with the Arduino: {e}")
        return

    # Wait for the RFID scan to succeed
    rfid_tag = None
    while True:
        try:
            rfid_tag = ser.readline().decode('utf-8').strip()
        except serial.SerialException as e:
            messagebox.showerror("Serial Communication Error", f"Failed to read from Arduino: {e}")
            return

        if rfid_tag and rfid_tag != "No RFID Card Detected":
            break
        elif rfid_tag == "No RFID Card Detected":
            messagebox.showinfo("Check-in", "No card detected. Please sweep your card again.")
            try:
                ser.write(b"check-in\n")
            except serial.SerialException as e:
                messagebox.showerror("Serial Communication Error", f"Failed to communicate with the Arduino: {e}")
                return

    checked_in_customers[customer_name] = rfid_tag
    messagebox.showinfo("Check-in", f"Check-in succeeded for {customer_name}.")

def handle_checkout():
    active_customers = list(checked_in_customers.keys())
    if not active_customers:
        messagebox.showerror("No Active Customers", "There are no customers ready for check-out.")
        return

    customer_name = simpledialog.askstring("Check-out", f"Which customer wants to check out?\nActive customers: {', '.join(active_customers)}", parent=root)

    if customer_name not in active_customers:
        messagebox.showerror("Error", "Invalid customer name or customer has not checked in.")
        return

    messagebox.showinfo("Check-out", "Please sweep your card.")
    ser.write(b"check-out\n")

    # Wait for the RFID scan to succeed
    rfid_tag = None
    while True:
        rfid_tag = ser.readline().decode('utf-8').strip()
        if rfid_tag and rfid_tag != "No RFID Card Detected":
            break
        elif rfid_tag == "No RFID Card Detected":
            messagebox.showinfo("Check-out", "No card detected. Please sweep your card again.")
            ser.write(b"check-out\n")

    if rfid_tag == checked_in_customers[customer_name]:
        del checked_in_customers[customer_name]
        messagebox.showinfo("Check-out", f"Check-out succeeded for {customer_name}.")
    else:
        messagebox.showerror("Error", "Failed to check out. Please try again.")

# Reception Tab Content
tk.Label(reception_tab, text="Reception Management", font=("Helvetica", 16)).pack()
update_reception_tab()

# Booking Tab Content
tk.Label(booking_tab, text="Booking Management", font=("Helvetica", 16)).pack()
booking_text = tk.Text(booking_tab, height=20, width=80)
booking_text.pack()
booking_text.config(state=tk.DISABLED)
update_booking_tab()
tk.Button(booking_tab, text="Reset Booking", command=reset_booking).pack()

# Check-in Tab Content
tk.Label(checkin_tab, text="Check-in Management", font=("Helvetica", 16)).pack()
tk.Button(checkin_tab, text="Check-in", command=handle_checkin).pack()

# Check-out Tab Content
tk.Label(checkout_tab, text="Check-out Management", font=("Helvetica", 16)).pack()
tk.Button(checkout_tab, text="Check-out", command=handle_checkout).pack()

# Status Tab Content
tk.Label(status_tab, text="Room Status", font=("Helvetica", 16)).pack()
status_text = tk.Text(status_tab, height=20, width=80)
status_text.pack()
status_text.config(state=tk.DISABLED)
update_status_tab()

# Faces Tab Content
update_faces_tab()

# Unknown Faces Tab Content
update_unknown_faces_tab()

# Start updating the frame
update_frame()

# Run the Tkinter main loop
root.mainloop()
