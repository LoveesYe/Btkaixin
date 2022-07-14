#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

install_tmp='/tmp/bt_install.pl'
public_file=/www/server/panel/install/public.sh

if [ ! -f $public_file ];then
  wget -O $public_file http://download.bt.cn/install/public.sh -T 5;
fi

. $public_file
download_Url=$NODE_URL
echo 'download url...'
echo $download_Url

pluginPath=/www/server/panel/plugin/enterprise_backup

pyVersion=$(python -c 'import sys;print(sys.version_info[0]);')
py_zi=$(python -c 'import sys;print(sys.version_info[1]);')

cpu_arch=`arch`

Install()
{
  if [[ $cpu_arch != "x86_64" ]];then
    echo '不支持非x86架构的系统安装'
    exit 0
  fi
  if [ -f "/usr/bin/apt-get" ];then
    apt install pigz -y
    apt install openssl -y
  elif [ -f "/usr/bin/yum" ];then
    yum install pigz -y
    yum install openssl -y
  fi
  mkdir -p $pluginPath
  mkdir -p $pluginPath/crontab_tasks
  mkdir -p $pluginPath/config
  rm -f $pluginPath/*.so
  \mv -f /www/server/panel/data/enterprise_backup_config/* $pluginPath/config

  echo > $pluginPath/enterprise_backup_main.py
  echo '正在安装脚本文件...' > $install_tmp
  if [  -f /www/server/panel/pyenv/bin/python ];then
    btpip install oss2
    btpip install qiniu==7.4.1 -I
    btpip install cos-python-sdk-v5
    btpip install boto3
  else
    if [ "$pyVersion" == 2 ];then
      /usr/bin/pip install oss2
      /usr/bin/pip install qiniu==7.4.1 -I
      /usr/bin/pip install cos-python-sdk-v5
      /usr/bin/pip install boto3
    else
      /usr/bin/pip3 install oss2
      /usr/bin/pip3 install qiniu==7.4.1 -I
      /usr/bin/pip3 install cos-python-sdk-v5
      /usr/bin/pip3 install boto3
    fi
  fi

  wget -O $pluginPath/enterprise_backup_main.so $download_Url/install/plugin/enterprise_backup/enterprise_backup_main.so -T 5
  wget -O $pluginPath/backup_task.so $download_Url/install/plugin/enterprise_backup/backup_task.so -T 5
  wget -O $pluginPath/enterprise_backup_main.cpython-36m-x86_64-linux-gnu.so $download_Url/install/plugin/enterprise_backup/enterprise_backup_main.cpython-36m-x86_64-linux-gnu.so -T 5
  wget -O $pluginPath/backup_task.cpython-36m-x86_64-linux-gnu.so $download_Url/install/plugin/enterprise_backup/backup_task.cpython-36m-x86_64-linux-gnu.so -T 5
  wget -O $pluginPath/enterprise_backup_main.cpython-37m-x86_64-linux-gnu.so $download_Url/install/plugin/enterprise_backup/enterprise_backup_main.cpython-37m-x86_64-linux-gnu.so -T 5
  wget -O $pluginPath/backup_task.cpython-37m-x86_64-linux-gnu.so $download_Url/install/plugin/enterprise_backup/backup_task.cpython-37m-x86_64-linux-gnu.so -T 5

  wget -O $pluginPath/upload_ftp.py $download_Url/install/plugin/enterprise_backup/upload_ftp.py -T 5
  wget -O $pluginPath/upload_alioss.py $download_Url/install/plugin/enterprise_backup/upload_alioss.py -T 5
  wget -O $pluginPath/upload_txcos.py $download_Url/install/plugin/enterprise_backup/upload_txcos.py -T 5
  wget -O $pluginPath/upload_qiniu.py $download_Url/install/plugin/enterprise_backup/upload_qiniu.py -T 5
  wget -O $pluginPath/upload_aws.py $download_Url/install/plugin/enterprise_backup/upload_aws.py -T 5
  wget -O $pluginPath/index.html $download_Url/install/plugin/enterprise_backup/index.html -T 5
  wget -O $pluginPath/info.json $download_Url/install/plugin/enterprise_backup/info.json -T 5
  wget -O $pluginPath/icon.png $download_Url/install/plugin/enterprise_backup/icon.png -T 5
  wget -O $pluginPath/crontab_tasks/mysql_full_backup.py $download_Url/install/plugin/enterprise_backup/crontab_tasks/mysql_full_backup.py -T 5
  wget -O $pluginPath/crontab_tasks/mysql_inc_backup.py $download_Url/install/plugin/enterprise_backup/crontab_tasks/mysql_inc_backup.py -T 5
  wget -O $pluginPath/crontab_tasks/path_full_backup.py $download_Url/install/plugin/enterprise_backup/crontab_tasks/path_full_backup.py -T 5
  wget -O $pluginPath/crontab_tasks/path_inc_backup.py $download_Url/install/plugin/enterprise_backup/crontab_tasks/path_inc_backup.py -T 5
  wget -O $pluginPath/crontab_tasks/log_backup.py $download_Url/install/plugin/enterprise_backup/crontab_tasks/log_backup.py -T 5
  \cp -a -r $pluginPath/icon.png /www/server/panel/BTPanel/static/img/soft_ico/ico-enterprise_backup.png
  echo '安装完成' > $install_tmp
}

Uninstall()
{
  mkdir -p /www/server/panel/data/enterprise_backup_config
  \mv -f $pluginPath/config/* /www/server/panel/data/enterprise_backup_config
  rm -rf $pluginPath
}

if [ "${1}" == 'install' ];then
  Install
elif  [ "${1}" == 'update' ];then
  Install
elif [ "${1}" == 'uninstall' ];then
  Uninstall
fi
