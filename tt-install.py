#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tt-nstall.py
#  Code by: Tecqto.com
#  Date: 03/01/2017
#  Revised: 11/02/2017
#  Tested: CoreOS, Cents OS, Fedora, Debian, Ubuntu, FreeBsd
#  Minimum Pythong Version: 2.7
#  
#  

import os, sys, time
from shutil import rmtree
import subprocess

def check_output(*popenargs, **kwargs):
    """ check_output method from subprocess module after Python 2.7 """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output

tecqto_dir = '/etc/tecqto'
tecqto_agent = 'tt-agent.py'
tecqto_agent_path = os.path.join(tecqto_dir,tecqto_agent)
tecqto_cronlog = 'tt-cron.log'
tecqto_cronlog_path = os.path.join(tecqto_dir,tecqto_cronlog)
tecqto_authlog = 'tt-auth.log'
tecqto_authlog_path = os.path.join(tecqto_dir,tecqto_authlog)

print("|\n|   Tecqto-Agent Installer\n|   ===================\n|")

if os.getuid() != 0:
    print("|   Error: You need to be root to install the Tecqto-Agent\n|")
    print("|          The agent itself will NOT be running as root but instead under its own non-privileged user\n|")
    sys.exit(1)

if len(sys.argv) != 2:
    print("|   Usage: {0} 'token'\n|".format(sys.argv[0]))
    sys.exit(1)


# Detect distro family
if subprocess.call(['command','-v','apt-get'],shell=True) == 0:
    distro_family = 'debian'
elif subprocess.call(['command','-v','yum'],shell=True) == 0:
    distro_family = 'redhat'
elif subprocess.call(['command','-v','pacman'],shell=True) == 0:
    distro_family = 'arch'
else:
    distro_family = 'other'

def is_crontab_available():
    return subprocess.call(['command','-v','crontab'],shell=True)==0

if not is_crontab_available():
    print("|")
    installvar = raw_input("|   Crontab is required and could not be found. Do you want to install it? [Y/n] ")
    if (installvar=='Y') or (installvar=='y'):
        if distro_family == 'debian':
            print("|\n|   Notice: Installing required package 'cron' via 'apt-get'")
            p = subprocess.Popen(['apt-get', '-y', 'update'])
            p.wait()
            p = subprocess.Popen(['apt-get', '-y', 'install', 'cron'])
            p.wait()
        elif distro_family == 'redhat':
            print("|\n|   Notice: Installing required package 'cronie' via 'yum'")
            p = subprocess.Popen(['yum', '-y', 'install', 'cronie'])
            p.wait()
            if not is_crontab_available():
                print("|\n|   Notice: Installing required package 'vixie-cron' via 'yum'")
                p = subprocess.Popen(['yum', '-y', 'install', 'vixie-cron'])
                p.wait()
        elif distro_family == 'arch':
            print("|\n|   Notice: Installing required package 'cronie' via 'pacman'")
            p = subprocess.Popen(['pacman', '-S', '--noconfirm', 'cronie'])
            p.wait()
        else:
            print("|   Could not detect the package manager used on the system to install Crontab")
    else:
        print("|   Skipping Crontab installation.")
    
    if not is_crontab_available():
        print("|\n|   Error: Crontab is required and could not be installed\n|")
        sys.exit(1)
    

def is_cron_running():
    ps = check_output(['ps','-Al'])
    proclist = ps.split('\n')
    proclist.remove('')
    proclistsplit = [proc.split() for proc in proclist]
    procs = [proc[-1] for proc in proclistsplit]
    cronprocs = [proc for proc in procs if 'cron' in proc]
    cron_running = (len(cronprocs)>0)
    return cron_running

if not is_cron_running():
    print("|")
    startcronflag = raw_input("|   Cron is available but not running. Do you want to start it? [Y/n] ")
    if (startcronflag=='Y') or (startcronflag=='y'):
        if distro_family == 'debian':
            print("|\n|   Notice: Starting 'cron' via 'service'")
            p = subprocess.Popen(['service', 'cron', 'start'])
            p.wait()
        elif distro_family == 'redhat':
            print("|\n|   Notice: Starting 'crond' via 'service'")
            p = subprocess.Popen(['chkconfig', 'crond', 'on'])
            p.wait()
            p = subprocess.Popen(['service', 'crond', 'start'])
            p.wait()
        elif distro_family == 'arch':
            print("|\n|   Notice: Starting 'cronie' via 'systemctl'")
            p = subprocess.Popen(['systemctl', 'start', 'cronie'])
            p.wait()
            p = subprocess.Popen(['systemctl', 'enable', 'cronie'])
            p.wait()
        else:
            print("|   Could not enable cron service\n|")
    else:
        print("|   Skipping the starting of cron service")
    
    if not is_cron_running():
        print("|\n|   Error: Cron is available but could not be started\n|")
        print("|   It is possible that Cron is running but not detected correctly.")
        continue_anyway = raw_input("|   Do you still wish to continue? [Y/n] ")
        if (continue_anyway=='Y') or (continue_anyway=='y'):
            pass
        else:
            print("|")
            sys.exit(1)
    

def exists_user(user):
    status = ( subprocess.call(['id', '-u', user]) == 0 )
    return status

def add_user_tecqto():
    status = ( subprocess.call(['useradd','tecqto','-r','-d',tecqto_dir,'-s','/bin/false']) == 0 )
    subprocess.call(['chown', '-R', 'tecqto:tecqto', tecqto_dir])
    subprocess.call(['chmod', '-R', '700', tecqto_dir])
    r = os.system('chmod +s `type -p ping` 2>/dev/null')
    if r!=0:
        os.system('chmod +s `command -v ping`')
    return status

def del_user_tecqto():
    status = ( subprocess.call(['userdel','tecqto']) == 0 )
    return status

def read_crontab(user):
    crontab_cmd = ['crontab', '-u', user, '-l']
    crontab_proc = subprocess.Popen(crontab_cmd, stdout=subprocess.PIPE)
    crontable = crontab_proc.stdout.read()
    return crontable

def search_in_crontab(crontable):
    crontab_list = crontable.split('\n')
    status_arr = [tecqto_agent_path in entry for entry in crontab_list]
    status = any(status_arr)
    return status

def cron_edit(user, crontablenew):
    cron_fromstdin = ['crontab', '-u', user, '-']
    cron_edit = subprocess.Popen(cron_fromstdin, stdin=subprocess.PIPE)
    cron_edit.communicate(crontablenew)
    time.sleep(1)
    if cron_edit.poll() == None:
        cron_edit.terminate()

def crontab_add_tecqto(user, crontable):
    crontable_new = crontable + "*/3 * * * * python {0} > {1} 2>&1\n".format(tecqto_agent_path,tecqto_cronlog_path)
    cron_edit(user, crontable_new)
    return 0

def crontab_remove_tecqto(user, crontable):
    crontab_list = crontable.split('\n')
    res = [crontab_list.remove(entry) for entry in crontab_list if tecqto_agent_path in entry]
    removed_entries = len(res)
    crontable_new = ('\n').join(crontab_list)
    cron_edit(user, crontable_new)
    return removed_entries

if os.path.isfile(tecqto_agent_path):
    rmtree(tecqto_dir)
    if exists_user('tecqto'):
        crontable = read_crontab('tecqto')
        crontab_remove_tecqto('tecqto', crontable)
        del_user_tecqto()
    else:
        crontable = read_crontab('root')
        crontab_remove_tecqto('root', crontable)

if not os.path.exists(tecqto_dir):
    os.mkdir(tecqto_dir)

# Method 1: Download
print("|   Downloading tt-agent.py to /etc/tecqto\n|\n|  ")
download_cmd = 'wget -nv -o /dev/stdout -O /etc/tecqto/tt-agent.py --no-check-certificate https://raw.githubusercontent.com/tecqto/tt-agent/master/tt-agent.py'
download_command = download_cmd.split()
dl = subprocess.Popen(download_command)
dl.wait()

# Method 2: Copy
#from shutil import copy2
#copy2(tecqto_agent, tecqto_dir)

# Make tt-agent.py executable
subprocess.call(['chmod','a+x',tecqto_agent_path])

# If successful, proceed
if os.path.isfile(tecqto_agent_path):
    token = sys.argv[1]
    authlog = open(tecqto_authlog_path, 'w')
    authlog.write(token)
    authlog.close()
    subprocess.call(['chmod', 'a-x', tecqto_authlog_path])
    
    add_user_tecqto()
    crontable = read_crontab('tecqto')
    crontab_add_tecqto('tecqto', crontable)
    print("|\n|   Success: The Tecqto agent has been installed\n|")
    
    print("|\n|   Running Tecqto agent now... \n|")
    subprocess.call(['python',tecqto_agent_path])
    # Fix permissions for newly created tt-agent.log and tt-data.log
    for f in os.listdir(tecqto_dir):
        subprocess.call(['chown', 'tecqto:tecqto', os.path.join(tecqto_dir,f)])
    
    # Try deleting the install script
    # Second condition, file extension .py, to prevent removing /usr/bin/python
    if os.path.isfile(sys.argv[0]) and ( '.py' in sys.argv[0][-3:] ):
        try:
            print("|   Removing install script\n|")
            os.remove(sys.argv[0])
        except:
            print("|   Could not remove install script\n|")
            sys.exit(2)
    
else:
    print("|\n|   Error: The Tecqto-Agent agent could not be installed\n|")
    sys.exit(1)

sys.exit(0)

