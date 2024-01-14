
# Imports
import pyaudio
import numpy as np
from openwakeword.model import Model
import argparse
import socket
import threading
import time
import RPi.GPIO as GPIO
# Sender configuration
SENDER_HOST = '0.0.0.0'  # Host IP
SENDER_PORT = 12345     # Port for sender
RECEIVER_IP = '192.168.29.183'  # Receiver's IP address
RECEIVER_PORT = 12346   # Port for receiver
server_ip = '192.168.29.183'  # Raspberry Pi's IP address
server_port = 12356




GPIO.setmode(GPIO.BCM)
gpio_pin = 17  # Change this to the actual GPIO pin number you're using
GPIO.setup(gpio_pin, GPIO.OUT)

# Parse input arguments
parser=argparse.ArgumentParser()
parser.add_argument(
    "--chunk_size",
    help="How much audio (in number of samples) to predict on at once",
    type=int,
    default=1280,
    required=False
)
parser.add_argument(
    "--model_path",
    help="The path of a specific model to load",
    type=str,
    default="",
    required=False
)
parser.add_argument(
    "--inference_framework",
    help="The inference framework to use (either 'onnx' or 'tflite'",
    type=str,
    default='tflite',
    required=False
)
# Set up sender and receiver sockets
sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiver_socket.bind((SENDER_HOST, RECEIVER_PORT))
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

args=parser.parse_args()
audio = pyaudio.PyAudio()
MAX_PACKET_SIZE = 4096  # Maximum size of each packet

# Get microphone stream
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = args.chunk_size
audio = pyaudio.PyAudio()
mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

# Load pre-trained openwakeword models
if args.model_path != "":
    owwModel = Model(wakeword_models=[args.model_path], inference_framework=args.inference_framework)
else:
    owwModel = Model(inference_framework=args.inference_framework)

n_models = len(owwModel.models.keys())


server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('0.0.0.0', 12356))  # Change the port if needed
sender_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
receiver_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

def send_audio():
    while True:
        if True:
            data = sender_stream.read(CHUNK)
            for i in range(0, len(data), MAX_PACKET_SIZE):
                chunk = data[i:i+MAX_PACKET_SIZE]
                sender_socket.sendto(chunk, (RECEIVER_IP, RECEIVER_PORT))

# def receive_audio():
#     while True:
#         data, _ = receiver_socket.recvfrom(MAX_PACKET_SIZE)
#         receiver_stream.write(data)
def receive_audio():
    while True:
        data, _ = receiver_socket.recvfrom(MAX_PACKET_SIZE)

        # Feed received audio to openWakeWord model
        prediction = owwModel.predict(np.frombuffer(data, dtype=np.int16))

        # Check if the wake word "Alexa" is detected
        if prediction['alexa'] > 0.3:  # Adjust the threshold as needed
            # Turn on the relay
            GPIO.output(gpio_pin, GPIO.LOW)
            print("Wakeword Detected! Turning on the relay.")
            
        if prediction['hey_mycroft'] > 0.3:  # Adjust the threshold as needed
            # Turn on the relay
            GPIO.output(gpio_pin, GPIO.HIGH)
            # client_socket.sendto(b'low', (server_ip, server_port))
            print("Wakeword Detected! Turning on the relay.")
            
            # Wait for 20 seconds
            
            # Turn off the relay after 20 seconds
            print("Turning off the relay.")

        # Print results table
        n_spaces = 16
        output_string_header = """
            Model Name         | Score | Wakeword Status
            --------------------------------------
            """

        for mdl in owwModel.prediction_buffer.keys():
            # Add scores in formatted table
            scores = list(owwModel.prediction_buffer[mdl])
            curr_score = format(scores[-1], '.20f').replace("-", "")

            output_string_header += f"""{mdl}{" "*(n_spaces - len(mdl))}   | {curr_score[0:5]} | {"--"+" "*20 if scores[-1] <= 0.5 else "Wakeword Detected!"}
            """

        # Print results table
        print("\033[F"*(4*n_models+1))
        print(output_string_header, "                             ", end='\r')

# Start sender and receiver threads
sender_thread = threading.Thread(target=send_audio)
receiver_thread = threading.Thread(target=receive_audio)
sender_thread.start()
receiver_thread.start()

# Run capture loop continuosly, checking for wakewords
if __name__ == "__main__":
    pass
