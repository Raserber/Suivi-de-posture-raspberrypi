import time
import json
import struct
import threading
from datetime import datetime

import paho.mqtt.client as mqtt
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, UUID, BTLEDisconnectError

# ======= CONFIGURATION =======

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "FAME"

SERVICE_UUID = UUID("04dbe0ce-7da7-4629-b2c1-7b6389fd5290")
CHAR_IMU_UUID = UUID("150b83fc-1440-4104-b232-4e61ebc94322")
CHAR_BATT_UUID = UUID("775b6cf8-f951-41ff-9eb1-b37469b4ed64")
CHAR_CMD_UUID = UUID("c6183eb2-ce58-46c1-82de-c96e5033d7a4")

SCAN_INTERVAL = 10  # secondes
DEVICE_PREFIX = "STM"

devices_found = {}

# ========== MQTT SETUP ==========

mqtt_client = mqtt.Client()

connected_devices = {}  # nom → { peripheral, thread, running_flag }

def now_iso():
    return datetime.utcnow().isoformat()

def publish(topic, payload, retain=False):
    mqtt_client.publish(topic, json.dumps(payload), retain=retain)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ========== NOTIFICATION HANDLER ==========

class BLEDelegate(DefaultDelegate):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def handleNotification(self, cHandle, data):
        try:
            if len(data) == 13:
                origine, ax, ay, az, gx, gy, gz = struct.unpack("<Bhhhhhh", data)

                if (origine == 1) :

                    topic_base = f"{MQTT_TOPIC_BASE}/{self.name}/data/capteurs/haut"

                else :
                    topic_base = f"{MQTT_TOPIC_BASE}/{self.name}/data/capteurs/bas"

                payload = {
                    "accX": ax,
                    "accY": ay,
                    "accZ": az,
                    "gyrX": gx,
                    "gyrY": gy,
                    "gyrZ": gz,
                    "dt": 500,
                    "conversionAcc": 16384.0,
                    "conversionGyr": 131.0
                }

                publish(topic_base, payload)

            elif len(data) == 6:
                voltage_mv, temp_cX100, cap = struct.unpack("<HhH", data)
                payload = {
                    "tension": voltage_mv,
                    "temperature": temp_cX100 / 100.0,
                    "capacitee": cap
                }
                publish(f"{MQTT_TOPIC_BASE}/{self.name}/data/batterie", payload)
        except Exception as e:
            log(f"Erreur notification {self.name}: {e}")

# ========== SCAN BLE PÉRIODIQUE ==========

def scan_ble():
    log("Scan BLE...")
    scanner = Scanner()
    devices = scanner.scan(5.0)
    for d in devices:
        name = d.getValueText(9)  # Complete Local Name
        if name and name.startswith(DEVICE_PREFIX):
            addr = d.addr

            devices_found[name] = addr

            topic_base = f"{MQTT_TOPIC_BASE}/{name}"
            publish(f"{topic_base}/description/Nom", name, retain=True)
            publish(f"{topic_base}/description/Adresse_BLE", addr, retain=True)
            if name not in connected_devices:
                publish(f"{topic_base}/etats/BLE/etat", "non_connecte", retain=True)
            publish(f"{topic_base}/etats/BLE/last_time", now_iso(), retain=True)

# ========== CONNEXION / DÉCONNEXION ==========

def connect_device(name):

    try:
        log(f"Tentative de connexion à {name}")
        p = Peripheral(devices_found[name])
        p.setDelegate(BLEDelegate(name))
        svc = p.getServiceByUUID(SERVICE_UUID)
        imu = svc.getCharacteristics(CHAR_IMU_UUID)[0]
        batt = svc.getCharacteristics(CHAR_BATT_UUID)[0]

        p.writeCharacteristic(imu.getHandle() + 1, b"\x01\x00", withResponse=True)
        p.writeCharacteristic(batt.getHandle() + 1, b"\x01\x00", withResponse=True)

        running = threading.Event()
        running.set()

        def notify_loop():
            while running.is_set():
                try:
                    if p.waitForNotifications(1.0):
                        continue
                    publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/last_time", now_iso(), retain=True)
                except BTLEDisconnectError:
                    log(f"Déconnecté de {name}")
                    break
                except Exception as e:
                    log(f"Erreur {name}: {e}")
            p.disconnect()
            publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/etat", "non_connecte", retain=True)

        thread = threading.Thread(target=notify_loop, daemon=True)
        thread.start()

        connected_devices[name] = {
            "peripheral": p,
            "thread": thread,
            "running": running
        }

        publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/etat", "connecte", retain=True)
    except Exception as e:
        log(f"Erreur de connexion à {name} : {e}")

def disconnect_device(name):
    info = connected_devices.get(name)
    if info:
        info["running"].clear()
        info["thread"].join()
        try:
            info["peripheral"].disconnect()
        except:
            pass
        del connected_devices[name]
        publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/etat", "non_connecte", retain=True)
        log(f"Déconnecté de {name}")

# ========== MQTT CALLBACK ==========

def on_mqtt_message(client, userdata, msg):
    try:
        parts = msg.topic.split('/')
        if parts[-1] == "etat":
            device_name = parts[1]
            cmd = msg.payload.decode()

            if len(devices_found) and cmd == "connexion" and device_name not in connected_devices:
                threading.Thread(target=connect_device, args=(device_name,), daemon=True).start()
            elif len(devices_found) and cmd == "deconnexion" and device_name in connected_devices:
                threading.Thread(target=disconnect_device, args=(device_name,), daemon=True).start()
    except Exception as e:
        log(f"Erreur MQTT: {e}")

# ========== MAIN LOOP ==========

def main_loop():

    print('bah')
    while True:
        if (connected_devices == {}) :
            scan_ble()
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.subscribe(f"{MQTT_TOPIC_BASE}/+/etats/BLE/etat")
    mqtt_client.loop_start()

    try:
        main_loop()
    except KeyboardInterrupt:
        log("Arrêt manuel.")
