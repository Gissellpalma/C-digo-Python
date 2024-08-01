import paho.mqtt.client as mqtt
from datetime import datetime, time as dt_time
import os
import time
import pytz
import threading
import subprocess

# Configuración MQTT
MQTT_BROKER = "192.168.2.7"
MQTT_PORT = 1888  # Asegúrate de que este sea el puerto correcto para tu broker
MQTT_TOPIC_CAMERA_STATUS = "camara/estado"
MQTT_TOPIC_MOTION_DETECTED = "movimiento/detectado"
MQTT_TOPIC_CAMERA_SCHEDULE = "camara/hora"
MQTT_TOPIC_MOTION_LOCATION = "movimiento/ubicado"

# Configuración de la cámara
CAMERA_DEVICE = "/dev/video2"  # Esto puede variar, verifica el dispositivo correcto
CAPTURE_FOLDER = "captures"

# Asegúrate de que la carpeta exista
os.makedirs(CAPTURE_FOLDER, exist_ok=True)

# Zona horaria de Ecuador
ecuador_tz = pytz.timezone('America/Guayaquil')

# Variables de estado
camera_scheduled = False
motion_detected_last_state = False

def is_night_time():
    current_time = datetime.now(ecuador_tz).time()
    return dt_time(22, 0) <= current_time or current_time <= dt_time(6, 0)

def find_camera(camera_name):
    result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
    devices = result.stdout.split('\n')

    # Buscar el nombre del dispositivo
    for i, line in enumerate(devices):
        if camera_name in line:
            # El siguiente dispositivo en la lista es el /dev/video*
            if i + 1 < len(devices):
                device_line = devices[i + 1].strip()
                if device_line.startswith('/dev/video'):
                    return device_line
    return None

CAMERA_NAME = "IMC Networks XHC Camera"

def activate_camera():
    global CAMERA_DEVICE
    CAMERA_DEVICE = find_camera(CAMERA_NAME) or CAMERA_DEVICE
    if CAMERA_DEVICE is None:
        print("No se pudo encontrar el dispositivo de cámara")
        return
    print(f"Cámara activada en {CAMERA_DEVICE}")

def deactivate_camera():
    print("Cámara desactivada")

def capture_image_with_fswebcam():
    timestamp = datetime.now(ecuador_tz).strftime("%Y%m%d_%H%M%S")
    filename = f"{CAPTURE_FOLDER}/capture_{timestamp}.jpg"
    try:
        subprocess.run(['fswebcam', '-d', CAMERA_DEVICE, '-r', '640x480', '--no-banner', filename], check=True)
        return filename
    except subprocess.CalledProcessError as e:
        print(f"Error al capturar la imagen: {e}")
        return None

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe([(MQTT_TOPIC_CAMERA_STATUS, 2), (MQTT_TOPIC_MOTION_DETECTED, 2), 
                      (MQTT_TOPIC_CAMERA_SCHEDULE, 1), (MQTT_TOPIC_MOTION_LOCATION, 1)])

def on_message(client, userdata, msg):
    global camera_scheduled, motion_detected_last_state

    print(f"Mensaje recibido en el tópico {msg.topic}: {msg.payload.decode()}")

    if msg.topic == MQTT_TOPIC_CAMERA_STATUS:
        if msg.payload.decode() == "Camara en modo programado":
            camera_scheduled = True
            client.publish(MQTT_TOPIC_CAMERA_SCHEDULE, "Horario programado para las 22:00pm a 6:00am", qos=1)
        elif msg.payload.decode() == "Detectando movimiento":
            camera_scheduled = False
            deactivate_camera()
            client.publish(MQTT_TOPIC_CAMERA_SCHEDULE, "", qos=1)
    
    elif msg.topic == MQTT_TOPIC_MOTION_DETECTED:
        motion_detected = (msg.payload.decode() == "ON")
        
        # Solo activar la cámara y tomar una foto si el estado de detección de movimiento cambia a "ON"
        if motion_detected and not motion_detected_last_state:
            activate_camera()
            image_file = capture_image_with_fswebcam()
            if image_file:
                timestamp = datetime.now(ecuador_tz).strftime("%Y-%m-%d %H:%M:%S")
                client.publish(MQTT_TOPIC_MOTION_LOCATION, f"Captura Guardada {timestamp}", qos=1)
            deactivate_camera()
        
        motion_detected_last_state = motion_detected

    # Enviar confirmación de recepción para mensajes importantes
    if msg.topic in [MQTT_TOPIC_CAMERA_STATUS, MQTT_TOPIC_MOTION_DETECTED]:
        client.publish(f"{msg.topic}/ack", "received", qos=2)

def camera_loop():
    global camera_scheduled
    while True:
        if camera_scheduled and is_night_time():
            activate_camera()
            while camera_scheduled and is_night_time():
                # Simplemente espera para no usar CPU intensivamente
                time.sleep(0.1)  
            deactivate_camera()
        time.sleep(1)  # Espera 1 segundo antes de verificar de nuevo

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Inicia el loop MQTT en un hilo separado
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.start()

# Inicia el loop de la cámara
camera_loop()
