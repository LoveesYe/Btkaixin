#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
mtype=$1
actionType=$2
name=$3
version=$4
. /www/server/panel/install/public.sh
serverUrl=$NODE_URL/install

if [ ! -f 'lib.sh' ];then
	wget -O lib.sh $serverUrl/$mtype/lib.sh
fi

libNull=`cat lib.sh`
if [ "$libNull" == '' ];then
	wget -O lib.sh $serverUrl/$mtype/lib.sh
fi

wget -O $name.sh $serverUrl/$mtype/$name.sh

sed -i "s/http:\/\/download.bt.cn\/install\/public.sh/http:\/\/server.fikkey.com\/install\/public.sh/" lib.sh
sed -i "s/wget -O Tpublic.sh/#wget -O Tpublic.sh/" $name.sh

if [ "$actionType" == 'install' ];then
	bash lib.sh
fi
bash $name.sh $actionType $version
echo '|-Successify --- 命令已执行! ---'
