import time
import json
import struct
import threading
import sys
from datetime import datetime

import paho.mqtt.client as mqtt
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, UUID, BTLEDisconnectError


# ===== INITIALISATION =====

# variable qui va nous servir a adapter le comportement du programme
machineEtat = "attente"


# ----------- MQTT -----------------------------------------------|
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "FAME"

mqtt_client = mqtt.Client()

def publish(topic, payload, retain=False):
    """Fonction publiant sur un payload sur un public MQTT"""
    mqtt_client.publish(topic, json.dumps(payload), retain=retain)

# ----------------------------------------------------------------|

# ----------- BLE -------------------------------------------|
scanner = Scanner()
peripheral = None

delegation = None
connected_devices = {}  # nom → { peripheral, thread, running_flag }

# UUIDs BLE
SERVICE_UUID = UUID("04dbe0ce-7da7-4629-b2c1-7b6389fd5290")
CHAR_IMU_UUID = UUID("150b83fc-1440-4104-b232-4e61ebc94322")
CHAR_BATT_UUID = UUID("775b6cf8-f951-41ff-9eb1-b37469b4ed64")
CHAR_CMD_UUID = UUID("c6183eb2-ce58-46c1-82de-c96e5033d7a4")

SCAN_INTERVAL = 10  # secondes
DEVICE_PREFIX = "FAMESuiviDePosture" # pour filtrage

devices_discovered = {}
deviceBLE = {
    "name" : "",
    "adresse" : ""
    }

# -----------------------------------------------------------|

# ----------- Threading -------------------|
stopEvent_connecte_loop = threading.Event()
stopEvent_deconnexion = threading.Event()
ble_lock = threading.Lock()
# Gestion du threading : pour pouvoir communiquer
#                        entre les différents
#                        threads
# -----------------------------------------|

# ----------- Fonctions utiles ------------------------|
def now_iso():
    """Fonction renvoyant au format HH:MM:SS la date"""
    return time.strftime('%H:%M:%S')

def log(msg):
    """Fonction faisant un print d'un message log"""
    print(f"[{now_iso()}] {msg}")

# -----------------------------------------------------|


# ========== MQTT CALLBACK ==========

def on_mqtt_message(client, userdata, msg):
    """Fonction qui recupere les messages MQTT pour les traiter"""
    try :
        payload = msg.payload.decode()

        cmd = payload.split('|')[0]
        cmd_data = payload.split('|')[-1] # ne genera pas d'erreur si liste à 1 seul entité

        if (cmd == "connexion" and cmd_data in devices_discovered.keys()) :

            machineEtat = "connexion"

            deviceBLE["name"] = cmd_data
            deviceBLE["adresse"] = devices_discovered[cmd_data]

        elif (cmd == "deconnexion" and deviceBLE["name"]) :

            publish(f"{MQTT_TOPIC_BASE}/{deviceBLE['name']}/etats/BLE/etat", "non_connecte")

            deviceBLE["name"] = ""
            deviceBLE["adresse"] = ""

            stopEvent_deconnexion.set()

        # elif (cmd == "goto_inactif" and deviceBLE["name"]) :

            # delegation.envoiCommande(0)

        # elif (cmd == "goto_actif" and deviceBLE["name"]) :

            # delegation.envoiCommande(1)

        # elif (cmd == "dt" and deviceBLE["name"]) :

            # delegation.envoiCommande(2, cmd_data)

        # elif (cmd == "conversion_acc" and deviceBLE["name"]) :

            # delegation.envoiCommande(3, cmd_data)

        # elif (cmd == "conversion_gyr" and deviceBLE["name"]) :

            # delegation.envoiCommande(4, cmd_data)


    except Exception as e :

        log("Lever d'exception dans 'MQTT'")
        log(f"Erreur {type(e)}: {e}")

# ======= NOTIFICATION HANDLER =======

class BLEDelegate(DefaultDelegate):
    def __init__(self, name):
        super().__init__()
        self.name = name

        # initialisation des variables sur les paramètres par défaut
        self.dt = 200
        self.conversion_acc = 16384
        self.conversion_gyr = 131
        self.pourcentage = 0

        # initialisation des variables contenant les UUIDs BLE
        self.imu_char = None
        self.custom_char = None
        self.cmd_char = None

    def importCharacteristics(self, imu_char, custom_char, cmd_char) :
        """Importation des UUID BLE"""

        self.imu_char = imu_char
        self.custom_char = custom_char
        self.cmd_char = cmd_char

    def envoiCommande(self, cmd, cmd_data=0) :

        payload = struct.pack("<Bh", cmd, cmd_data)

        self.cmd_char.write(payload, withResponse=True)


    def handleNotification(self, cHandle, data):
        """Gestion des messages BLE sur les 2 caractéristiques IMU et custom"""
        try:

            if (self.imu_char == cHandle):

                # extraction des données
                ax, ay, az, gx, gy, gz, infos = struct.unpack("<hhhhhhB", data)

                origine = infos & 0b1 # bit de poids faible
                temoin_capteurBas = (infos>>1) & 0b1 # 2nd bit
                temoin_capteurHaut = (infos>>2) & 0b1 # 3eme bit



                if (origine == 1) :

                    topic_base = f"{MQTT_TOPIC_BASE}/{self.name}/data/capteurs/haut"
                    deviceName = f"haut {self.name}"

                    ax = -ax
                    ay = -ay
                    az = -az

                else :

                    topic_base = f"{MQTT_TOPIC_BASE}/{self.name}/data/capteurs/bas"
                    deviceName = f"bas {self.name}"

                payload = {
                    "deviceName": deviceName,
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

                publish(f"{MQTT_TOPIC_BASE}/{self.name}/data/batterie", payload, retain=True)
                with open("/home/admin/test.csv", "a") as f :
                    f.write(f"{now_iso()}, {self.pourcentage}\n")

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
mqtt_client.subscribe(f"{MQTT_TOPIC_BASE}/downlink")
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

                    

                    if (name == "FAMESuiviDePosture_01") :

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
            cmd_char = svc.getCharacteristics(CHAR_CMD_UUID)[0]

            delegation.importCharacteristics(imu_char.getHandle(), custom_char.getHandle(), cmd_char)

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

    # si deconnexion le programme se kill
    # Car : bug chelou non résolu cote bluepy
    # quand deconnexion à un périphérique
    # BLE pas possible de se reconnecter
    # à ce meme périphérique sans redemarrer
    # le programme. re-lancement du programme
    # gérer par systemd via .service

        try :

            stopEvent_connecte_loop.set()
            thread_connecte.join()

            peripheral.disconnect()
            devices_discovered = {}

            mqtt_client.loop_stop()
            mqtt_client.disconnect()

            machineEtat = "attente"

        except Exception as e :

            log("Lever d'exception dans 'deconnexion'")
            log(f"Erreur {type(e)}: {e}")

        finally :

            sys.exit()

