import time
import json
import struct
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, UUID, BTLEDisconnectError
import paho.mqtt.client as mqtt

# ==== Configuration ====
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
BASE_TOPIC = "BLE"

SCAN_NAME_PREFIX = "FAME"
SCAN_INTERVAL = 5  # seconds

# ==== Etats ====
STATE_ATTENTE = "etat_attente"
STATE_RECONNEXION = "etat_reconnexion"
STATE_CONNECTE = "connecte"
STATE_BLE_ACTIF = "ble_actif"
STATE_BLE_INACTIF = "ble_inactif"

class BLEDevice:
    def __init__(self, addr, name):
        self.addr = addr
        self.name = name
        self.state = "non_connecte"
        self.last_seen = time.time()
        self.peripheral = None

    def update_last_seen(self):
        self.last_seen = time.time()

class BLEScanDelegate(DefaultDelegate):
    def __init__(self, devices):
        super().__init__()
        self.devices = devices

    def handleDiscovery(self, dev, isNewDev, isNewData):
        for (adtype, desc, value) in dev.getScanData():
            if desc == "Complete Local Name" and value.startswith(SCAN_NAME_PREFIX):
                if dev.addr not in self.devices:
                    self.devices[dev.addr] = BLEDevice(dev.addr, value)
                self.devices[dev.addr].update_last_seen()

# ==== MQTT ====
class MQTTManager:
    def __init__(self, devices):
        self.devices = devices
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connecté à MQTT")
        self.client.subscribe(f"{BASE_TOPIC}/+/etats/BLE/etat")

    def on_message(self, client, userdata, msg):
        topic_parts = msg.topic.split("/")
        if len(topic_parts) == 5 and topic_parts[-1] == "etat":
            name = topic_parts[1]
            command = msg.payload.decode()
            for device in self.devices.values():
                if device.name == name and command == "connexion":
                    device.state = "demande_connexion"

    def publish_device_info(self, device):
        base = f"{BASE_TOPIC}/{device.name}"
        self.client.publish(f"{base}/description/Nom", device.name, retain=True)
        self.client.publish(f"{base}/description/Adresse_BLE", device.addr, retain=True)
        self.client.publish(f"{base}/etats/BLE/etat", device.state, retain=True)
        self.client.publish(f"{base}/etats/BLE/last_time", int(device.last_seen), retain=True)

# ==== Machine à état ====
def state_machine(devices, mqtt_mgr):
    scanner = Scanner().withDelegate(BLEScanDelegate(devices))

    while True:
        for addr, device in list(devices.items()):
            if device.state == "non_connecte":
                mqtt_mgr.publish_device_info(device)

            elif device.state == "demande_connexion":
                try:
                    print(f"Tentative de connexion à {device.name}")
                    device.peripheral = Peripheral(device.addr, addrType=device.addrType)
                    device.state = "connecte"
                    mqtt_mgr.publish_device_info(device)
                except Exception as e:
                    print(f"Erreur connexion BLE à {device.name}: {e}")
                    device.state = "non_connecte"

            elif device.state == "connecte":
                # Par défaut, on repasse en non connecté (à adapter)
                device.peripheral.disconnect()
                device.state = "non_connecte"

        print("Scan BLE...")
        scanner.scan(SCAN_INTERVAL)

# ==== Main ====
if __name__ == "__main__":
    devices = {}
    mqtt_mgr = MQTTManager(devices)
    mqtt_mgr.start()

    try:
        state_machine(devices, mqtt_mgr)
    except KeyboardInterrupt:
        print("Arrêt du script.")