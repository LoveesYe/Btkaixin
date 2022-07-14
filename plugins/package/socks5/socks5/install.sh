#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
install_tmp='/tmp/bt_install.pl'
pluginPath=/www/server/panel/plugin/socks5
aacher=$(uname -a |grep -Po aarch64|awk 'NR==1')

Install_socks5()
{
	mkdir -p $pluginPath
	mkdir -p $pluginPath/config
	mkdir -p $pluginPath/total

	echo '正在安装脚本文件...' > $install_tmp
	if [ "$aacher" == "aarch64" ];then 
		cp –rf  $pluginPath/aachar64/ $pluginPath/
	fi
#	echo > $pluginPath/socks5_main.py
	initSh=/etc/init.d/bt-socks5
	cp -f $pluginPath/init.sh $initSh
	chmod +x $initSh
	if [ -f "/usr/bin/apt-get" ];then
		sudo update-rc.d bt-socks5 defaults
	else
		chkconfig --add bt-socks5
		chkconfig --level 2345 bt-socks5 on
	fi

	
	chmod -R 600 $pluginPath
	chmod 700 $pluginPath/BT-Socks5
	$initSh stop
	$initSh start
	echo > /www/server/panel/data/reload.pl
	echo '安装完成' > $install_tmp
}

Uninstall_socks5()
{
	initSh=/etc/init.d/bt-socks5
	$initSh stop
	chkconfig --del bt-socks5
	rm -rf $pluginPath
	rm -f $initSh
}


action=$1
if [ "${1}" == 'install' ];then
	Install_socks5
else
	Uninstall_socks5
fi
