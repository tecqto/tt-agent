#!/bin/bash
#
# Tecqto-Agent installer bash script
# 
#  Code by: Tecqto.com
#  Date: 03/01/2017
#  Revised: 11/02/2017
#  Tested: CoreOS, Cents OS, Fedora, Debian, Ubuntu, FreeBsd
#
#

echo -e "Commencing Tecqto-Agent installation...\n"

# Root required
if [ $(id -u) != "0" ];
then
	echo -e "|   Error: You need to be root to install the Tecqto-Agent \n|"
	echo -e "|		  The agent itself will NOT be running as root but instead under its own non-privileged user\n|"
	exit 1
fi

# Parameters required
if [ $# -lt 1 ]
then
	echo -e "|   Usage: bash $0 'token'\n|"
	exit 1
fi

echo -e "This software requires Python version 2 to be installed."
echo -e "Detecting if Python 2 is available...\n"

if [ -n "$(command -v python)" ]
then
	PYTHONCOMMAND="python"
elif [ -n "$(command -v python2)" ]
then
	PYTHONCOMMAND="python2"
fi

pyv="$($PYTHONCOMMAND -V 2>&1 | awk '{ print $2 }' | cut -d'.' -f1)"

if [ $pyv == '2' ]
then
	echo -e "Python 2 found. Proceeding with Tecqto-Agent installation...\n"
	mkdir -p /etc/tecqto
	echo -e "Downloading tt-install.py to /etc/tecqto\n   + $(wget -nv -o /dev/stdout -O /etc/tecqto/tt-install.py --no-check-certificate https://raw.githubusercontent.com/tecqto/tt-agent/master/tt-install.py)"
	if [ -f /etc/tecqto/tt-install.py ]
then
	$PYTHONCOMMAND /etc/tecqto/tt-install.py $1
else
	# Error Display
	echo -e "\n Error: Tecqto-Agent Unable to Download - Tecqto-Agent Can't be Installed"

fi
	exit 0
else
	echo "You do not have Python 2 installed."
	echo "Python 2 is required to run this program."
	echo "Please install Python 2 first.\n"
	exit 1
fi
