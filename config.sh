#!/bin/bash

# =============================================
# Configuration post-installation pour Raspbian
# =============================================

dossierInstallation = "/home/admin"

# Fonction pour afficher les étapes
print_step() {
    echo -e "\033[32m----------------------------------------"
    echo -e "[Étape] $1"
    echo -e "----------------------------------------\033[0m"
}

# Fonction pour demander le réseau Wi-Fi et se connecter
connect_wifi() {

        # Redémarrer l'interface Wi-Fi
        wpa_cli -i wlan0 reconfigure
        sleep 3

        # Vérifier la connexion
        if ping -c 4 google.com &> /dev/null; then
            echo "Connexion Wi-Fi réussie !"
            break
        else
            echo ""
            echo -e "\033[31mErreur : Échec de la connexion Wi-Fi. Veuillez réessayer. !\033[0m"
            echo -e "-> \"sudo raspi-config\""
            exit
        fi
}

# 1. Vérifier execution en tant que sudoer
if [ "$UID" -ne "0" ]
then

        echo -e "\033[31mErreur : Vous devez être root (sudo) !\033[0m"
        echo -e "-> sudo bash ./config.sh"
        echo -e "Sortie ..."
        exit
fi

# 2. Configuration du swap pour optimiser les performances
print_step "Optimisation du swap"
dphys-swapfile swapoff
sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
dphys-swapfile setup
dphys-swapfile swapon

# 3. Activation du Wi-Fi et test de connexion
print_step "Activation du Wi-Fi et test de connexion"
rfkill unblock wifi
connect_wifi

# 4. Mise à jour du système et des paquets
print_step "Mise à jour du système et des paquets"
apt-get update -y && apt-get upgrade -y
apt-get autoremove -y
apt-get clean

# 5. Configuration de la locale et du fuseau horaire
print_step "Configuration de la locale et du fuseau horaire"
raspi-config nonint do_change_locale fr_FR.UTF-8
raspi-config nonint do_change_timezone Europe/Paris

# 6. Installation des outils essentiels
print_step "Installation des outils essentiels (git, curl, htop, etc.)"
apt-get install -y git curl wget htop vim net-tools

# 7. Configuration de l'environnement Python et des dépendances
print_step "Installation des dépendances Python et création d'un environnement virtuel"
apt-get install -y python3 python3-venv python3-pip python3-dev libglib2.0-dev
python3 -m venv $dossierInstallation/venv
source $dossierInstallation/venv/bin/activate

# 8. Installation des paquets Pip (exemple : numpy et requests)
print_step "Installation des paquets Pip"
sudo $dossierInstallation/venv/bin/pip install --upgrade pip
sudo $dossierInstallation/venv/bin/pip install bluepy paho.mqtt

# 9. Installation et configuration de Mosquitto (broker MQTT)
print_step "Installation et configuration de Mosquitto"
apt-get install -y mosquitto mosquitto-clients

# Configuration de Mosquitto pour écouter sur toutes les interfaces (0.0.0.0) et sans authentification
cat > /etc/mosquitto/mosquitto.conf <<EOF
listener 1883 0.0.0.0
allow_anonymous true
EOF

# Redémarrer Mosquitto pour appliquer la configuration
systemctl restart mosquitto
systemctl enable mosquitto

# 10. Désactivation du Wi-Fi après installation
print_step "Désactivation du Wi-Fi"
sudo rfkill block wifi
ifconfig wlan0 down

# 11. Configuration du service passerelle.service
print_step "Configuration du service passerelle.service"
cp $dossierInstallation/passerelle.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable passerelle.service
systemctl start passerelle.service

# 12. Nettoyage final
print_step "Nettoyage final"
apt-get autoremove -y
apt-get clean

echo "========================================"
echo -e "\033[32mConfiguration terminée avec succès !\033[0m"
echo "----------------------------------------"
echo "Maintenant faire : 'sudo rasp-config'"
echo "aller dans Performances -> Fan"
echo "Changer paramètresactivation ventilateur a 80°C"
echo "========================================"
echo "Pensez a REDEMARRER le Raspberry Pi pour que tout les changements puissent se faire"
