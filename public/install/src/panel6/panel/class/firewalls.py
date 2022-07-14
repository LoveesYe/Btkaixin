#coding: utf-8
# +-------------------------------------------------------------------
# | 宝塔Linux面板 x3
# +-------------------------------------------------------------------
# | Copyright (c) 2015-2016 宝塔软件(http:#bt.cn) All rights reserved.
# +-------------------------------------------------------------------
# | Author: hwliang <hwl@bt.cn>
# +-------------------------------------------------------------------
import sys,os,public,re,firewalld,time
class firewalls:
    __isFirewalld = False
    __isUfw = False
    __Obj = None

    def __init__(self):
        if os.path.exists('/usr/sbin/firewalld'): self.__isFirewalld = True
        if os.path.exists('/usr/sbin/ufw'): self.__isUfw = True
        if self.__isFirewalld:
            try:
                self.__Obj = firewalld.firewalld()
                self.GetList()
            except:
                pass


    #获取服务端列表
    def GetList(self):
        try:
            data = {}
            data['ports'] = self.__Obj.GetAcceptPortList()
            addtime = time.strftime('%Y-%m-%d %X',time.localtime())
            for i in range(len(data['ports'])):
                tmp = self.CheckDbExists(data['ports'][i]['port'])
                if not tmp: public.M('firewall').add('port,ps,addtime',(data['ports'][i]['port'],'',addtime))

            data['iplist'] = self.__Obj.GetDropAddressList()
            for i in range(len(data['iplist'])):
                try:
                    tmp = self.CheckDbExists(data['iplist'][i]['address'])
                    if not tmp: public.M('firewall').add('port,ps,addtime',(data['iplist'][i]['address'],'',addtime))
                except:
                    pass
        except:
            pass

    #检查数据库是否存在
    def CheckDbExists(self,port):
        data = public.M('firewall').field('id,port,ps,addtime').select()
        for dt in data:
            if dt['port'] == port: return dt
        return False

    #重载防火墙配置
    def FirewallReload(self):
        if self.__isUfw:
            public.ExecShell('/usr/sbin/ufw reload &')
            return
        if self.__isFirewalld:
            public.ExecShell('firewall-cmd --reload &')
        else:
            public.ExecShell('/etc/init.d/iptables save &')
            public.ExecShell('/etc/init.d/iptables restart &')

    #取防火墙状态
    def CheckFirewallStatus(self):
        if self.__isUfw:
            res = public.ExecShell('ufw status verbose')[0]
            if res.find('inactive') != -1: return False
            return True

        if self.__isFirewalld:
            res = public.ExecShell("systemctl status firewalld")[0]
            if res.find('active (running)') != -1: return True
            if res.find('disabled') != -1: return False
            if res.find('inactive (dead)') != -1: return False
        else:
            res = public.ExecShell("/etc/init.d/iptables status")[0]
            if res.find('not running') != -1: return False
            return True

    def SetFirewallStatus(self,get=None):
        '''
            @name 设置系统防火墙状态
            @author hwliang<2022-01-13>
        '''
        status = not self.CheckFirewallStatus()
        status_msg = {False: '关闭', True: '开启'}
        if self.__isUfw:
            if status:
                public.ExecShell('echo y|ufw enable')
            else:
                public.ExecShell('echo y|ufw disable')
        if self.__isFirewalld:
            if status:
                public.ExecShell('systemctl enable firewalld')
                public.ExecShell('systemctl start firewalld')
            else:
                public.ExecShell('systemctl disable firewalld')
                public.ExecShell('systemctl stop firewalld')
        else:
            if status:
                public.ExecShell("chkconfig iptables on")
                public.ExecShell('/etc/init.d/iptables start')
            else:
                public.ExecShell("chkconfig iptables off")
                public.ExecShell('/etc/init.d/iptables stop')
        public.WriteLog('TYPE_FIREWALL','{}系统防火墙'.format(status_msg[status]))
        return public.returnMsg(True,'已{}系统防火墙'.format(status_msg[status]))

    #添加屏蔽IP
    def AddDropAddress(self,get):
        if not self.CheckFirewallStatus(): return public.returnMsg(False,'当前系统防火墙未开启')
        import time
        import re
        ip_format = get.port.split('/')[0]
        if not public.check_ip(ip_format): return public.returnMsg(False,'FIREWALL_IP_FORMAT')
        # if public.is_ipv6(ip_format): return public.returnMsg(False,'暂不支持屏蔽IPv6')
        if ip_format in  ['0.0.0.0','127.0.0.0',"::1"]: return public.returnMsg(False,'请不要花样作死!')
        address = get.port
        if public.M('firewall').where("port=?",(address,)).count() > 0: return public.returnMsg(False,'FIREWALL_IP_EXISTS')
        if self.__isUfw:
            if public.is_ipv6(ip_format):
                public.ExecShell('ufw deny from ' + address + ' to any')
            else:
                public.ExecShell('ufw insert 1 deny from ' + address + ' to any')
        else:
            if self.__isFirewalld:
                #self.__Obj.AddDropAddress(address)
                if public.is_ipv6(ip_format):
                    public.ExecShell('firewall-cmd --permanent --add-rich-rule=\'rule family=ipv6 source address="'+ address +'" drop\'')
                else:
                    public.ExecShell('firewall-cmd --permanent --add-rich-rule=\'rule family=ipv4 source address="'+ address +'" drop\'')
            else:
                if public.is_ipv6(ip_format): return public.returnMsg(False,'FIREWALL_IP_FORMAT')
                public.ExecShell('iptables -I INPUT -s '+address+' -j DROP')

        public.WriteLog("TYPE_FIREWALL", 'FIREWALL_DROP_IP',(address,))
        addtime = time.strftime('%Y-%m-%d %X',time.localtime())
        public.M('firewall').add('port,ps,addtime',(address,get.ps,addtime))
        self.FirewallReload()
        return public.returnMsg(True,'ADD_SUCCESS')


    #删除IP屏蔽
    def DelDropAddress(self,get):
        if not self.CheckFirewallStatus(): return public.returnMsg(False,'当前系统防火墙未开启')
        address = get.port
        id = get.id
        ip_format = get.port.split('/')[0]

        if self.__isUfw:
            public.ExecShell('ufw delete deny from ' + address + ' to any')
        else:
            if self.__isFirewalld:
                if public.is_ipv6(ip_format):
                    public.ExecShell('firewall-cmd --permanent --remove-rich-rule=\'rule family=ipv6 source address="'+ address +'" drop\'')
                else:
                    public.ExecShell('firewall-cmd --permanent --remove-rich-rule=\'rule family=ipv4 source address="'+ address +'" drop\'')
            else:
                public.ExecShell('iptables -D INPUT -s '+address+' -j DROP')

        public.WriteLog("TYPE_FIREWALL",'FIREWALL_ACCEPT_IP',(address,))
        public.M('firewall').where("id=?",(id,)).delete()

        self.FirewallReload()
        return public.returnMsg(True,'DEL_SUCCESS')


    #添加放行端口
    def AddAcceptPort(self,get):
        if not self.CheckFirewallStatus(): return public.returnMsg(False,'当前系统防火墙未开启')
        import re
        src_port = get.port
        get.port = get.port.replace('-',':')
        rep = r"^\d{1,5}(:\d{1,5})?$"
        if not re.search(rep,get.port):
            return public.returnMsg(False,'PORT_CHECK_RANGE')

        import time
        port = get.port
        ps = public.xssencode2(get.ps)
        is_exists = public.M('firewall').where("port=? or port=?",(port,src_port)).count()
        if is_exists: return public.returnMsg(False,'端口已经放行过了!')
        notudps = ['80','443','8888','888','39000:40000','21','22']
        if self.__isUfw:
            public.ExecShell('ufw allow ' + port + '/tcp')
            if not port in notudps: public.ExecShell('ufw allow ' + port + '/udp')
        else:
            if self.__isFirewalld:
                #self.__Obj.AddAcceptPort(port)
                port = port.replace(':','-')
                public.ExecShell('firewall-cmd --permanent --zone=public --add-port='+port+'/tcp')
                if not port in notudps: public.ExecShell('firewall-cmd --permanent --zone=public --add-port='+port+'/udp')
            else:
                public.ExecShell('iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport '+port+' -j ACCEPT')
                if not port in notudps: public.ExecShell('iptables -I INPUT -p tcp -m state --state NEW -m udp --dport '+port+' -j ACCEPT')
        public.WriteLog("TYPE_FIREWALL", 'FIREWALL_ACCEPT_PORT',(port,))
        addtime = time.strftime('%Y-%m-%d %X',time.localtime())
        if not is_exists: public.M('firewall').add('port,ps,addtime',(port,ps,addtime))
        self.FirewallReload()
        return public.returnMsg(True,'ADD_SUCCESS')


    #添加放行端口
    def AddAcceptPortAll(self,port,ps):
        if not self.CheckFirewallStatus(): return public.returnMsg(False,'当前系统防火墙未开启')
        import re
        port = port.replace('-',':')
        rep = r"^\d{1,5}(:\d{1,5})?$"
        if not re.search(rep,port):
            return False
        if self.__isUfw:
            public.ExecShell('ufw allow ' + port + '/tcp')
            public.ExecShell('ufw allow ' + port + '/udp')
        else:
            if self.__isFirewalld:
                port = port.replace(':','-')
                public.ExecShell('firewall-cmd --permanent --zone=public --add-port='+port+'/tcp')
                public.ExecShell('firewall-cmd --permanent --zone=public --add-port='+port+'/udp')
            else:
                public.ExecShell('iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport '+port+' -j ACCEPT')
                public.ExecShell('iptables -I INPUT -p tcp -m state --state NEW -m udp --dport '+port+' -j ACCEPT')
        return True

    #删除放行端口
    def DelAcceptPort(self,get):
        if not self.CheckFirewallStatus(): return public.returnMsg(False,'当前系统防火墙未开启')
        port = get.port
        id = get.id

        if public.is_ipv6(port): return self.DelDropAddress(get) # 如果是ipv6地址，则调用DelDropAddress

        try:
            if(port == public.GetHost(True) or port == public.readFile('data/port.pl').strip()): return public.returnMsg(False,'FIREWALL_PORT_PANEL')
            if self.__isUfw:
                public.ExecShell('ufw delete allow ' + port + '/tcp')
                public.ExecShell('ufw delete allow ' + port + '/udp')
            else:
                if self.__isFirewalld:
                    #self.__Obj.DelAcceptPort(port)
                    public.ExecShell('firewall-cmd --permanent --zone=public --remove-port='+port+'/tcp')
                    public.ExecShell('firewall-cmd --permanent --zone=public --remove-port='+port+'/udp')
                else:
                    public.ExecShell('iptables -D INPUT -p tcp -m state --state NEW -m tcp --dport '+port+' -j ACCEPT')
                    public.ExecShell('iptables -D INPUT -p tcp -m state --state NEW -m udp --dport '+port+' -j ACCEPT')
            public.WriteLog("TYPE_FIREWALL", 'FIREWALL_DROP_PORT',(port,))
            public.M('firewall').where("id=?",(id,)).delete()

            self.FirewallReload()
            return public.returnMsg(True,'DEL_SUCCESS')
        except:
            return public.returnMsg(False,'DEL_ERROR')

    #设置远程端口状态
    def SetSshStatus(self,get):
        # version = public.readFile('/etc/redhat-release')
        if int(get['status'])==1:
            msg = public.getMsg('FIREWALL_SSH_STOP')
            act = 'stop'
        else:
            msg = public.getMsg('FIREWALL_SSH_START')
            act = 'start'

        # if not os.path.exists('/etc/redhat-release'):
        #     public.ExecShell('service ssh ' + act)
        # elif version.find(' 7.') != -1 or version.find(' 8.') != -1 or version.find('Fedora') != -1:
        #     public.ExecShell("systemctl "+act+" sshd")
        # else:
        # 全试一次?
        public.ExecShell("/etc/init.d/sshd "+act)
        public.ExecShell('service ssh ' + act)
        public.ExecShell("systemctl "+act+" sshd")
        public.ExecShell("systemctl "+act+" ssh")

        public.WriteLog("TYPE_FIREWALL", msg)
        return public.returnMsg(True,'SUCCESS')




    #设置ping
    def SetPing(self,get):
        if get.status == '1':
            get.status = '0'
        else:
            get.status = '1'
        filename = '/etc/sysctl.conf'
        conf = public.readFile(filename)
        if conf.find('net.ipv4.icmp_echo') != -1:
            rep = r"net\.ipv4\.icmp_echo.*"
            conf = re.sub(rep,'net.ipv4.icmp_echo_ignore_all='+get.status,conf)
        else:
            conf += "\nnet.ipv4.icmp_echo_ignore_all="+get.status


        public.writeFile(filename,conf)
        public.ExecShell('sysctl -p')
        return public.returnMsg(True,'SUCCESS')



    #改远程端口
    def SetSshPort(self,get):
        port = get.port
        if int(port) < 22 or int(port) > 65535: return public.returnMsg(False,'FIREWALL_SSH_PORT_ERR')
        ports = ['21','25','80','443','8080','888','8888']
        if port in ports: return public.returnMsg(False,'请不要使用常用程序的默认端口!')
        file = '/etc/ssh/sshd_config'
        conf = public.readFile(file)

        rep = r"#*Port\s+([0-9]+)\s*\n"
        conf = re.sub(rep, "Port "+port+"\n", conf)
        public.writeFile(file,conf)

        if self.__isFirewalld:
            public.ExecShell('firewall-cmd --permanent --zone=public --add-port='+port+'/tcp')
            public.ExecShell('setenforce 0')
            public.ExecShell('sed -i "s#SELINUX=enforcing#SELINUX=disabled#" /etc/selinux/config')
            public.ExecShell("systemctl restart sshd.service")
        elif self.__isUfw:
            public.ExecShell('ufw allow ' + port + '/tcp')
            public.ExecShell("service ssh restart")
        else:
            public.ExecShell('iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport '+port+' -j ACCEPT')
            public.ExecShell("/etc/init.d/sshd restart")

        self.FirewallReload()
        public.M('firewall').where("ps=? or ps=? or port=?",('SSH远程管理服务','SSH远程服务',port)).delete()
        public.M('firewall').add('port,ps,addtime',(port,'SSH远程服务',time.strftime('%Y-%m-%d %X',time.localtime())))
        public.WriteLog("TYPE_FIREWALL", "FIREWALL_SSH_PORT",(port,))
        return public.returnMsg(True,'EDIT_SUCCESS')

    #取SSH信息
    def GetSshInfo(self,get):
        port = public.get_sshd_port()
        status = public.get_sshd_status()
        isPing = True
        try:
            file = '/etc/sysctl.conf'
            conf = public.readFile(file)
            rep = r"#*net\.ipv4\.icmp_echo_ignore_all\s*=\s*([0-9]+)"
            tmp = re.search(rep,conf).groups(0)[0]
            if tmp == '1': isPing = False
        except:
            isPing = True

        data = {}
        data['port'] = port
        data['status'] = status
        data['ping'] = isPing
        data['firewall_status'] = self.CheckFirewallStatus()
        return data

