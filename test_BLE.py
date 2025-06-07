from bluepy.btle import Peripheral, UUID
import struct
import time

# Configuration BLE
BLE_ADDRESS = "02:07:92:73:45:0A"
UUID_SERVICE = UUID("0000180c-0000-1000-8000-00805f9b34fb")
UUID_CHARACTERISTIC = UUID("00002a56-0000-1000-8000-00805f9b34fb")

print("Tentative de connexion au périphérique BLE...")

try:
    # Connexion au périphérique BLE
    peripheral = Peripheral(BLE_ADDRESS)
    print("Connecté au périphérique BLE.")

    service = peripheral.getServiceByUUID(UUID_SERVICE)
    print("Service trouvé.")

    characteristic = service.getCharacteristics(UUID_CHARACTERISTIC)[0]
    print("Caractéristique trouvée.")

    def read_sensor_data():
        data = characteristic.read()
        ax, ay, az, gx, gy, gz = struct.unpack("hhhhhh", data)
        return ax, ay, az, gx, gy, gz

    while True:
        try:
            ax, ay, az, gx, gy, gz = read_sensor_data()
            print(f"Accel: {ax}, {ay}, {az} | Gyro: {gx}, {gy}, {gz}")
            time.sleep(0.5)
        except Exception as e:
            print(f"Erreur lors de la lecture des données BLE : {e}")

except Exception as e:
    print(f"Erreur lors de la connexion au périphérique BLE : {e}")
