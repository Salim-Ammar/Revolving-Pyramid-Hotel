# Stepper Motor Control GUI
# This script controls a stepper motor using a Tkinter GUI.
# The user can set RPM, position (in degrees), and direction for the motor.
# The script sends commands to an Arduino to control the motor's speed and position.
# Additionally, it calculates and displays the estimated time for the motor to reach the specified position.
# Necessary libraries: tkinter, serial, time

# Install required libraries:
# pip install pyserial

import tkinter as tk
import serial
import time

class MotorControlGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Stepper Motor Control")
        self.serial_conn = serial.Serial('/dev/ttyACM0', 9600, timeout=1)  # Adjust port as needed
        self.serial_conn.flush()

        # Motor parameters
        self.rpm = tk.DoubleVar()
        self.degrees = tk.DoubleVar()
        self.direction = tk.IntVar(value=1)  # 1 for forward, 0 for backward

        # Create GUI components
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.master, text="RPM:").grid(row=0, column=0)
        tk.Entry(self.master, textvariable=self.rpm).grid(row=0, column=1)

        tk.Label(self.master, text="Position (Degrees):").grid(row=1, column=0)
        tk.Entry(self.master, textvariable=self.degrees).grid(row=1, column=1)

        tk.Label(self.master, text="Direction:").grid(row=2, column=0)
        tk.Radiobutton(self.master, text="Forward", variable=self.direction, value=1).grid(row=2, column=1)
        tk.Radiobutton(self.master, text="Backward", variable=self.direction, value=0).grid(row=2, column=2)

        tk.Button(self.master, text="Start", command=self.start_motor).grid(row=3, column=0)
        tk.Button(self.master, text="Stop", command=self.stop_motor).grid(row=3, column=1)
        tk.Button(self.master, text="Calculate Time", command=self.calculate_time).grid(row=4, column=0, columnspan=2)

        self.time_label = tk.Label(self.master, text="")
        self.time_label.grid(row=5, column=0, columnspan=2)

    def send_command(self, command):
        """Send command to Arduino."""
        self.serial_conn.write((command + '\n').encode('utf-8'))
        time.sleep(0.1)  # Small delay to ensure command is sent

    def start_motor(self):
        rpm = self.rpm.get()
        degrees = self.degrees.get()
        direction = self.direction.get()

        # Calculate rolls based on gear ratios
        # small gear ratio: 1, big gear ratio: 10, full step: 6400
        rolls = degrees / 360 * 10  # 10 rolls for 360 degrees of big gear

        self.send_command(f"R {rpm}")
        self.send_command(f"D {1 if degrees >= 0 else 0}")
        self.send_command(f"S {abs(rolls)}")
        self.send_command("START")

    def stop_motor(self):
        self.send_command("STOP")

    def calculate_time(self):
        rpm = self.rpm.get()
        degrees = self.degrees.get()

        # Calculate estimated time (in seconds)
        # 1 roll = 360 degrees on the small gear, so 36 degrees on big gear
        rolls = abs(degrees) / 360 * 10  # Ratio 10 for big gear
        rps = rpm / 60  # Revolutions per second
        estimated_time = rolls / rps if rps != 0 else 0
        self.time_label.config(text=f"Estimated Time: {estimated_time:.2f} seconds")

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorControlGUI(root)
    root.mainloop()
