import time
import json
import struct
import threading
import sys
from datetime import datetime

import paho.mqtt.client as mqtt
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, UUID, BTLEDisconnectError


# ===== CONFIGURATION =====

machineEtat = "attente"

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "FAME"

scanner = Scanner()
peripheral = None

SERVICE_UUID = UUID("04dbe0ce-7da7-4629-b2c1-7b6389fd5290")
CHAR_IMU_UUID = UUID("150b83fc-1440-4104-b232-4e61ebc94322")
CHAR_BATT_UUID = UUID("775b6cf8-f951-41ff-9eb1-b37469b4ed64")
CHAR_CMD_UUID = UUID("c6183eb2-ce58-46c1-82de-c96e5033d7a4")

SCAN_INTERVAL = 10  # secondes
DEVICE_PREFIX = "STM"

devices_discovered = {}
deviceBLE = {
    "name" : "",
    "adresse" : ""
    }

stopEvent_connecte_loop = threading.Event()
stopEvent_deconnexion = threading.Event()

# ======= MQTT SETUP =======

mqtt_client = mqtt.Client()

connected_devices = {}  # nom → { peripheral, thread, running_flag }

def now_iso():
    return time.strftime('%H:%M:%S')

def publish(topic, payload, retain=False):
    mqtt_client.publish(topic, json.dumps(payload), retain=retain)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ========== MQTT CALLBACK ==========

def on_mqtt_message(client, userdata, msg):

    try :
        parts = msg.topic.split('/')

        device_name = parts[1]
        cmd = msg.payload.decode()

        if (cmd == "connexion") :

            machineEtat = "connexion"

            deviceBLE["name"] = device_name
            deviceBLE["adresse"] = devices_discovered[device_name]

        elif (cmd == "deconnexion" and deviceBLE["name"]) :

            publish(f"{MQTT_TOPIC_BASE}/{deviceBLE['name']}/etats/BLE/etat", "non_connecte")

            deviceBLE["name"] = ""
            deviceBLE["adresse"] = ""

            stopEvent_deconnexion.set()

    except Exception as e :

        log("Lever d'exception dans 'MQTT'")
        log(f"Erreur {type(e)}: {e}")

# ======= NOTIFICATION HANDLER =======

class BLEDelegate(DefaultDelegate):
    def __init__(self, name):
        super().__init__()
        self.name = name

        self.dt = 0
        self.conversion_acc = 0
        self.conversion_gyr = 0
        self.pourcentage = 0

        self.imu_char = None
        self.custom_char = None

    def importCharacteristics(self, imu_char, custom_char) :

        self.imu_char = imu_char
        self.custom_char = custom_char

    def handleNotification(self, cHandle, data):
        try:

            if (self.imu_char == cHandle):

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
                    "dt": self.dt,
                    "conversionAcc": self.conversion_acc,
                    "conversionGyr": self.conversion_gyr
                }

                publish(topic_base, payload)

            elif (self.custom_char == cHandle) :

                voltage_mv, temp_cX100, cap, self.dt, self.conversion_acc, self.conversion_gyr, self.pourcentage = struct.unpack("<HhHHHHB", data)
                payload = {
                    "tension": voltage_mv,
                    "temperature": temp_cX100 / 100.0,
                    "capacitee": cap,
                    "pourcentage": self.pourcentage
                }

                publish(f"{MQTT_TOPIC_BASE}/{self.name}/data/batterie", payload)

        except Exception as e:
            log(f"Erreur notification {self.name}: {e}")

# =============================================================================================

def connecte_loop () :

    while not stopEvent_connecte_loop.is_set() :

        try :

            if peripheral.waitForNotifications(1.0):

                continue

            publish(f"{MQTT_TOPIC_BASE}/{deviceBLE['name']}/etats/BLE/last_time", now_iso(), retain=True)

        except BTLEDisconnectError:

            log(f"Déconnecté de {deviceBLE['name']}")

            machineEtat = "deconnexion"

            publish(f"{MQTT_TOPIC_BASE}/{deviceBLE['name']}/etats/BLE/etat", "deconnexion")

            break

        except Exception as e:

            log(f"Erreur {deviceBLE['name']}: {e}")
            break

    stopEvent_deconnexion.set()

# =============================================================================================

mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.subscribe(f"{MQTT_TOPIC_BASE}/+/downlink")
mqtt_client.loop_start()

while True :

    if (machineEtat == "attente") :

        try :

            log("Scan BLE...")
            log(deviceBLE)

            devices = scanner.scan(5.0)

            for device in devices :

                name = device.getValueText(9)

                if (deviceBLE["name"] == name) :

                    machineEtat = "connexion"
                    break

                if (name and name.startswith(DEVICE_PREFIX)) :

                    devices_discovered[name] = device.addr

                    publish(f"{MQTT_TOPIC_BASE}/{name}/description/Nom", name, retain=True)
                    publish(f"{MQTT_TOPIC_BASE}/{name}/description/Adresse_BLE", device.addr, retain=True)

                    publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/etat", "non_connecte", retain=True)
                    publish(f"{MQTT_TOPIC_BASE}/{name}/etats/BLE/last_time", now_iso(), retain=True)


                if (name == "STM32Test") :

                    machineEtat = "connexion"

                    deviceBLE["name"] = name
                    deviceBLE["adresse"] = devices_discovered[name]

        except Exception as e :

            log("Lever d'exception dans 'attente'")
            log(f"Erreur {type(e)}: {e}")

    elif (machineEtat == "connexion") :

        try :

            publish(f"{MQTT_TOPIC_BASE}/{deviceBLE['name']}/etats/BLE/etat", "connexion")
            log("Tentative de connexion ...")

            delegation = BLEDelegate(deviceBLE["name"])
            peripheral = Peripheral(deviceBLE["adresse"])
            peripheral.setDelegate(delegation)

            svc = peripheral.getServiceByUUID(SERVICE_UUID)
            imu_char = svc.getCharacteristics(CHAR_IMU_UUID)[0]
            custom_char = svc.getCharacteristics(CHAR_BATT_UUID)[0]
            cmd_char = peripheral.getCharacteristics(uuid=CHAR_CMD_UUID)[0]

            delegation.importCharacteristics(imu_char.getHandle(), custom_char.getHandle())

            peripheral.writeCharacteristic(imu_char.getHandle() + 1, b"\x01\x00", withResponse=True)
            peripheral.writeCharacteristic(custom_char.getHandle() + 1, b"\x01\x00", withResponse=True)

            machineEtat = "connecte"

        except Exception as e :

                log("Lever d'exception dans 'connexion'")
                log(f"Erreur {type(e)}: {e}")

    elif (machineEtat == "connecte") :

        try :

            publish(f"{MQTT_TOPIC_BASE}/{deviceBLE['name']}/etats/BLE/etat", "connecte")

            thread_connecte = threading.Thread(target=connecte_loop, daemon=True)

            thread_connecte.start()

            machineEtat = "actif"

        except Exception as e :

            log("Lever d'exception dans 'connecte'")
            log(f"Erreur {type(e)}: {e}")

    elif ((machineEtat == "actif" or machineEtat == "non_actif")) :

        if (stopEvent_deconnexion.is_set()) :
            machineEtat = "deconnexion"

    elif (machineEtat == "deconnexion") :

        try :

            stopEvent_connecte_loop.set()
            thread_connecte.join()

            peripheral.disconnect()
            devices_discovered = {}

            machineEtat = "attente"
            sys.exit()

        except Exception as e :

            log("Lever d'exception dans 'deconnexion'")
            log(f"Erreur {type(e)}: {e}")
