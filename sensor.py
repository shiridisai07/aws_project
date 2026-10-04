import json
import random
import time
import ssl
import paho.mqtt.client as mqtt


# ==========================================
# AWS IoT CONFIGURATION
# ==========================================

ENDPOINT = "a31cdm12ugh1v9-ats.iot.ap-southeast-2.amazonaws.com"
PORT = 8883
TOPIC = "iot/sensor/data"

CA_CERT = "certificates/AmazonRootCA1.pem"
CLIENT_CERT = "certificates/device.pem.crt"
PRIVATE_KEY = "certificates/private.pem.key"


# ==========================================
# MQTT CLIENT
# ==========================================

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)


# TLS configuration
client.tls_set(
    ca_certs=CA_CERT,
    certfile=CLIENT_CERT,
    keyfile=PRIVATE_KEY,
    tls_version=ssl.PROTOCOL_TLS
)


# ==========================================
# CONNECT
# ==========================================

print("Connecting to AWS IoT Core...")

client.connect(ENDPOINT, PORT)

# IMPORTANT:
# Start Paho MQTT network loop
client.loop_start()

print("Connected successfully!")
print("Publishing sensor data...")
print()


# ==========================================
# SENSOR SIMULATOR
# ==========================================

try:

    while True:

        temperature = round(random.uniform(20, 35), 2)
        humidity = round(random.uniform(40, 80), 2)
        pressure = round(random.uniform(1000, 1020), 2)

        data = {
            "device_id": "sensor01",
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure
        }

        message = json.dumps(data)

        result = client.publish(TOPIC, message)

        print("--------------------------------")
        print("Sensor Data Published")
        print("Device ID  :", data["device_id"])
        print("Temperature:", data["temperature"], "°C")
        print("Humidity   :", data["humidity"], "%")
        print("Pressure   :", data["pressure"], "hPa")
        print("MQTT Topic :", TOPIC)
        print("Publish Status:", result.rc)
        print("--------------------------------")

        time.sleep(5)


except KeyboardInterrupt:

    print("\nStopping sensor simulator...")

finally:

    client.loop_stop()
    client.disconnect()

    print("Disconnected from AWS IoT Core.")