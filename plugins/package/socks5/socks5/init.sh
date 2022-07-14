#!/bin/bash
# chkconfig: 2345 55 25
# description: bt.cn BT-Socks5

### BEGIN INIT INFO
# Provides:          BT-Socks5
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: starts BT-Socks5
# Description:       starts the BT-Socks5
### END INIT INFO

panel_path=/www/server/panel
pidfile=$panel_path/logs/panel.pid
cd $panel_path
env_path=$panel_path/pyenv/bin/activate
if [ -f $env_path ];then
        source $env_path
        pythonV=$panel_path/pyenv/bin/python
        chmod -R 700 $panel_path/pyenv/bin
else
        pythonV=/usr/bin/python
fi

pid_file=$panel_path/logs/socks5.pid
log_file=$panel_path/logs/socks5.log
bin_file=$panel_path/plugin/socks5/BT-Socks5
sed -i "s@^#!.*@#!$pythonV@" $bin_file

cd $panel_path
panel_start()
{        
        if [ ! -f $pid_file ];then
                echo -e "Starting BT-Socks5 service... \c"
                $bin_file &> /dev/null
                sleep 0.5
                isStart=`ps aux |grep BT-Socks5|grep -v grep|awk '{print $2}'`
                if [ "$isStart" == '' ];then
                        echo -e "\033[31mfailed\033[0m"
                        echo '------------------------------------------------------'
                        cat $log_file
                        echo '------------------------------------------------------'
                        echo -e "\033[31mError: BT-Socks5 service startup failed.\033[0m"
                        return;
                fi
                echo -e "\033[32mdone\033[0m"
        else
                pid=$(cat $pid_file)
                echo "Starting  BT-Socks5 service (pid $pid) already running"
        fi
}

panel_stop()
{
	echo -e "Stopping BT-Socks5 service... \c";
        pid=$(cat $pid_file)
        kill -9 $pid
        rm -f $pid_file
        pids=$(ps aux |grep BT-Socks5|grep -v grep|grep -v PID|awk '{print $2}')
        if [ "$pids" != "" ];then
                kill -9 $pids
        fi
        echo -e "\033[32mdone\033[0m"
}

panel_status()
{
        pid=$(cat $pid_file)
        if [ "$pid" != '' ];then
                echo -e "\033[32mBT-Socks5 service (pid $pid) already running\033[0m"
        else
                echo -e "\033[31mBT-Socks5 service not running\033[0m"
        fi
}

case "$1" in
        'start')
                panel_start
                ;;
        'stop')
                panel_stop
                ;;
        'restart')
                panel_stop
                sleep 0.2
                panel_start
                ;;
        'reload')
                panel_stop
                sleep 0.2
                panel_start
                ;;
        'status')
                panel_status
                ;;
        *)
                echo "Usage: /etc/init.d/bt-socks5 {start|stop|restart|reload}"
        ;;
esac