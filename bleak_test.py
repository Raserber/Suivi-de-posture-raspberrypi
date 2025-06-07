import asyncio
import json
import struct
import time
from datetime import datetime

from bleak import BleakScanner, BleakClient
import paho.mqtt.client as mqtt

# ======= CONFIGURATION =======

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "FAME"

SERVICE_UUID = "04dbe0ce-7da7-4629-b2c1-7b6389fd5290"
CHAR_IMU_UUID = "150b83fc-1440-4104-b232-4e61ebc94322"
CHAR_BATT_UUID = "775b6cf8-f951-41ff-9eb1-b37469b4ed64"
CHAR_CMD_UUID = "c6183eb2-ce58-46c1-82de-c96e5033d7a4"

SCAN_INTERVAL = 10  # en secondes
DEVICE_PREFIX = "STM"

connected_devices = {}

# ========== UTILS ==========

def now_iso():
    return datetime.utcnow().isoformat()

def publish(topic, payload, retain=False):
    mqtt_client.publish(topic, payload=json.dumps(payload), retain=retain)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ========== BLE LOGIC ==========

async def scan_ble():
    log("Scan BLE...")
    devices = await BleakScanner.discover(timeout=5)
    for d in devices:
        if d.name and d.name.startswith(DEVICE_PREFIX):
            addr = d.address
            name = d.name
            topic_base = f"{MQTT_TOPIC_BASE}/{name}"
            publish(f"{topic_base}/description/Nom", name, retain=True)
            publish(f"{topic_base}/description/Adresse_BLE", addr, retain=True)
            publish(f"{topic_base}/etats/BLE/etat", "non_connecte", retain=True)
            publish(f"{topic_base}/etats/BLE/last_time", now_iso(), retain=True)

async def connect_device_by_name(name):
    devices = await BleakScanner.discover(timeout=5)
    for d in devices:
        if d.name == name:
            log(f"Tentative de connexion à {name}")
            try:
                client = BleakClient(d)
                await client.connect()
                await setup_notifications(client, name)
                connected_devices[name] = client
                publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/etat", "connecte", retain=True)
                return
            except Exception as e:
                log(f"Erreur connexion BLE à {name}: {e}")

async def disconnect_device(name):
    client = connected_devices.get(name)
    if client:
        try:
            await client.disconnect()
            log(f"Déconnecté de {name}")
        except Exception as e:
            log(f"Erreur déconnexion de {name}: {e}")
        del connected_devices[name]
        publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/etat", "non_connecte", retain=True)

async def setup_notifications(client, name):
    async def imu_handler(_, data):
        origine, ax, ay, az, gx, gy, gz = struct.unpack("<Bhhhhhh", data)

        if (origine == 1) :
            topic_base = f"{MQTT_TOPIC_BASE}/{name}/data/capteurs/haut"

        else :
            topic_base = f"{MQTT_TOPIC_BASE}/{name}/data/capteurs/bas"

        conversion_acc = 16384.0
        conversion_gyr = 131.0
        payload = {
            "accX": ax,
            "accY": ay,
            "accZ": az,
            "gyrX": gx,
            "gyrY": gy,
            "gyrZ": gz,
            "dt": 500,
            "conversionAcc": conversion_acc,
            "conversionGyr": conversion_gyr
        }
        publish(topic_base, payload)

    async def batt_handler(_, data):
        voltage_mv, temp_cX100, cap = struct.unpack("<HhH", data)
        payload = {
            "tension": voltage_mv,
            "temperature": temp_cX100 / 100.0,
            "capacitee": cap
        }
        publish(f"{MQTT_TOPIC_BASE}/{name}/data/batterie", payload)

    while True :
        await client.start_notify(CHAR_IMU_UUID, imu_handler)
        await client.start_notify(CHAR_BATT_UUID, batt_handler)

# ========== MQTT ==========

def on_mqtt_message(client, userdata, msg):
    try:
        parts = msg.topic.split('/')
        if parts[-1] == "etat":
            device_name = parts[1]
            cmd = msg.payload.decode()
            if cmd == "connexion" and device_name not in connected_devices:
                asyncio.run(connect_device_by_name(device_name))
            elif cmd == "deconnexion" and device_name in connected_devices:
                asyncio.run(disconnect_device(device_name))
    except Exception as e:
        log(f"Erreur MQTT: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.subscribe(f"{MQTT_TOPIC_BASE}/+/etats/BLE/etat")
mqtt_client.loop_start()

# ========== MAIN ==========

async def main():
    while True:
        await scan_ble()
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Arrêt manuel du script.")
