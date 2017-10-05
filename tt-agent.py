#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tt-agent.py
#  Code by: Tecqto.com
#  Date: 03/01/2017
#  Revised: 11/02/2017
#  Tested: CoreOS, Cents OS, Fedora, Debian, Ubuntu, FreeBsd
#  Minimum Pythong Version: 2.7
#  
#  

import sys, os, time
from base64 import b64encode
import subprocess
import platform

# Cron path issue workaround
if not 'sbin' in os.environ['PATH']:
    os.environ['PATH'] += ':/sbin:/usr/sbin'

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

class TTagent(object):
    def __init__(self):
        self.version = "0.11JN17"
        self.ttagent_dir = '/etc/tecqto/'
        self.authlog = os.path.join(self.ttagent_dir,'tt-auth.log')
        if not os.path.isfile(self.authlog):
            print("Error: Authentication log missing. Please authenticate client and try again.")
            sys.exit(1)
        
        authlog = open(self.authlog,'r')
        auth = authlog.read()
        authlog.close()
        self.auth = auth.split()[0]
        
        self.msdatalog = os.path.join(self.ttagent_dir,'tt-data.log')
        self.ttagentlog = os.path.join(self.ttagent_dir,'tt-agent.log')
        
        self.calc_uptime()
        self.calc_sessions()
        self.calc_processes()
        self.calc_filehandles()
        self.identify_os()
        self.calc_hardware()
        self.calc_connections()
        self.get_network_latency()
        self.calc_load()
        self.read_msdata()
        self.write_msdata()
        self.post_msdata()
    
    def calc_uptime(self):
        f = open('/proc/uptime', 'r')
        up = float(f.readline().split()[0])
        f.close()
        self.uptime = up
    
    def calc_sessions(self):
        p = check_output('who')
        n_sessions = len(p.splitlines())
        self.sessions = n_sessions
    
    def calc_processes(self):
        p = check_output(['ps','axc'])
        n_processes = len(p.splitlines())
        self.processes = n_processes
        # write the processes_array part here
        p2 = check_output(['ps', 'axc', '-o', 'uname:12,pcpu,rss,cmd', '--sort=-pcpu,-rss', '--noheaders', '--width', '120'])
        proclist = p2.decode('utf8').splitlines()
        proclistsplit = list()
        for proc in proclist:
            proclistsplit.append(proc.split())
        procarray = list()
        for proc in proclistsplit:
            procarray.append(' '.join(proc))
        procarray.append('')
        self.processes_array = ';'.join(procarray)
    
    def calc_filehandles(self):
        f = open('/proc/sys/fs/file-nr','r')
        fl = f.readline()
        f.close()
        self.filehandles = int(fl.split()[0])
        self.filehandles_limit = int(fl.split()[2])
    
    def identify_os(self):
        self.os_kernel = platform.release()
        if platform.system() == 'Linux' and platform.linux_distribution()[0] != '':
            self.os_name = ' '.join(platform.linux_distribution()[0:2])
        else:
            self.os_name = platform.system()
        self.machine = platform.machine()
        if self.machine == 'x86_64':
            self.os_arch = 'x64'
        elif self.machine[0] == 'i' and self.machine[-2:] == '86':
            self.os_arch = 'x86'
        else:
            self.os_arch = platform.machine()
    
    def calc_hardware(self):
        f = open('/proc/cpuinfo','r')
        flines = f.readlines()
        f.close()
        cpu_cores_list = [line.split('\t: ')[1].strip() for line in flines if 'model name' in line]
        if len(cpu_cores_list) == 0:
            cpu_cores_list = [line.split('\t: ')[1].strip() for line in flines if 'vendor_id' in line]
        
        if len(cpu_cores_list) != 0:
            self.cpu_name = cpu_cores_list[0]
            self.cpu_cores = len(cpu_cores_list)
        else:
            self.cpu_name = 'N/A'
            self.cpu_cores = 1
        
        try:
            self.cpu_freq = [line.split('\t: ')[1].strip() for line in flines if 'cpu MHz' in line][0]
        except:
            try:
                p = check_output(['lscpu'])
                p = p.split('\n')
                plines = [line.split() for line in p]
                plines.remove([])
                self.cpu_freq = [line[2] for line in plines if line[0]=='CPU' and line[1]=='MHz:'][0]
            except:
                self.cpu_freq = ''
        # RAM and Swap units in meminfo are in kB. We'll convert to Bytes later
        meminf  = open('/proc/meminfo','r')
        meminftext = meminf.readlines()
        meminf.close()
        meminfo = [line.split() for line in meminftext]
        self.ram_total = int([line[1] for line in meminfo if line[0]=='MemTotal:'][0])
        ram_free = int([line[1] for line in meminfo if line[0]=='MemFree:'][0])
        ram_cached = int([line[1] for line in meminfo if line[0]=='Cached:'][0])
        ram_buffers = int([line[1] for line in meminfo if line[0]=='Buffers:'][0])
        self.ram_usage = self.ram_total-(ram_free+ram_cached+ram_buffers)
        # Convert from kB to B
        self.ram_usage = self.ram_usage * 1024
        self.ram_total = self.ram_total * 1024
        # Now swap
        self.swap_total = int([line[1] for line in meminfo if line[0]=='SwapTotal:'][0])
        swap_free = int([line[1] for line in meminfo if line[0]=='SwapFree:'][0])
        self.swap_usage = self.swap_total - swap_free
        # Convert kB to B
        self.swap_usage = self.swap_usage * 1024
        self.swap_total = self.swap_total * 1024
        # Disk space
        df = check_output(['df', '-P', '-B', '1'])
        disks = [disk.split() for disk in df.split('\n')]
        disks.remove([])
        disktotvals = [disk[1] for disk in disks if disk[0][0]=='/']
        self.disk_total = '+'.join(disktotvals)
        diskusevals = [disk[2] for disk in disks if disk[0][0]=='/']
        self.disk_usage = '+'.join(diskusevals)
        disk_arr = [disk[0:3] for disk in disks if disk[0][0]=='/']
        disk_arr_txt = [' '.join(disk_arr_itm) for disk_arr_itm in disk_arr]
        disk_arr_txt.append('')
        self.disk_array = '; '.join(disk_arr_txt).strip()
    
    def calc_connections(self):
        try:
            subprocess.check_call(['command','-v','ss'],shell=True)
            connections = check_output(['ss', '-tun']).split('\n')[1:]
        except:
            connections = check_output(['netstat', '-tun']).split('\n')[2:]
        connections.remove('')
        self.connections = len(connections)
        try:
            irout = check_output(['ip', 'route', 'get', '8.8.8.8']).split()
            devidx = irout.index('dev')+1
            self.nic = irout[devidx]
        except:
            try:
                irout = check_output(['ip','link','show']).split('\n')
                irout.remove('')
                iroutarr = [rout.split() for rout in irout]
                self.nic = [rout[1][:-1] for rout in iroutarr if 'eth' in rout[1][0:3]][0]
            except:
                self.nic = 'N/A'
        # IPv4 address
        try:
            ipinfo = check_output(['ip','addr','show',self.nic]).split("inet ")[1].split("/")[0]
            ipv4 = ipinfo.strip()
            if ipv4 == '127.0.0.1':
                ipinfo = check_output(['ip','addr','show',self.nic]).split("inet ")[2].split("/")[0]
                ipv4 = ipinfo.strip()
                self.ipv4 = ipv4.strip()
            else:
                self.ipv4 = ipv4.strip()
            #print ipv4
        except:
            self.ipv4 = 'N/A'
        # IPv6 address
        try:
            ipinfo = check_output(['ip','addr','show',self.nic]).split()
            ipv6idx = ipinfo.index('inet6')+1
            ipv6 = ipinfo[ipv6idx]
            self.ipv6 = ipv6.split('/')[0]
        except:
            self.ipv6 = 'N/A'
        
        # Defaults for TX and RX
        self.tx = '0'
        self.rx = '0'
        netstatisticspath = '/sys/class/net/{0}/statistics'.format(self.nic)
        if os.path.isdir(netstatisticspath):
            rx = open(os.path.join(netstatisticspath,'rx_bytes'),'r')
            rxbytes = rx.readline()
            self.rx = rxbytes.strip()
            rx.close()
            tx = open(os.path.join(netstatisticspath,'tx_bytes'),'r')
            txbytes = tx.readline()
            self.tx = txbytes.strip()
            tx.close()
        else:
            try:
                netstats = check_output(['ip','-s','link','show',self.nic])
                netstatsplit = netstats.split('\n')
                netstatarr = [line.split() for line in netstatsplit]
                netstatarr.remove([])
                fnd = 0
                for line in netstatarr:
                    if 'TX:' in line[0]:
                        fnd = 1
                        continue
                    if fnd==1:
                        self.tx = line[0]
                        fnd=0
                fnd = 0
                for line in netstatarr:
                    if 'RX:' in line[0]:
                        fnd = 1
                        continue
                    if fnd==1:
                        self.rx = line[0]
                        fnd=0
            except:
                self.tx = '0'
                self.rx = '0'
        self.tx = int(self.tx)
        self.rx = int(self.rx)
    
    def calc_load(self):
        # Average system load
        ld = open('/proc/loadavg','r')
        ldavg = ld.read()
        self.load = " ".join(ldavg.split()[0:3])
        ld.close()
        self.time = int(time.time())
        statfile = open('/proc/stat','r')
        statf = statfile.readlines()
        statfile.close()
        stat = statf[0]
        stat = stat.split()[1:]
        stat = map(int, stat)
        self.cpu = sum(stat[0:4])
        self.io = stat[3]+stat[4]
        self.idle = stat[3]
    
    def read_msdata(self):
        if os.path.isfile(self.msdatalog):
            ms = open(self.msdatalog,'r')
            msdata = ms.read()
            ms.close()
            msdata = msdata.split()
            msdata = map(int,msdata)
            self.data = msdata
            self.interval = self.time - self.data[0]
            self.cpu_gap = self.cpu - self.data[1]
            self.io_gap = self.io - self.data[2]
            self.idle_gap = self.idle - self.data[3]
            
            if self.cpu_gap > 0:
                self.load_cpu = (1000*(self.cpu_gap-self.idle_gap)/self.cpu_gap+5)/10
            else:
                self.load_cpu = 0
            
            if self.io_gap > 0:
                self.load_io = (1000*(self.io_gap-self.idle_gap)/self.io_gap+5)/10
            else:
                self.load_io = 0
            
            if self.rx > self.data[4]:
                self.rx_gap = self.rx - self.data[4]
            else:
                self.rx_gap = 0
            
            if self.tx > self.data[5]:
                self.tx_gap = self.tx - self.data[5]
            else:
                self.tx_gap = 0
        else:
            self.interval = 0
            self.cpu_gap  = 0
            self.io_gap   = 0
            self.idle_gap = 0
            self.load_cpu = 0
            self.load_io  = 0
            self.rx_gap   = 0
            self.tx_gap   = 0
            
    def write_msdata(self):
        msdatalog = open(self.msdatalog, 'w')
        msdatalog.write("{0} {1} {2} {3} {4} {5}\n".format(self.time, self.cpu, self.io, self.idle, self.rx, self.tx))
        msdatalog.close()
    
    def get_network_latency(self):
        def get_latency(server):
            pingcmd = ['ping', '-c', '2', '-w', '2', server]
            try:
                pingout = check_output(pingcmd)
            except:
                return '0'
            pingout = pingout.split('\n')
            # Remove blank lines
            while True:
                try:
                    pingout.remove('')
                except:
                    break
            for line in pingout:
                if 'rtt min/avg/max/mdev' in line:
                    pingres = line
            pingres = pingres.split()
            # Compare to pattern: ['rtt', 'min/avg/max/mdev', '=', '245.174/246.370/247.567/1.295', 'ms']
            validx = pingres.index('=') + 1
            vals = pingres[validx]
            mdev = vals.split('/')[-1]
            return mdev
        
        self.ping_eu = get_latency('146.66.158.1')
        self.ping_us = get_latency('8.8.8.8')
        self.ping_as = get_latency('116.202.224.146')
    
    def post_msdata(self):
        datapost = [self.version,
                    self.uptime,
                    self.sessions,
                    self.processes,
                    self.processes_array,
                    self.filehandles,
                    self.filehandles_limit,
                    self.os_kernel,
                    self.os_name,
                    self.os_arch,
                    self.cpu_name,
                    self.cpu_cores,
                    self.cpu_freq,
                    self.ram_total,
                    self.ram_usage,
                    self.swap_total,
                    self.swap_usage,
                    self.disk_array,
                    self.disk_total,
                    self.disk_usage,
                    self.connections,
                    self.nic,
                    self.ipv4,
                    self.ipv6,
                    self.rx,
                    self.tx,
                    self.rx_gap,
                    self.tx_gap,
                    self.load,
                    self.load_cpu,
                    self.load_io,
                    self.ping_eu,
                    self.ping_us,
                    self.ping_as
                    ]
        # Required form is strings
        datapost = map(str,datapost)
        self.data_post_plain = datapost
        data_post_64 = map(self.base64enc, datapost)
        self.data_post = "token={auth}&data={dt}".format(auth=self.auth, dt=" ".join(data_post_64))
        post_cmd = ['wget', '-q', '-o', '/dev/null', '-O', self.ttagentlog, '-T', '25', '--post-data', self.data_post, '--no-check-certificate', 'http://tecqto.com/fetch-server-data']
        timeout_cmd = ['timeout', '-s', 'SIGKILL', '30']
        timeout_cmd_available = (subprocess.call(['command','-v','timeout'],shell=True)==0)
        
        if timeout_cmd_available:
            self.post_command = timeout_cmd + post_cmd
            retcode = subprocess.call(post_cmd)
            return retcode
        else:
            self.post_command = post_cmd
            wget_timeout = 30
            wget_counter = 0
            try:
                postproc = subprocess.Popen(self.post_command)
                while (postproc.poll()==None) and (wget_counter<wget_timeout):
                    time.sleep(1)
                    wget_counter += 1
                try:
                    postproc.terminate()
                    postproc.kill()
                except:
                    pass
                return postproc.returncode
            except:
                return 1
    
    def base64enc(self,instring):
        outstring =  b64encode(instring)
        outstring = outstring.strip('\n')    ###.strip('=')###
        outstring = outstring.replace('/','%2F').replace('+','%2B')
        return outstring


if __name__ == '__main__':
    ttagent = TTagent()
    exit()
