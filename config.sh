#!/bin/bash

# =============================================
# Configuration post-installation pour Raspbian
# =============================================

# Fonction pour afficher les étapes
print_step() {
    echo "----------------------------------------"
    echo "[Étape] $1"
    echo "----------------------------------------"
}

# Fonction pour demander le réseau Wi-Fi et se connecter
connect_wifi() {
    while true; do
        read -p "Entrez le nom du réseau Wi-Fi (SSID) : " ssid
        read -s -p "Entrez le mot de passe Wi-Fi : " password
        echo

        # Configuration Wi-Fi
        cat > /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=FR

network={
    ssid="$ssid"
    psk="$password"
}
EOF

        # Redémarrer l'interface Wi-Fi
        wpa_cli -i wlan0 reconfigure
        sleep 10

        # Vérifier la connexion
        if ping -c 4 google.com &> /dev/null; then
            echo "Connexion Wi-Fi réussie !"
            break
        else
            echo "Échec de la connexion Wi-Fi. Veuillez réessayer."
        fi
    done
}

# 1. Mise à jour du système et des paquets
print_step "Mise à jour du système et des paquets"
apt-get update -y && apt-get upgrade -y
apt-get autoremove -y
apt-get clean

# 2. Configuration de la locale et du fuseau horaire
print_step "Configuration de la locale et du fuseau horaire"
raspi-config nonint do_change_locale fr_FR.UTF-8
raspi-config nonint do_change_timezone Europe/Paris

# 4. Activation du Wi-Fi et connexion
print_step "Activation du Wi-Fi et connexion"
rfkill unblock wifi
connect_wifi

# 5. Installation des outils essentiels
print_step "Installation des outils essentiels (git, curl, htop, etc.)"
apt-get install -y git curl wget htop vim net-tools

# 6. Configuration de l'environnement Python et des dépendances
print_step "Installation des dépendances Python et création d'un environnement virtuel"
apt-get install -y python3 python3-venv python3-pip python3-dev
python3 -m venv /home/pi/myenv
source /home/pi/myenv/bin/activate

# 7. Installation des paquets Pip (exemple : numpy et requests)
print_step "Installation des paquets Pip"
pip install --upgrade pip
pip install numpy requests

# 8. Désactivation du Wi-Fi après installation
print_step "Désactivation du Wi-Fi"
rfkill block wifi
ifconfig wlan0 down

# 9. Configuration du service gateway.service
print_step "Configuration du service gateway.service"
cp $(dirname "$0")/gateway.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable gateway.service
systemctl start gateway.service

# 10. Désactivation définitive du Wi-Fi
print_step "Désactivation définitive du Wi-Fi"
echo "blacklist brcmfmac" | tee -a /etc/modprobe.d/blacklist-wifi.conf
echo "blacklist brcmutil" | tee -a /etc/modprobe.d/blacklist-wifi.conf
update-initramfs -u

# 12. Configuration du swap pour optimiser les performances
print_step "Optimisation du swap"
dphys-swapfile swapoff
sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
dphys-swapfile setup
dphys-swapfile swapon

# 13. Nettoyage final
print_step "Nettoyage final"
apt-get autoremove -y
apt-get clean

echo "========================================"
echo "Configuration terminée avec succès !"
echo "----------------------------------------"
echo "N'OUBLIEZ PAS DE MODIFIER LE MOT DE PASSE SSH"
echo "========================================"

