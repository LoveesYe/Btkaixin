#coding: utf-8
# +-------------------------------------------------------------------
# | 宝塔Linux面板
# +-------------------------------------------------------------------
# | Copyright (c) 2015-2099 宝塔软件(http://bt.cn) All rights reserved.
# +-------------------------------------------------------------------
# | Author: 王张杰 <750755014@qq.com>
# +-------------------------------------------------------------------

# +--------------------------------------------------------------------
# |   企业级备份
# +--------------------------------------------------------------------
import sys
import os
import re
import json
import time
import shutil
import glob

os.chdir("/www/server/panel")
sys.path.append("/www/server/panel/class/")
import public
from panelMysql import panelMysql
try:
    import crontab
except:
    pass

sys.path.insert(0, '/www/server/panel/plugin/enterprise_backup')
from enterprise_backup_main import enterprise_backup_main


class BackupTask(enterprise_backup_main):
    __log_type = '企业级备份'
    __mysql_conf_file = "/etc/my.cnf"
    __tar_pass_file = "/www/server/panel/data/tar_pass"
    __tar_pass = ""
    __plugin_path = '/www/server/panel/plugin/enterprise_backup'
    __configPath = os.path.join(__plugin_path, 'config')
    __encrypt_file = os.path.join(__configPath, 'encrypt.pl')
    __mysql_backup_log_file = os.path.join(__plugin_path, 'mysql_backup_log_')
    __mysql_restore_log_file = os.path.join(__plugin_path, 'mysql_restore_log')
    __path_backup_log_file = os.path.join(__plugin_path, 'path_backup_log_')
    __path_restore_log_file = os.path.join(__plugin_path, 'path_restore_log')
    __log_backup_output_file = os.path.join(__plugin_path, 'log_backup_output')

    def __init__(self):
        super(BackupTask, self).__init__()

        if not os.path.exists(self.__configPath):
            os.makedirs(self.__configPath)
        # 生成随机的tar命令压缩密码
        self.__tar_pass = public.readFile(self.__tar_pass_file)
        if not self.__tar_pass:
            self.__tar_pass = public.GetRandomString(6)
            public.writeFile(self.__tar_pass_file, self.__tar_pass)

        self.__backup_path = public.readFile(self.__configPath + '/local.conf')
        if not self.__backup_path:
            return

        # mysql备份相关配置
        self.__database_path = os.path.join(self.__backup_path, 'database')
        self.__full_backup_path = os.path.join(self.__database_path, 'full')
        self.__ddl_backup_path = os.path.join(self.__database_path, 'ddl')
        self.__last_full_backup_path = os.path.join(self.__full_backup_path, 'last')
        self.__inc_backup_path = os.path.join(self.__database_path, 'inc')

        # 目录备份相关配置
        self.__dir_backup = os.path.join(self.__backup_path, 'path')
        self.__dir_full_backup = os.path.join(self.__dir_backup, 'full')
        self.__dir_last_full_backup = os.path.join(self.__dir_full_backup, 'last')
        self.__dir_inc_backup = os.path.join(self.__dir_backup, 'inc')

        # 日志备份相关配置
        self.__log_backup_path = os.path.join(self.__backup_path, 'log')
        self.__website_log_backup_path = os.path.join(self.__log_backup_path, 'website')
        self.__mysql_log_backup_path = os.path.join(self.__log_backup_path, 'mysql')
        self.__secure_log_backup_path = os.path.join(self.__log_backup_path, 'secure')
        self.__messages_log_backup_path = os.path.join(self.__log_backup_path, 'messages')

        # 创建日志备份相关目录
        if not os.path.exists(self.__log_backup_path):
            os.makedirs(self.__log_backup_path, 384)
        if not os.path.exists(self.__website_log_backup_path):
            os.makedirs(self.__website_log_backup_path, 384)
        if not os.path.exists(self.__mysql_log_backup_path):
            os.makedirs(self.__mysql_log_backup_path, 384)
        if not os.path.exists(self.__secure_log_backup_path):
            os.makedirs(self.__secure_log_backup_path, 384)
        if not os.path.exists(self.__messages_log_backup_path):
            os.makedirs(self.__messages_log_backup_path, 384)

    # 获取逻辑cpu个数的一半
    def get_half_cpu(self):
        import psutil

        cpu_count = psutil.cpu_count() / 2
        if cpu_count < 1:
            cpu_count = 1
        else:
            cpu_count = int(cpu_count)
        return cpu_count

    # mysql全量备份
    def mysql_full_backup(self, sid):
        backup_log_file = self.__mysql_backup_log_file + str(sid) + '_full'
        # while True:
        #     if not os.path.exists(backup_log_file): break
        #     time.sleep(3)
        if self.get_innodb_file_per_table().upper() != 'ON':
            return public.returnMsg(False, u'innodb_file_per_table设置未打开!')
        if not self.check_version_suitable():
            self.repair_version_suitable()
        setting_info = public.M('mysql_backup_setting').where('id=?', sid).find()
        database = setting_info['database']
        root_pass = self.get_mysql_root()
        today = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        database_backup_path = os.path.join(self.__full_backup_path, database)
        if not os.path.exists(database_backup_path):
            os.makedirs(database_backup_path, 384)
        backup_path = os.path.join(database_backup_path, today)
        self.remove_dir(backup_path)
        start_time = time.time()
        public.writeFile(backup_log_file, "数据库[{}]开始全量备份\n".format(database))
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), u'数据库[{}]开始全量备份'.format(database))

        try:
            cmd = 'xtrabackup --backup --parallel={} --password={} --databases="{}" --target-dir={} --no-timestamp >> {} 2>&1'.format(
                self.get_half_cpu(), root_pass, database, backup_path, backup_log_file)
            public.writeFile(backup_log_file, '全量备份数据库[{}]命令：{}\n'.format(database, cmd), 'a+')
            public.ExecShell(cmd)
            output = public.GetNumLines(backup_log_file, 10)
            if 'completed OK!' in output:
                # 加密压缩备份目录
                # print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), u'开始压缩全量备份文件[{}]'.format(backup_path))
                if os.path.exists(self.__encrypt_file):
                    tar_pass = self.__tar_pass
                else:
                    tar_pass = '未加密'
                result = self.compress_dir(backup_path, tar_pass, backup_log_file)
                if not result['status']:
                    self.remove_dir(backup_path)
                    os.remove(backup_log_file)
                    return result
                # print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), u'压缩全量备份文件[{}]完成'.format(backup_path))
                database_last_full_backup = os.path.join(self.__last_full_backup_path, database)
                self.remove_dir(database_last_full_backup)
                shutil.copytree(backup_path, database_last_full_backup)
                self.remove_dir(backup_path)
                file_path = backup_path + '.tar.gz'
                if not public.M('mysql_full_backup').where('sid=? and file_path=?', (sid, file_path)).count():
                    public.M('mysql_full_backup').add('sid,file_path,tar_pass,addtime,cost_time', (sid, file_path, tar_pass, int(time.time()), round(time.time() - start_time, 2)))
                else:
                    public.M('mysql_full_backup').where('sid=? and file_path=?', (sid, file_path)).save('tar_pass,addtime,cost_time', (tar_pass, int(time.time()), round(time.time() - start_time, 2)))
                # 上传备份到ftp
                if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and setting_info['upload_ftp']:
                    self.mysql_upload_cloud('ftp', 'full', file_path, database, backup_log_file)
                # 上传备份到阿里云oss
                if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and setting_info['upload_alioss']:
                    self.mysql_upload_cloud('alioss', 'full', file_path, database, backup_log_file)
                # 上传备份到腾讯cos
                if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and setting_info['upload_txcos']:
                    self.mysql_upload_cloud('txcos', 'full', file_path, database, backup_log_file)
                # 上传备份到七牛云存储
                if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and setting_info['upload_qiniu']:
                    self.mysql_upload_cloud('qiniu', 'full', file_path, database, backup_log_file)
                # 上传备份到亚马逊S3云存储
                if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and setting_info['upload_aws']:
                    self.mysql_upload_cloud('aws', 'full', file_path, database, backup_log_file)
                # 如果设置本地不保存
                if not setting_info['upload_local'] and os.path.exists(file_path):
                    os.remove(file_path)
                # 删除全量备份的旧记录
                sql = 'select id from mysql_full_backup where sid={} order by id desc limit (select count(*) from mysql_full_backup) offset {}'.format(sid, setting_info['full_backup_save'])
                full_backup_delete = public.M('').query(sql)
                for item in full_backup_delete:
                    self.delete_mysql_full_backup(item[0], delete_cloud=True)
                public.writeFile(backup_log_file, '全量备份数据库[{}]完成，耗时：{}秒'.format(database, time.time() - start_time), 'a+')
                os.remove(backup_log_file)
                return public.returnMsg(True, u'全量备份数据库[{}]完成，耗时：{}秒'.format(database, round(time.time() - start_time, 2)))
            else:
                self.remove_dir(backup_path)
                os.remove(backup_log_file)
                return public.returnMsg(False, u'全量备份数据库[{}]失败，原因：{}'.format(database, output))
        except:
            self.remove_dir(backup_path)
            os.remove(backup_log_file)
            return public.returnMsg(False, u'全量备份数据库[{}]失败，原因：{}'.format(database, public.get_error_info()))

    # mysql增量备份
    def mysql_inc_backup(self, sid):
        backup_log_file = self.__mysql_backup_log_file + str(sid) + '_inc'
        # 判断是否有其他的增量备份任务
        # while True:
        #     if not os.path.exists(backup_log_file): break
        #     time.sleep(3)
        if self.get_innodb_file_per_table().upper() != 'ON':
            return public.returnMsg(False, u'innodb_file_per_table设置未打开!')
        if not self.check_version_suitable():
            self.repair_version_suitable()
        setting_info = public.M('mysql_backup_setting').where('id=?', sid).find()
        database = setting_info['database']
        # 等待全量备份任务完成
        echo = public.M('crontab').where("name=?", "[勿删]企业级备份-数据库全量备份任务[{}]".format(database)).getField('echo')
        execstr = public.GetConfigValue('setup_path') + '/cron/' + echo
        while True:
            if not self.process_exists(execstr): break
            time.sleep(3)

        public.writeFile(backup_log_file, "数据库[{}]开始增量备份\n".format(database))
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), u'数据库[{}]开始增量备份'.format(database))
        start_time = time.time()
        database_last_full_backup_path = os.path.join(self.__last_full_backup_path, database)
        if not public.get_path_size(database_last_full_backup_path) or not public.M('mysql_full_backup').where('sid=?', sid).count():
            public.writeFile(backup_log_file, '第一次增量备份数据库[{}]之前要先进行一次全量备份\n'.format(database), 'a+')
            print(u'第一次增量备份数据库[{}]之前要先进行一次全量备份'.format(database))
            self.start_mysql_full_backup_task(database)
        root_pass = self.get_mysql_root()
        str_time = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        database_backup_path = os.path.join(self.__inc_backup_path, database)
        if not os.path.exists(database_backup_path):
            os.makedirs(database_backup_path, 384)
        backup_path = os.path.join(database_backup_path, str_time)
        self.remove_dir(backup_path)

        try:
            cmd = 'xtrabackup --backup --parallel={} --password={} --databases="{}" --target-dir={} --no-timestamp --incremental-basedir={} >> {} 2>&1'.format(
                self.get_half_cpu(), root_pass, database, backup_path, database_last_full_backup_path, backup_log_file)
            public.writeFile(backup_log_file, '增量备份数据库[{}]命令：{}\n'.format(database, cmd), 'a+')
            public.ExecShell(cmd)
            output = public.GetNumLines(backup_log_file, 10)
            if 'completed OK!' in output:
                # 加密压缩备份目录
                if os.path.exists(self.__encrypt_file):
                    tar_pass = self.__tar_pass
                else:
                    tar_pass = '未加密'
                result = self.compress_dir(backup_path, tar_pass, backup_log_file)
                if not result['status']:
                    self.remove_dir(backup_path)
                    os.remove(backup_log_file)
                    return result
                self.remove_dir(backup_path)
                last_full_backup = public.M('mysql_full_backup').where('sid=?', sid).order('id desc').find()
                inc_file_path = backup_path + '.tar.gz'
                public.M('mysql_inc_backup').add('sid,fid,inc_file_path,full_file_path,tar_pass,addtime,cost_time',
                                                 (sid, last_full_backup['id'], inc_file_path, last_full_backup['file_path'], tar_pass, int(time.time()), round(time.time() - start_time, 2)))
                # 上传备份到ftp
                if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and setting_info['upload_ftp']:
                    self.mysql_upload_cloud('ftp', 'inc', inc_file_path, database, backup_log_file)
                # 上传备份到阿里云oss
                if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and setting_info['upload_alioss']:
                    self.mysql_upload_cloud('alioss', 'inc', inc_file_path, database, backup_log_file)
                # 上传备份到腾讯cos
                if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and setting_info['upload_txcos']:
                    self.mysql_upload_cloud('txcos', 'inc', inc_file_path, database, backup_log_file)
                # 上传备份到七牛云存储
                if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and setting_info['upload_qiniu']:
                    self.mysql_upload_cloud('qiniu', 'inc', inc_file_path, database, backup_log_file)
                # 上传备份到亚马逊S3云存储
                if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and setting_info['upload_aws']:
                    self.mysql_upload_cloud('aws', 'inc', inc_file_path, database, backup_log_file)
                # 如果设置本地不保存
                if not setting_info['upload_local'] and os.path.exists(inc_file_path):
                    os.remove(inc_file_path)
                # 删除增量备份的旧记录
                sql = 'select id from mysql_inc_backup where sid={} order by id desc limit (select count(*) from mysql_inc_backup) offset {}'.format(sid, setting_info['inc_backup_save'])
                inc_backup_delete = public.M('').query(sql)
                for item in inc_backup_delete:
                    self.delete_mysql_inc_backup(item[0], delete_cloud=True)
                public.writeFile(backup_log_file, '增量备份数据库[{}]完成，耗时：{}秒'.format(database, time.time() - start_time), 'a+')
                os.remove(backup_log_file)
                return public.returnMsg(True, u'增量备份数据库[{}]完成，耗时：{}秒'.format(database, round(time.time() - start_time, 2)))
            else:
                self.remove_dir(backup_path)
                os.remove(backup_log_file)
                return public.returnMsg(False, u'增量备份数据库[{}]失败，原因：{}'.format(database, output))
        except:
            self.remove_dir(backup_path)
            os.remove(backup_log_file)
            return public.returnMsg(False, u'增量备份数据库[{}]失败，原因：{}'.format(database, public.get_error_info))

    # 备份数据库表结构
    def mysql_ddl_backup(self, sid):
        setting_info = public.M('mysql_backup_setting').where('id=?', sid).find()
        database = setting_info['database']
        root_pass = self.get_mysql_root()
        today_hour = time.strftime('%Y-%m-%d-%H', time.localtime())
        backup_path = os.path.join(self.__ddl_backup_path, database)
        if not os.path.exists(backup_path):
            os.makedirs(backup_path, 384)
        filename = os.path.join(backup_path, '{}.sql.gz'.format(today_hour))

        if '.' in database:
            db_name, table_name = database.split('.')
            cmd = '/www/server/mysql/bin/mysqldump -uroot -p{} -d -f --skip-add-drop-table -B {} --tables {} | gzip > {}'.format(root_pass, db_name, table_name, filename)
        else:
            db_name = database
            cmd = '/www/server/mysql/bin/mysqldump -uroot -p{} -d -f --skip-add-drop-table -B {} | gzip > {}'.format(root_pass, db_name, filename)
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), u'开始数据库[{}]表结构备份!'.format(db_name))
        # print(u'备份数据库{}表结构语句：{}'.format(db_name, cmd))
        public.ExecShell(cmd)

        if not os.path.exists(filename):
            print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), u'数据库[{}]表结构备份失败!'.format(db_name))
        else:
            print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), u'数据库[{}]表结构备份完成!'.format(db_name))
            # 上传备份到ftp
            if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and setting_info['upload_ftp']:
                self.mysql_upload_cloud('ftp', 'ddl', filename, database)
            # 上传备份到阿里云oss
            if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and setting_info['upload_alioss']:
                self.mysql_upload_cloud('alioss', 'ddl', filename, database)
            # 上传备份到腾讯cos
            if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and setting_info['upload_txcos']:
                self.mysql_upload_cloud('txcos', 'ddl', filename, database)
            # 上传备份到七牛云存储
            if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and setting_info['upload_qiniu']:
                self.mysql_upload_cloud('qiniu', 'ddl', filename, database)
            # 上传备份到亚马逊S3云存储
            if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and setting_info['upload_aws']:
                self.mysql_upload_cloud('aws', 'ddl', filename, database)

    # mysql上传备份文件到云端存储
    def mysql_upload_cloud(self, storage_type, backup_type, local_file, database, backup_log_file=None):
        get = public.dict_obj()
        get.path = '/'
        if backup_type == 'full':
            get.dirname = 'enterprise_backup/database/full/' + database
        elif backup_type == 'inc':
            get.dirname = 'enterprise_backup/database/inc/' + database
        elif backup_type == 'ddl':
            get.dirname = 'enterprise_backup/database/ddl/' + database

        self.upload_cloud(get, storage_type, local_file, backup_log_file)

    # 目录全量备份
    def path_full_backup(self, sid):
        backup_log_file = self.__path_backup_log_file + str(sid) + '_full'
        # while True:
        #     if not os.path.exists(backup_log_file): break
        #     time.sleep(3)
        setting_info = public.M('path_backup_setting').where('id=?', sid).find()
        path = setting_info['path']

        start_time = time.time()
        public.writeFile(backup_log_file, "目录[{}]开始全量备份\n".format(path))
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), '目录[{}]开始全量备份'.format(path))
        backup_path = os.path.join(self.__dir_full_backup, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()) + path.replace('/', '_'))
        self.remove_dir(backup_path)

        try:
            os.makedirs(backup_path, 384)
            tar_file = backup_path + '/full_backup.tar.gz'
            snapshot_file = backup_path + '/snapshot'
            cmd = 'cd {0} && tar -g {1} -zcvf {2} {3} {4} >> {5} 2>&1'.format(
                os.path.dirname(path), snapshot_file, tar_file, self.get_exclude(setting_info['exclude']), os.path.basename(path), backup_log_file)
            public.writeFile(backup_log_file, '全量备份目录[{}]命令：{}'.format(path, cmd), 'a+')
            public.ExecShell(cmd)
            if public.get_path_size(backup_path) > 100:
                # print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), '目录[{}]全量备份完成'.format(path))
                # 加密压缩备份目录
                if os.path.exists(self.__encrypt_file):
                    tar_pass = self.__tar_pass
                else:
                    tar_pass = '未加密'
                result = self.compress_dir(backup_path, tar_pass, backup_log_file)
                if not result['status']:
                    self.remove_dir(backup_path)
                    os.remove(backup_log_file)
                    return result
                path_last_full_backup = os.path.join(self.__dir_last_full_backup, path.replace('/', '_'))
                self.remove_dir(path_last_full_backup)
                shutil.copytree(backup_path, path_last_full_backup)
                self.remove_dir(backup_path)
                file_path = backup_path + '.tar.gz'
                if not public.M('path_full_backup').where('sid=? and file_path=?', (setting_info['id'], file_path)).count():
                    public.M('path_full_backup').add('sid,file_path,tar_pass,addtime,cost_time', (setting_info['id'], file_path, tar_pass, int(time.time()), round(time.time() - start_time, 2)))
                else:
                    public.M('path_full_backup').where('file_path=?', file_path).save('tar_pass,addtime,cost_time', (tar_pass, int(time.time()), round(time.time() - start_time, 2)))
                # 上传备份到ftp
                if setting_info['upload_ftp'] and os.path.exists(os.path.join(self.__configPath, 'ftp.conf')):
                    self.path_upload_cloud('ftp', 'full', file_path)
                # 上传备份到alioss
                if setting_info['upload_alioss'] and os.path.exists(os.path.join(self.__configPath, 'alioss.conf')):
                    self.path_upload_cloud('alioss', 'full', file_path)
                # 上传备份到txcos
                if setting_info['upload_txcos'] and os.path.exists(os.path.join(self.__configPath, 'txcos.conf')):
                    self.path_upload_cloud('txcos', 'full', file_path)
                # 上传备份到七牛云存储
                if setting_info['upload_qiniu'] and os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')):
                    self.path_upload_cloud('qiniu', 'full', file_path)
                # 上传备份到亚马逊S3云存储
                if setting_info['upload_aws'] and os.path.exists(os.path.join(self.__configPath, 'aws.conf')):
                    self.path_upload_cloud('aws', 'full', file_path)
                # 如果设置本地不保存
                if not setting_info['upload_local'] and os.path.exists(file_path):
                    os.remove(file_path)
                # 删除全量备份的旧记录
                sql = 'select id from path_full_backup where sid={} order by id desc limit (select count(*) from path_full_backup) offset {}'.format(
                    sid, setting_info['full_backup_save'])
                full_backup_delete = public.M('').query(sql)
                for item in full_backup_delete:
                    self.delete_path_full_backup(item[0], delete_cloud=True)
            else:
                self.remove_dir(backup_path)
                print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), '目录[{}]全量备份失败, 生成的备份目录过小'.format(path))
            os.remove(backup_log_file)
            return public.returnMsg(True, '全量备份目录[{}]完成，耗时：{}'.format(path, round(time.time() - start_time, 2)))
        except:
            self.remove_dir(backup_path)
            os.remove(backup_log_file)
            return public.returnMsg(False, '全量备份目录[{}]失败, 原因：{}'.format(path, public.get_error_info()))

    # 目录增量备份
    def path_inc_backup(self, sid):
        backup_log_file = self.__path_backup_log_file + str(sid) + '_inc'
        # while True:
        #     if not os.path.exists(backup_log_file): break
        #     time.sleep(3)
        setting_info = public.M('path_backup_setting').where('id=?', sid).find()
        path = setting_info['path']
        # 等待全量备份任务完成
        echo = public.M('crontab').where("name=?", "[勿删]企业级备份-目录全量备份任务[{}]".format(path)).getField('echo')
        execstr = public.GetConfigValue('setup_path') + '/cron/' + echo
        while True:
            if not self.process_exists(execstr): break
            time.sleep(3)

        start_time = time.time()
        public.writeFile(backup_log_file, "目录[{}]开始增量备份\n".format(path))
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), '目录[{}]开始增量备份'.format(path))
        # 增量备份是基于全量备份的
        path_last_full_backup_path = os.path.join(self.__dir_last_full_backup, path.replace('/', '_'))
        if not public.get_path_size(path_last_full_backup_path) or not public.M('path_full_backup').where('sid=?', sid).count():
            public.writeFile(backup_log_file, '第一次增量备份目录[{}]之前要先进行一次全量备份\n'.format(path), 'a+')
            print(u'第一次增量备份目录[{}]之前要先进行一次全量备份'.format(path))
            self.start_path_full_backup_task(path)

        backup_path = os.path.join(self.__dir_inc_backup, time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()) + path.replace('/', '_'))
        self.remove_dir(backup_path)
        os.makedirs(backup_path, 384)
        tar_file = backup_path + '/inc_backup.tar.gz'
        snapshot_file = path_last_full_backup_path + '/snapshot'
        tmp_snapshot_file = path_last_full_backup_path + '/snapshot_tmp'
        shutil.copy(snapshot_file, tmp_snapshot_file)

        try:
            cmd = 'cd {0} && tar -g {1} -zcvf {2} {3} {4} >> {5} 2>&1'.format(
                os.path.dirname(path), tmp_snapshot_file, tar_file, self.get_exclude(setting_info['exclude']), os.path.basename(path), backup_log_file)
            public.writeFile(backup_log_file, '增量备份目录[{}]命令：{}'.format(path, cmd), 'a+')
            # print(u'增量备份目录[{}]命令：{}'.format(path, cmd))
            public.ExecShell(cmd)
            if public.get_path_size(backup_path) > 100:
                shutil.copy(tmp_snapshot_file, backup_path + '/snapshot')
                # 加密压缩备份目录
                if os.path.exists(self.__encrypt_file):
                    tar_pass = self.__tar_pass
                else:
                    tar_pass = '未加密'
                result = self.compress_dir(backup_path, tar_pass, backup_log_file)
                if not result['status']:
                    self.remove_dir(backup_path)
                    os.remove(backup_log_file)
                    return result
                self.remove_dir(backup_path)
                # 记录存入数据库
                last_full_backup = public.M('path_full_backup').where('sid=?', sid).order('id desc').find()
                inc_file_path = backup_path + '.tar.gz'
                public.M('path_inc_backup').add('sid,fid,inc_file_path,full_file_path,tar_pass,addtime,cost_time',
                                                (sid, last_full_backup['id'], inc_file_path, last_full_backup['file_path'], tar_pass, int(time.time()), round(time.time() - start_time, 2)))
                # 上传备份到ftp
                if setting_info['upload_ftp'] and os.path.exists(os.path.join(self.__configPath, 'ftp.conf')):
                    self.path_upload_cloud('ftp', 'inc', inc_file_path)
                # 上传备份到alioss
                if setting_info['upload_alioss'] and os.path.exists(os.path.join(self.__configPath, 'alioss.conf')):
                    self.path_upload_cloud('alioss', 'inc', inc_file_path)
                # 上传备份到txcos
                if setting_info['upload_txcos'] and os.path.exists(os.path.join(self.__configPath, 'txcos.conf')):
                    self.path_upload_cloud('txcos', 'inc', inc_file_path)
                # 上传备份到七牛云存储
                if setting_info['upload_qiniu'] and os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')):
                    self.path_upload_cloud('qiniu', 'inc', inc_file_path)
                # 上传备份到亚马逊S3云存储
                if setting_info['upload_aws'] and os.path.exists(os.path.join(self.__configPath, 'aws.conf')):
                    self.path_upload_cloud('aws', 'inc', inc_file_path)
                # 如果设置本地不保存
                if not setting_info['upload_local'] and os.path.exists(inc_file_path):
                    os.remove(inc_file_path)
                # 删除增量备份的旧记录
                sql = 'select id from path_inc_backup where sid={} order by id desc limit (select count(*) from path_inc_backup) offset {}'.format(
                    sid, setting_info['inc_backup_save'])
                inc_backup_delete = public.M('').query(sql)
                for item in inc_backup_delete:
                    self.delete_path_inc_backup(item[0], delete_cloud=True)
            else:
                self.remove_dir(backup_path)
                print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), '目录[{}]增量备份失败, 生成的备份目录过小'.format(path))
            os.remove(tmp_snapshot_file)
            os.remove(backup_log_file)
            return public.returnMsg(True, '增量备份目录[{}]完成，耗时：{}'.format(path, round(time.time() - start_time, 2)))
        except:
            os.remove(tmp_snapshot_file)
            self.remove_dir(backup_path)
            os.remove(backup_log_file)
            return public.returnMsg(False, '增量备份目录[{}]失败, 原因：{}'.format(path, public.get_error_info()))

    # 目录备份文件上传到云端存储
    def path_upload_cloud(self, storage_type, backup_type, local_file, backup_log_file=None):
        get = public.dict_obj()
        get.path = '/'
        if backup_type == 'full':
            get.dirname = 'enterprise_backup/path/full'
        elif backup_type == 'inc':
            get.dirname = 'enterprise_backup/path/inc'

        self.upload_cloud(get, storage_type, local_file, backup_log_file)

    # 上传备份文件到云端存储
    def upload_cloud(self, get, storage_type, local_file, backup_log_file):
        if storage_type == 'ftp':
            from upload_ftp import ftp_main
            myftp = ftp_main()
            # myftp.createDir(get)
            result = myftp.upload_file_by_path(local_file, get.path + get.dirname)
            if not result:
                print(u'上传文件[{}]到ftp失败，请检查ftp配置是否可用'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到ftp失败，请检查ftp配置是否可用\n'.format(local_file), 'a+')
            else:
                print(u'上传文件[{}]到ftp成功'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到ftp成功\n'.format(local_file), 'a+')
        elif storage_type == 'alioss':
            from upload_alioss import alioss_main
            myalioss = alioss_main()
            myalioss.create_dir(get)
            result = myalioss.upload_file_by_path(local_file, get.dirname)
            if not result:
                print(u'上传文件[{}]到阿里云OSS失败，请检查阿里云OSS配置是否可用'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到阿里云OSS失败，请检查阿里云OSS配置是否可用\n'.format(local_file), 'a+')
            else:
                print(u'上传文件[{}]到阿里云OSS成功'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到阿里云OSS成功\n'.format(local_file), 'a+')
        elif storage_type == 'txcos':
            from upload_txcos import txcos_main
            mytxcos = txcos_main()
            mytxcos.create_dir(get)
            result = mytxcos.upload_file_by_path(local_file, get.dirname)
            if not result:
                print(u'上传文件[{}]到腾讯云COS失败，请检查腾讯云COS配置是否可用'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到腾讯云COS失败，请检查腾讯云COS配置是否可用\n'.format(local_file), 'a+')
            else:
                print(u'上传文件[{}]到腾讯云COS成功'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到腾讯云COS成功\n'.format(local_file), 'a+')
        elif storage_type == 'qiniu':
            from upload_qiniu import qiniu_main
            myqiniu = qiniu_main()
            myqiniu.create_dir(get.dirname)
            result = myqiniu.upload_file_by_path(local_file, get.dirname)
            if not result:
                print(u'上传文件[{}]到七牛云存储失败，请检查七牛云存储配置是否可用'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到七牛云存储失败，请检查七牛云存储配置是否可用\n'.format(local_file), 'a+')
            else:
                print(u'上传文件[{}]到七牛云存储成功'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到七牛云存储成功\n'.format(local_file), 'a+')
        elif storage_type == 'aws':
            from upload_aws import aws_main
            myaws = aws_main()
            result = myaws.upload_file_by_path(local_file, get.dirname)
            if not result:
                print(u'上传文件[{}]到亚马逊S3云存储失败，请检查亚马逊S3云存储配置是否可用'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到亚马逊S3云存储失败，请检查亚马逊S3云存储配置是否可用\n'.format(local_file), 'a+')
            else:
                print(u'上传文件[{}]到亚马逊S3云存储成功'.format(local_file))
                if backup_log_file:
                    public.writeFile(backup_log_file, '上传文件[{}]到亚马逊S3云存储成功\n'.format(local_file), 'a+')

    # 加密打包压缩文件夹
    def compress_dir(self, path, tar_pass, backup_log_file=None):
        encrypt = False
        if os.path.exists(self.__encrypt_file):
            encrypt = True
        if not os.path.exists('/usr/bin/openssl'):
            if os.path.exists('/usr/bin/yum'):
                public.ExecShell('yum install openssl -y')
            elif os.path.exists('/usr/bin/apt'):
                public.ExecShell('apt install openssl -y')
        if not os.path.exists('/usr/bin/pigz'):
            if os.path.exists('/usr/bin/yum'):
                public.ExecShell('yum install pigz -y')
            elif os.path.exists('/usr/bin/apt'):
                public.ExecShell('apt install pigz -y')
        path = path.strip()
        try:
            if backup_log_file:
                public.writeFile(backup_log_file, '压缩备份文件[{}]\n'.format(path), 'a+')
            # if os.path.exists('/usr/bin/pigz'):
            #     if encrypt:
            #         cmd = 'cd {0} && tar --use-compress-program=pigz -cvf - {1} | openssl des3 -salt -k {2} -out {1}.tar.gz'.format(os.path.dirname(path), os.path.basename(path), tar_pass)
            #     else:
            #         cmd = 'cd {0} && tar --use-compress-program=pigz -cvf {1}.tar.gz {1}'.format(os.path.dirname(path), os.path.basename(path))
            # else:
            if encrypt:
                cmd = 'cd {0} && tar -czvf - {1} | openssl des3 -salt -k {2} -out {1}.tar.gz'.format(os.path.dirname(path), os.path.basename(path), tar_pass)
            else:
                cmd = 'cd {0} && tar -czvf {1}.tar.gz {1}'.format(os.path.dirname(path), os.path.basename(path))
            public.ExecShell(cmd)
            file_size = public.get_path_size(path + '.tar.gz')
            # 检查备份是否有效
            if file_size > 100:
                return public.returnMsg(True, u'压缩目录{}完成'.format(path))
            else:
                return public.returnMsg(False, u'生成的压缩文件过小')
        except Exception as e:
            return public.returnMsg(False, u'压缩目录{}出错，错误原因：{}'.format(path, str(e)))

    def backup_site_log(self, log_backup_conf):
        '''
        备份网站日志
        :param log_backup_conf:
        :return:
        '''
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        print('★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份网站日志')
        public.writeFile(self.__log_backup_output_file, '★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份网站日志\n', 'a+')
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        webserver = public.get_webserver()
        px = '.log'
        if webserver == 'apache': px = '-access_log'
        if webserver == 'openlitespeed': px = '_ols.access_log'

        if log_backup_conf['select_website'] == 'ALL':
            sites = [item['name'] for item in public.M('sites').field('name').select()]
        else:
            sites = log_backup_conf['select_website'].split(',')
        backup_files = []
        for site in sites:
            if not site: continue
            if not self.exist_split_task(site):
                result = self.split_site_log(site, log_backup_conf['save'])
                if result:
                    backup_files.append(result)
            else:
                old_file_name = '/www/wwwlogs/' + site + px
                logs = glob.glob(old_file_name + "_*")
                backup_files.extend(logs)

        # 重启web服务
        public.serviceReload()

        # 上传备份文件到云端
        for local_file in backup_files:
            if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and log_backup_conf['upload_ftp']:
                if not self.check_file_cloud_storage_status('ftp', 'website', local_file):
                    self.log_upload_cloud('ftp', 'website', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and log_backup_conf['upload_alioss']:
                if not self.check_file_cloud_storage_status('alioss', 'website', local_file):
                    self.log_upload_cloud('alioss', 'website', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and log_backup_conf['upload_txcos']:
                if not self.check_file_cloud_storage_status('txcos', 'website', local_file):
                    self.log_upload_cloud('txcos', 'website', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and log_backup_conf['upload_qiniu']:
                if not self.check_file_cloud_storage_status('qiniu', 'website', local_file):
                    self.log_upload_cloud('qiniu', 'website', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and log_backup_conf['upload_aws']:
                if not self.check_file_cloud_storage_status('aws', 'website', local_file):
                    self.log_upload_cloud('aws', 'website', local_file)
            # 如果设置本地保存
            if log_backup_conf['upload_local']:
                new_file = os.path.join(self.__website_log_backup_path, os.path.basename(local_file))
                if public.get_path_size(local_file) != public.get_path_size(new_file):
                    shutil.copyfile(local_file, new_file)

    def exist_split_task(self, site):
        '''
        判断是否存在网站日志切割任务
        :param site:
        :return:
        '''
        if public.M('crontab').where('name=? and status=1', '切割日志[%s]' % site).count() or public.M('crontab').where('name=? and status=1', '切割日志[ALL]').count():
            return True
        return False

    def split_site_log(self, site, num):
        '''
        切割指定网站的日志
        :param site:
        :param num:
        :return:
        '''
        webserver = public.get_webserver()
        px = '.log'
        if webserver == 'apache': px = '-access_log'
        if webserver == 'openlitespeed': px = '_ols.access_log'

        old_file_name = '/www/wwwlogs/' + site + px
        if not os.path.exists(old_file_name):
            print('|---' + old_file_name + '文件不存在!')
            public.writeFile(self.__log_backup_output_file, '|---' + old_file_name + '文件不存在!', 'a+')
            return None

        logs = sorted(glob.glob(old_file_name + "_*"))
        count = len(logs)
        num = count - num

        for i in range(count):
            if i > num: break
            os.remove(logs[i])
            print('|---多余日志[' + logs[i] + ']已删除!')
            public.writeFile(self.__log_backup_output_file, '|---多余日志[' + logs[i] + ']已删除!\n', 'a+')

        new_file_name = old_file_name + '_' + time.strftime("%Y-%m-%d_%H%M%S") + '.log'
        shutil.move(old_file_name, new_file_name)
        if not os.path.exists('/www/server/panel/data/log_not_gzip.pl'):
            os.system("gzip %s" % new_file_name)
            print('|---已切割日志到:' + new_file_name + '.gz')
            public.writeFile(self.__log_backup_output_file, '|---已切割日志到:' + new_file_name + '.gz\n', 'a+')
            return new_file_name + '.gz'
        else:
            print('|---已切割日志到:' + new_file_name)
            public.writeFile(self.__log_backup_output_file, '|---已切割日志到:{}\n'.format(new_file_name), 'a+')
            return new_file_name

    def backup_secure_log(self, log_backup_conf):
        '''
        备份ssh登录日志
        :return:
        '''
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        print('★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份登录日志')
        public.writeFile(self.__log_backup_output_file, '★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份登录日志\n', 'a+')
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        system_version = self.get_system_version().lower()
        logs = []
        if 'centos' in system_version:
            logs = glob.glob('/var/log/secure*')
        elif 'ubuntu' in system_version or 'debian' in system_version:
            logs = glob.glob('/var/log/auth*')
        # print(logs)
        # 上传备份文件到云端
        for local_file in logs:
            if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and log_backup_conf['upload_ftp']:
                if not self.check_file_cloud_storage_status('ftp', 'secure', local_file):
                    self.log_upload_cloud('ftp', 'secure', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and log_backup_conf['upload_alioss']:
                if not self.check_file_cloud_storage_status('alioss', 'secure', local_file):
                    self.log_upload_cloud('alioss', 'secure', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and log_backup_conf['upload_txcos']:
                if not self.check_file_cloud_storage_status('txcos', 'secure', local_file):
                    self.log_upload_cloud('txcos', 'secure', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and log_backup_conf['upload_qiniu']:
                if not self.check_file_cloud_storage_status('qiniu', 'secure', local_file):
                    self.log_upload_cloud('qiniu', 'secure', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and log_backup_conf['upload_aws']:
                if not self.check_file_cloud_storage_status('aws', 'secure', local_file):
                    self.log_upload_cloud('aws', 'secure', local_file)
            if log_backup_conf['upload_local']:
                new_file = os.path.join(self.__secure_log_backup_path, os.path.basename(local_file))
                if public.get_path_size(local_file) != public.get_path_size(new_file):
                    shutil.copyfile(local_file, new_file)

    def backup_messages_log(self, log_backup_conf):
        '''
        备份系统日志
        :return:
        '''
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        print('★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份系统日志')
        public.writeFile(self.__log_backup_output_file, '★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份系统日志\n', 'a+')
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        system_version = self.get_system_version().lower()
        logs = []
        if 'centos' in system_version:
            logs = glob.glob('/var/log/messages*')
        elif 'ubuntu' in system_version or 'debian' in system_version:
            logs = glob.glob('/var/log/messages*')
            if not logs:
                conf = public.readFile('/etc/rsyslog.d/50-default.conf')
                if not conf or '*.info;mail.none;authpriv.none;cron.none /var/log/messages' not in conf:
                    public.writeFile('/etc/rsyslog.d/50-default.conf', '*.info;mail.none;authpriv.none;cron.none /var/log/messages\n', 'a+')
                    public.ExecShell('systemctl restart rsyslog')
                    time.sleep(1)
                logs = glob.glob('/var/log/messages*')
        # print(logs)
        # 上传备份文件到云端
        for local_file in logs:
            if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and log_backup_conf['upload_ftp']:
                if not self.check_file_cloud_storage_status('ftp', 'messages', local_file):
                    self.log_upload_cloud('ftp', 'messages', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and log_backup_conf['upload_alioss']:
                if not self.check_file_cloud_storage_status('alioss', 'messages', local_file):
                    self.log_upload_cloud('alioss', 'messages', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and log_backup_conf['upload_txcos']:
                if not self.check_file_cloud_storage_status('txcos', 'messages', local_file):
                    self.log_upload_cloud('txcos', 'messages', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and log_backup_conf['upload_qiniu']:
                if not self.check_file_cloud_storage_status('qiniu', 'messages', local_file):
                    self.log_upload_cloud('qiniu', 'messages', local_file)
            if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and log_backup_conf['upload_aws']:
                if not self.check_file_cloud_storage_status('aws', 'messages', local_file):
                    self.log_upload_cloud('aws', 'messages', local_file)
            if log_backup_conf['upload_local']:
                new_file = os.path.join(self.__messages_log_backup_path, os.path.basename(local_file))
                if public.get_path_size(local_file) != public.get_path_size(new_file):
                    shutil.copyfile(local_file, new_file)

    def get_mysql_info(self):
        '''
        获取数据库配置信息
        :return:
        '''
        data = {}
        try:
            public.CheckMyCnf()
            myfile = '/etc/my.cnf'
            mycnf = public.readFile(myfile)
            rep = r"datadir\s*=\s*(.+)\n"
            data['datadir'] = re.search(rep, mycnf).groups()[0]
            rep = r"port\s*=\s*([0-9]+)\s*\n"
            data['port'] = re.search(rep, mycnf).groups()[0]
        except:
            data['datadir'] = '/www/server/data'
            data['port'] = '3306'
        return data

    def backup_mysql_log(self, log_backup_conf):
        '''
        备份mysql错误日志和慢日志
        :return:
        '''
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        print('★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份mysql错误日志，慢日志和二进制日志')
        public.writeFile(self.__log_backup_output_file, '★[' + time.strftime("%Y/%m/%d %H:%M:%S") + ']，备份mysql错误日志，慢日志和二进制日志\n', 'a+')
        print('==================================================================')
        public.writeFile(self.__log_backup_output_file, '==================================================================\n', 'a+')
        datadir = self.get_mysql_info()['datadir']
        if not os.path.exists(datadir):
            print('未安装mysql数据库！')
            public.writeFile(self.__log_backup_output_file, '未安装mysql数据库！\n', 'a+')
            return
        # 分割错误日志
        err_log_file = ''
        for n in os.listdir(datadir):
            if len(n) < 5: continue
            if n[-3:] == 'err':
                err_log_file = datadir + '/' + n
                break
        split_err_log_file = self.split_mysql_log(err_log_file, log_backup_conf['save'])
        # 分割慢日志
        slow_log_file = datadir + '/mysql-slow.log'
        split_slow_log_file = self.split_mysql_log(slow_log_file, log_backup_conf['save'])
        # 压缩二进制日志
        bin_log_file_list = self.get_mysql_bin_log(datadir, log_backup_conf['save'])

        # 刷新日志服务
        mysql_version = self.get_mysql_version()
        print('mysql_version: ', mysql_version)
        if mysql_version > '5.7':
            public.ExecShell('/www/server/mysql/bin/mysqladmin -uroot -p{} flush-logs error'.format(self.get_mysql_root()))
            public.ExecShell('/www/server/mysql/bin/mysqladmin -uroot -p{} flush-logs slow'.format(self.get_mysql_root()))
        else:
            public.ExecShell('/www/server/mysql/bin/mysqladmin -uroot -p{} flush-logs'.format(self.get_mysql_root()))

        # 上传错误日志文件到云端
        if split_err_log_file:
            if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and log_backup_conf['upload_ftp']:
                if not self.check_file_cloud_storage_status('ftp', 'mysql', split_err_log_file):
                    self.log_upload_cloud('ftp', 'mysql', split_err_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and log_backup_conf['upload_alioss']:
                if not self.check_file_cloud_storage_status('alioss', 'mysql', split_err_log_file):
                    self.log_upload_cloud('alioss', 'mysql', split_err_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and log_backup_conf['upload_txcos']:
                if not self.check_file_cloud_storage_status('txcos', 'mysql', split_err_log_file):
                    self.log_upload_cloud('txcos', 'mysql', split_err_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and log_backup_conf['upload_qiniu']:
                if not self.check_file_cloud_storage_status('qiniu', 'mysql', split_err_log_file):
                    self.log_upload_cloud('qiniu', 'mysql', split_err_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and log_backup_conf['upload_aws']:
                if not self.check_file_cloud_storage_status('aws', 'mysql', split_err_log_file):
                    self.log_upload_cloud('aws', 'mysql', split_err_log_file)
            # 如果设置本地保存
            if log_backup_conf['upload_local']:
                new_file = os.path.join(self.__mysql_log_backup_path, os.path.basename(split_err_log_file))
                if public.get_path_size(split_err_log_file) != public.get_path_size(new_file):
                    shutil.copyfile(split_err_log_file, new_file)
        # 上传慢日志文件到云端
        if split_slow_log_file:
            if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and log_backup_conf['upload_ftp']:
                if not self.check_file_cloud_storage_status('ftp', 'mysql', split_slow_log_file):
                    self.log_upload_cloud('ftp', 'mysql', split_slow_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and log_backup_conf['upload_alioss']:
                if not self.check_file_cloud_storage_status('alioss', 'mysql', split_slow_log_file):
                    self.log_upload_cloud('alioss', 'mysql', split_slow_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and log_backup_conf['upload_txcos']:
                if not self.check_file_cloud_storage_status('txcos', 'mysql', split_slow_log_file):
                    self.log_upload_cloud('txcos', 'mysql', split_slow_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and log_backup_conf['upload_qiniu']:
                if not self.check_file_cloud_storage_status('qiniu', 'mysql', split_slow_log_file):
                    self.log_upload_cloud('qiniu', 'mysql', split_slow_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and log_backup_conf['upload_aws']:
                if not self.check_file_cloud_storage_status('aws', 'mysql', split_slow_log_file):
                    self.log_upload_cloud('aws', 'mysql', split_slow_log_file)
            # 如果设置本地保存
            if log_backup_conf['upload_local']:
                new_file = os.path.join(self.__mysql_log_backup_path, os.path.basename(split_slow_log_file))
                if public.get_path_size(split_slow_log_file) != public.get_path_size(new_file):
                    shutil.copyfile(split_slow_log_file, new_file)
        # 上传二进制日志文件到云端
        for bin_log_file in bin_log_file_list:
            if os.path.exists(os.path.join(self.__configPath, 'ftp.conf')) and log_backup_conf['upload_ftp']:
                if not self.check_file_cloud_storage_status('ftp', 'mysql', bin_log_file):
                    self.log_upload_cloud('ftp', 'mysql', bin_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'alioss.conf')) and log_backup_conf['upload_alioss']:
                if not self.check_file_cloud_storage_status('alioss', 'mysql', bin_log_file):
                    self.log_upload_cloud('alioss', 'mysql', bin_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'txcos.conf')) and log_backup_conf['upload_txcos']:
                if not self.check_file_cloud_storage_status('txcos', 'mysql', bin_log_file):
                    self.log_upload_cloud('txcos', 'mysql', bin_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'qiniu.conf')) and log_backup_conf['upload_qiniu']:
                if not self.check_file_cloud_storage_status('qiniu', 'mysql', bin_log_file):
                    self.log_upload_cloud('qiniu', 'mysql', bin_log_file)
            if os.path.exists(os.path.join(self.__configPath, 'aws.conf')) and log_backup_conf['upload_aws']:
                if not self.check_file_cloud_storage_status('aws', 'mysql', bin_log_file):
                    self.log_upload_cloud('aws', 'mysql', bin_log_file)
            # 如果设置本地保存
            if log_backup_conf['upload_local']:
                new_file = os.path.join(self.__mysql_log_backup_path, os.path.basename(bin_log_file))
                if public.get_path_size(bin_log_file) != public.get_path_size(new_file):
                    shutil.copyfile(bin_log_file, new_file)

    def get_mysql_bin_log(self, datadir, num):
        '''
        获取mysql二进制日志列表
        :return:
        '''
        logs = sorted(glob.glob(datadir + "/mysql-bin*.gz"))
        count = len(logs)
        num = count - num

        for i in range(count):
            if i > num: break
            os.remove(logs[i])
            print('|---多余日志[' + logs[i] + ']已删除!')
            public.writeFile(self.__log_backup_output_file, '|---多余日志[' + logs[i] + ']已删除!\n', 'a+')

        log_list = []
        for log_file in glob.glob(datadir + "/mysql-bin*"):
            if log_file.endswith('.index') or log_file.endswith('.gz'): continue
            if not os.path.exists(log_file + '.gz'):
                print('正在压缩mysql二进制日志：' + log_file)
                public.writeFile(self.__log_backup_output_file, '正在压缩mysql二进制日志：{}\n'.format(log_file), 'a+')
                os.system("gzip -c {} > {}.gz".format(log_file, log_file))
            else:
                last_bin_file = public.readFile('/www/server/data/mysql-bin.index').split()[-1]
                if os.path.basename(log_file) == os.path.basename(last_bin_file):
                    os.remove(log_file + '.gz')
                    print('正在压缩mysql二进制日志：' + log_file)
                    public.writeFile(self.__log_backup_output_file, '正在压缩mysql二进制日志：{}\n'.format(log_file), 'a+')
                    os.system("gzip -c {} > {}.gz".format(log_file, log_file))
            log_list.append(log_file + '.gz')
        return log_list

    def split_mysql_log(self, log_file, num):
        '''
        mysql错误日志和慢日志按日期进行分割
        :return:
        '''
        if not os.path.exists(log_file):
            print('|---' + log_file + '文件不存在!')
            public.writeFile(self.__log_backup_output_file, '|---' + log_file + '文件不存在!\n', 'a+')
            return None

        logs = sorted(glob.glob(log_file + "_*"))
        count = len(logs)
        num = count - num

        for i in range(count):
            if i > num: break
            os.remove(logs[i])
            print('|---多余日志[' + logs[i] + ']已删除!')
            public.writeFile(self.__log_backup_output_file, '|---多余日志[' + logs[i] + ']已删除!\n', 'a+')

        new_file_name = log_file + '_' + time.strftime("%Y-%m-%d_%H%M%S")
        shutil.move(log_file, new_file_name)
        if not os.path.exists('/www/server/panel/data/log_not_gzip.pl'):
            os.system("gzip %s" % new_file_name)
            print('|---已切割日志到:' + new_file_name + '.gz')
            public.writeFile(self.__log_backup_output_file, '|---已切割日志到:' + new_file_name + '.gz\n', 'a+')
            return new_file_name + '.gz'
        else:
            print('|---已切割日志到:' + new_file_name)
            public.writeFile(self.__log_backup_output_file, '|---已切割日志到:{}\n'.format(new_file_name), 'a+')
            return new_file_name

    def log_upload_cloud(self, storage_type, backup_type, local_file, need_date=False):
        '''
        日志备份文件上传到云端存储
        :param storage_type: 云存储类型
        :param backup_type: 备份日志类型
        :param local_file: 本地文件路径
        :param backup_log_file:
        :param need_date:
        :return:
        '''
        get = public.dict_obj()
        get.path = '/'
        if need_date:
            get.dirname = 'enterprise_backup/log/{}/{}/{}'.format(backup_type, public.GetLocalIp(), time.strftime("%Y-%m-%d"))
        else:
            get.dirname = 'enterprise_backup/log/{}/{}'.format(backup_type, public.GetLocalIp())

        self.upload_cloud(get, storage_type, local_file, backup_log_file=self.__log_backup_output_file)

    def check_file_cloud_storage_status(self, storage_type, backup_type, local_file):
        '''
        检查文件是否已经上传到了云端
        :param storage_type: 云存储类型
        :param backup_type: 备份日志类型
        :param local_file: 本地文件路径
        :return:
        '''
        get = public.dict_obj()
        get.path = '/enterprise_backup/log/{}/{}'.format(backup_type, public.GetLocalIp())

        data = {}
        try:
            if storage_type == 'ftp':
                from upload_ftp import ftp_main
                myftp = ftp_main()
                data = myftp.getList(get)
            elif storage_type == 'alioss':
                from upload_alioss import alioss_main
                myalioss = alioss_main()
                data = myalioss.get_list(get)
            elif storage_type == 'txcos':
                from upload_txcos import txcos_main
                mytxcos = txcos_main()
                data = mytxcos.get_list(get)
            elif storage_type == 'qiniu':
                from upload_qiniu import qiniu_main
                myqiniu = qiniu_main()
                data = myqiniu.get_list(get.path)
            elif storage_type == 'aws':
                from upload_aws import aws_main
                myaws = aws_main()
                data = myaws.get_list(get)
        except:
            print(storage_type)
            return False

        cloud_file_size = 0
        if data and 'list' in data:
            for item in data['list']:
                if os.path.basename(local_file) == item['name']:
                    cloud_file_size = int(item['size'])
        if cloud_file_size == public.get_path_size(local_file):
            # print('文件{}已经存在于{}云存储{}目录下'.format(os.path.basename(local_file), storage_type, get.path))
            # public.writeFile(self.__log_backup_output_file, '文件{}已经存在于{}云存储{}目录下\n'.format(os.path.basename(local_file), storage_type, get.path), 'a+')
            return True
        return False


if __name__ == '__main__':
    log_backup_conf = {'save': 180, 'upload_local': 1, 'upload_ftp': 0, 'upload_alioss': 1, 'upload_txcos': 0, 'upload_qiniu': 0, 'upload_aws': 0, 'select_website': 'ALL',
                       'backup_website': 1, 'backup_mysql': 1, 'backup_secure': 1, 'backup_messages': 1, 'where_hour': 0, 'where_minute': 0}
    my_obj = BackupTask()
    # # 测试网站日志备份
    # my_obj.backup_site_log(log_backup_conf)
    # # 测试登录日志备份
    # my_obj.backup_secure_log(log_backup_conf)
    # # 测试系统日志备份
    # my_obj.backup_messages_log(log_backup_conf)
    # 测试mysql日志备份
    my_obj.backup_mysql_log(log_backup_conf)
