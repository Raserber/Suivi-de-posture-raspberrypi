#!/bin/bash

fichier_hostname="/etc/hostname"
fichier_hosts="/etc/hosts"
fichier_hostapd_conf="/etc/hostapd/hostapd.conf"
fichier_dnsmasq_conf="/etc/dnsmasq.conf"
fichier_wpa_supplicant_conf="/etc/wpa_supplicant/wpa_supplicant.conf"
fichier_dhcpcd_conf="/etc/dhcpcd.conf"
fichier_default_hostapd="/etc/default/hostapd"
fichier_hosts_allow="/etc/hosts.allow"
fichier_hosts_deny="/etc/hosts.deny"

ip_fixe_eth0_global="192.168.217.46"
ip_router_global="192.168.217.1"
ip_dns_global="195.83.24.30"

if [ "$UID" -ne "0" ]
then

	echo -e "\033[31mErreur : Vous devez être root (sudo) !\033[0m"
	echo -e "-> sudo Config.sh"
	echo -e "Sortie ..."
	exit

else

	#/etc/motd
	echo " "                                  			> /etc/motd
        echo " "                                   			>> /etc/motd
        echo "Pour changer la configuration initiale du Raspberry pi :"	>> /etc/motd
	echo "sudo Config.sh" 						>> /etc/motd
        echo " " 							>> /etc/motd
        echo "Pour changer de mode wifi :" 				>> /etc/motd
        echo "sudo SwitchWifi.sh" 					>> /etc/motd
        echo " " 							>> /etc/motd
        echo "Pour modifier les configurations du proxy :" 		>> /etc/motd
        echo "sudo ProxyOFF.sh" 					>> /etc/motd
        echo "sudo ProxyON.sh" 						>> /etc/motd
        echo " " 							>> /etc/motd
        echo " " 							>> /etc/motd

	#/etc/rc.local
	echo "#!/bin/sh -e"				> /etc/rc.local
	echo ""						>> /etc/rc.local
	echo "chown -R www-data:www-data /var/www/html"	>> /etc/rc.local
	echo ""						>> /etc/rc.local
	echo "/usr/local/bin/reboot.py&"		>> /etc/rc.local
	echo ""						>> /etc/rc.local
	echo "exit 0"					>> /etc/rc.local

	#/usr/local/bin/reboot.py
	echo "#!/usr/bin/python"						> /usr/local/bin/reboot.py
	echo ""									>> /usr/local/bin/reboot.py
	echo "import RPi.GPIO as GPIO"						>> /usr/local/bin/reboot.py
	echo "import os"							>> /usr/local/bin/reboot.py
	echo "import time"							>> /usr/local/bin/reboot.py
	echo ""									>> /usr/local/bin/reboot.py
	echo "GPIO.setmode(GPIO.BCM)"						>> /usr/local/bin/reboot.py
	echo "GPIO.setup(21,GPIO.IN,pull_up_down=GPIO.PUD_UP)"			>> /usr/local/bin/reboot.py
	echo "GPIO.setwarnings(False)"						>> /usr/local/bin/reboot.py
	echo ""									>> /usr/local/bin/reboot.py
	echo "def my_callback_one(channel):"					>> /usr/local/bin/reboot.py
        echo "	time.sleep(1)"							>> /usr/local/bin/reboot.py
        echo "	if GPIO.input(21) == GPIO.HIGH:"				>> /usr/local/bin/reboot.py
        echo "		print('REBOOT')"					>> /usr/local/bin/reboot.py
        echo "		os.system('reboot')"					>> /usr/local/bin/reboot.py
        echo "	else:"								>> /usr/local/bin/reboot.py
        echo "		print('HALT')"						>> /usr/local/bin/reboot.py
        echo "		os.system('halt')"					>> /usr/local/bin/reboot.py
	echo ""									>> /usr/local/bin/reboot.py
	echo "GPIO.add_event_detect(21, GPIO.FALLING, callback=my_callback_one)">> /usr/local/bin/reboot.py
	echo ""									>> /usr/local/bin/reboot.py
	echo "try:"								>> /usr/local/bin/reboot.py
	echo "    while 1:"							>> /usr/local/bin/reboot.py
	echo "	time.sleep(1)"							>> /usr/local/bin/reboot.py
	echo "except KeyboardInterrupt:"					>> /usr/local/bin/reboot.py
	echo "    pass"								>> /usr/local/bin/reboot.py
	echo ""									>> /usr/local/bin/reboot.py
	echo "GPIO.cleanup()"							>> /usr/local/bin/reboot.py

	chmod +x /usr/local/bin/reboot.py

	#/usr/local/bin/ProxyON.sh
	echo "#!/bin/bash"											> /usr/local/bin/ProxyON.sh
	echo ""													>> /usr/local/bin/ProxyON.sh
	echo "#/etc/apt/apt.conf"										>> /usr/local/bin/ProxyON.sh
	echo "echo 'Acquire::http::proxy \"http://www-cache.ujf-grenoble.fr:3128/\";' > /etc/apt/apt.conf"	>> /usr/local/bin/ProxyON.sh
	echo "echo 'Acquire::https::proxy \"https://www-cache.ujf-grenoble.fr:3128/\";' >> /etc/apt/apt.conf"	>> /usr/local/bin/ProxyON.sh
	echo ""													>> /usr/local/bin/ProxyON.sh
	echo "#/etc/environment"										>> /usr/local/bin/ProxyON.sh
	echo "echo 'http_proxy=\"http://www-cache.ujf-grenoble.fr:3128/\"' > /etc/environment"			>> /usr/local/bin/ProxyON.sh
	echo "echo 'https_proxy=\"https://www-cache.ujf-grenoble.fr:3128/\"' >> /etc/environment"		>> /usr/local/bin/ProxyON.sh
	echo ""													>> /usr/local/bin/ProxyON.sh
	echo "#/home/pi/.wgetrc"										>> /usr/local/bin/ProxyON.sh
	echo "echo 'http_proxy = http://152.77.66.134:3128/'	> /home/pi/.wgetrc"				>> /usr/local/bin/ProxyON.sh
	echo "echo 'https_proxy = https://152.77.66.134:3128/' >> /home/pi/.wgetrc"				>> /usr/local/bin/ProxyON.sh
	echo "echo 'use_proxy = on' >> /home/pi/.wgetrc"							>> /usr/local/bin/ProxyON.sh
	echo "echo 'wait = 15' >> /home/pi/.wgetrc"								>> /usr/local/bin/ProxyON.sh
	echo ""													>> /usr/local/bin/ProxyON.sh
	echo "#/root/.wgetrc"											>> /usr/local/bin/ProxyON.sh
	echo "echo 'http_proxy = http://152.77.66.134:3128/'  > /root/.wgetrc"					>> /usr/local/bin/ProxyON.sh
	echo "echo 'https_proxy = https://152.77.66.134:3128/' >> /root/.wgetrc"				>> /usr/local/bin/ProxyON.sh
	echo "echo 'use_proxy = on' >> /root/.wgetrc"								>> /usr/local/bin/ProxyON.sh
	echo "echo 'wait = 15' >> /root/.wgetrc"								>> /usr/local/bin/ProxyON.sh

	chmod +x /usr/local/bin/ProxyON.sh

	#/usr/local/bin/ProxyOFF.sh
	echo "#!/bin/bash"			> /usr/local/bin/ProxyOFF.sh
	echo ""					>> /usr/local/bin/ProxyOFF.sh
	echo "#/etc/apt/apt.conf"		>> /usr/local/bin/ProxyOFF.sh
	echo "echo '' > /etc/apt/apt.conf"	>> /usr/local/bin/ProxyOFF.sh
	echo ""					>> /usr/local/bin/ProxyOFF.sh
	echo "#/etc/environment"		>> /usr/local/bin/ProxyOFF.sh
	echo "echo '' > /etc/environment"	>> /usr/local/bin/ProxyOFF.sh
	echo ""					>> /usr/local/bin/ProxyOFF.sh
	echo "#/home/pi/.wgetrc"		>> /usr/local/bin/ProxyOFF.sh
	echo "echo ''	> /home/pi/.wgetrc"	>> /usr/local/bin/ProxyOFF.sh
	echo ""					>> /usr/local/bin/ProxyOFF.sh
	echo "#/root/.wgetrc"			>> /usr/local/bin/ProxyOFF.sh
	echo "echo ''  > /root/.wgetrc"		>> /usr/local/bin/ProxyOFF.sh

	chmod +x /usr/local/bin/ProxyOFF.sh

	read -p "Quel est le numéro du raspberry pi ? " numkit

	#/etc/hostname
	echo "RPiJeedom$numkit" > "$fichier_hostname"

	#/etc/hosts
	sed -i -e "/^127.0.1.1/ d" "$fichier_hosts"
	echo "127.0.1.1	RPiJeedom$numkit" >> "$fichier_hosts"

	#Point d'accès wifi (wlan0)
	echo "Canal wifi à utiliser (entre 1 et 11 inclus, 1,6 ou 11 de préférence) ? "
	read numcanal
	if [ $numcanal -gt 11 ] || [ $numcanal -lt 1 ]
	then
		echo "Erreur : canal non compris entre 1 et 11"
		echo "Sortie ..."
		exit
	fi

	echo "SSID généré : RPiJeedom$numkit"
	echo "mot de passe : wpaRPiJeedom$numkit"
	echo "Adresse IP du Raspberry pi dans ce mode : 192.168.4.1"

	#/etc/dnsmasq.conf
	echo "interface=wlan0"						> "$fichier_dnsmasq_conf"
	echo "domain-needed" 						>> "$fichier_dnsmasq_conf"
	echo "bogus-priv" 						>> "$fichier_dnsmasq_conf"
	echo "dhcp-range=192.168.4.2,192.168.4.50,255.255.255.0,24h" 	>> "$fichier_dnsmasq_conf"

        ip_fixe_eth0=$ip_fixe_eth0_global
        ip_router=$ip_router_global
        ip_dns=$ip_dns_global

	echo "Dans le cas où il n'y a aucune réponse d'un serveur DHCP (injoignable ou adresse MAC du raspberry pi inconnue du DHCP) : "

	read -p "	Adresse IP fixe (interface filaire) du raspberry [$ip_fixe_eth0] ? " ip_fixe_eth0
	if [ -z $ip_fixe_eth0 ]
	then
		ip_fixe_eth0=$ip_fixe_eth0_global
	fi
	read -p "	Adresse IP du routeur [$ip_router]? " ip_router
        if [ -z $ip_router ]
        then
                ip_router=$ip_router_global
        fi
	read -p "	Adresse IP du serveur DNS [$ip_dns]? " ip_dns
        if [ -z $ip_dns ]
        then
                ip_dns=$ip_dns_global
        fi

	echo $ip_fixe_eth0 > /etc/network/ip_fixe_eth0_fallback
	echo $ip_router > /etc/network/ip_router_fallback
	echo $ip_dns > /etc/network/ip_dns_fallback

	#/etc/dhcpcd.conf
	echo "hostname"								> "$fichier_dhcpcd_conf"
	echo "clientid"								>> "$fichier_dhcpcd_conf"
	echo "persistent"							>> "$fichier_dhcpcd_conf"
	echo "option rapid_commit"						>> "$fichier_dhcpcd_conf"
	echo "option domain_name_servers, domain_name, domain_search, host_name">> "$fichier_dhcpcd_conf"
	echo "option classless_static_routes"					>> "$fichier_dhcpcd_conf"
	echo "option ntp_servers"						>> "$fichier_dhcpcd_conf"
	echo "option interface_mtu"						>> "$fichier_dhcpcd_conf"
	echo "require dhcp_server_identifier"					>> "$fichier_dhcpcd_conf"
	echo "slaac private"							>> "$fichier_dhcpcd_conf"
	echo ""									>> "$fichier_dhcpcd_conf"
	echo "interface wlan0" 							>> "$fichier_dhcpcd_conf"
	echo "	static ip_address=192.168.4.1/24"				>> "$fichier_dhcpcd_conf"
	echo ""									>> "$fichier_dhcpcd_conf"
	echo "profile static_eth0"						>> "$fichier_dhcpcd_conf"
	echo "	static ip_address=$ip_fixe_eth0/24"				>> "$fichier_dhcpcd_conf"
	echo "	static routers=$ip_router"					>> "$fichier_dhcpcd_conf"
	echo "	static domain_name_servers=$ip_dns"				>> "$fichier_dhcpcd_conf"
	echo ""									>> "$fichier_dhcpcd_conf"
	echo "interface eth0"							>> "$fichier_dhcpcd_conf"
	echo "	fallback static_eth0"						>> "$fichier_dhcpcd_conf"

	#/etc/hostapd/hostapd.conf
	echo "interface=wlan0" 					> "$fichier_hostapd_conf"
	echo "driver=nl80211" 					>> "$fichier_hostapd_conf"
	echo "ssid=RPiJeedom$numkit" 				>> "$fichier_hostapd_conf"
	echo "hw_mode=g" 					>> "$fichier_hostapd_conf"
	echo "channel=$numcanal" 				>> "$fichier_hostapd_conf"
	echo "wmm_enabled=0" 					>> "$fichier_hostapd_conf" 
	echo "macaddr_acl=0" 					>> "$fichier_hostapd_conf" 
	echo "auth_algs=1" 					>> "$fichier_hostapd_conf" 
	echo "ignore_broadcast_ssid=0" 				>> "$fichier_hostapd_conf" 
	echo "wpa=2" 						>> "$fichier_hostapd_conf"
	echo "wpa_passphrase=wpaRPiJeedom$numkit" 		>> "$fichier_hostapd_conf" 
	echo "wpa_key_mgmt=WPA-PSK" 				>> "$fichier_hostapd_conf"
	echo "wpa_pairwise=TKIP" 				>> "$fichier_hostapd_conf"
	echo "rsn_pairwise=CCMP" 				>> "$fichier_hostapd_conf"

	#/etc/default/hostapd
	echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' > "$fichier_default_hostapd"

	read -p "Voulez-vous limiter l'accès en SSH ? (o/n) " limite_ssh
	if [ "$limite_ssh" = o ] || [ "$limite_ssh" = O ] || [ "$limite_ssh" = oui ] || [ "$limite_ssh" = OUI ] ; then

		#/etc/hosts.deny
	        echo 'sshd: ALL' > "$fichier_hosts_deny"

	        #/etc/hosts.allow
	        echo 'sshd: 152.77.179.0/255.255.255.0' > "$fichier_hosts_allow"
		echo "SSH autorisé depuis 152.77.179.0/24"

	else

		#/etc/hosts.deny
                echo '#sshd: ALL' > "$fichier_hosts_deny"

                #/etc/hosts.allow
                echo '#sshd: 152.77.179.0/255.255.255.0' > "$fichier_hosts_allow"

	fi

       	#/etc/wpa_supplicant/wpa_supplicant.conf
	if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]
	then
        	rm /etc/wpa_supplicant/wpa_supplicant.conf
	fi

        #/etc/network/interfaces.d/wlan0
        if [ -f /etc/network/interfaces.d/wlan0 ]
	then
		rm /etc/network/interfaces.d/wlan0
	fi

	/usr/local/bin/ProxyON.sh

	echo "1" > /etc/network/modeWifi

	echo "Appuyez sur la touche Entrée pour re-démarrer ..."
   	read attente
    	echo "Reboot !"
    	reboot

fi
