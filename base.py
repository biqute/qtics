import time

import serial
from serial.tools import list_ports

ser = None  # Declare ser as a global variable


# This function lists all the ports when called
def list_available_ports():
    # Identify the correct port
    ports = list_ports.comports()
    for port in ports:
        print(port)


# This line actually calls the list ports function to see which ports are there
list_available_ports()


# This function will open the serial port specified.
# The port_name parameter needs to be set to whatever port the synthesizer is connected at which the list_available_ports function will tell you
def open_serial_port(port_name="/dev/bus/usb/003/001", baud_rate=9600, timeout=3.0):
    global ser
    try:
        ser = serial.Serial(port_name, baud_rate, timeout=timeout)
        ser.setDTR(False)
        ser.flushInput()
        ser.setDTR(True)
        print(f"Serial port {port_name} opened successfully.")
        time.sleep(1.0)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")


def close_serial_port():
    global ser
    if ser and ser.is_open:
        ser.close()


# This function sends a command via the serial port specified as an argument in the function call
def send_command(command, delay=0.1):
    global ser
    try:
        # Clear the input buffer
        ser.reset_input_buffer()

        # Send the command with a carriage return
        command_with_cr = f"{command}\r"
        ser.write(command_with_cr.encode())

        # Introduce a delay before reading the response
        time.sleep(delay)

        # Read the response with a timeout
        response_bytes = ser.read(1024)  # Adjust the buffer size as needed

        # Decode and print the response
        response = response_bytes.decode().strip()
        print(f"Response from device: {response}")
    except serial.SerialException as e:
        print(f"Error communicating with the device: {e}")


# Open serial port
open_serial_port()

# Send the STAT command
send_command("STAT\r")

# Sends the ID command
send_command("ID\r")
