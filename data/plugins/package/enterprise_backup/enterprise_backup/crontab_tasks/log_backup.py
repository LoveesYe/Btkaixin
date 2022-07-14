# coding: utf-8

import sys
import os
import json
os.chdir("/www/server/panel/")
sys.path.append("/www/server/panel/class/")
import public


def get_log_backup_conf():
    '''
    获取日志备份任务设置
    :return:
    '''
    log_backup_conf = '/www/server/panel/plugin/enterprise_backup/config/log_backup_conf.json'
    if not os.path.exists(log_backup_conf):
        data = {'save': 180, 'upload_local': 1, 'upload_ftp': 0, 'upload_alioss': 0, 'upload_txcos': 0, 'upload_qiniu': 0, 'upload_aws': 0, 'select_website': 'ALL',
                'backup_website': 1, 'backup_mysql': 1, 'backup_secure': 1, 'backup_messages': 1, 'where_hour': 0, 'where_minute': 0}
    else:
        data = json.loads(public.readFile(log_backup_conf))
    if 'select_website' not in data: data['select_website'] = 'ALL'
    if 'upload_local' not in data: data['upload_local'] = 1
    if 'backup_website' not in data: data['backup_website'] = 1
    if 'backup_mysql' not in data: data['backup_mysql'] = 1
    if 'backup_secure' not in data: data['backup_secure'] = 1
    if 'backup_messages' not in data: data['backup_messages'] = 1
    if 'where_hour' not in data: data['where_hour'] = 0
    if 'where_minute' not in data: data['where_minute'] = 0
    public.writeFile(log_backup_conf, json.dumps(data))
    return data


if __name__ == "__main__":
    sys.path.insert(0, '/www/server/panel/plugin/enterprise_backup')
    from backup_task import BackupTask

    my_obj = BackupTask()
    __log_backup_output_file = '/www/server/panel/plugin/enterprise_backup/log_backup_output'
    public.writeFile(__log_backup_output_file, '开始日志备份任务\n')
    log_backup_conf = get_log_backup_conf()
    if log_backup_conf['backup_website']:
        # 网站日志备份
        my_obj.backup_site_log(log_backup_conf)
    if log_backup_conf['backup_secure']:
        # 登录日志备份
        my_obj.backup_secure_log(log_backup_conf)
    if log_backup_conf['backup_messages']:
        # 系统日志备份
        my_obj.backup_messages_log(log_backup_conf)
    if log_backup_conf['backup_mysql']:
        # mysql日志备份
        my_obj.backup_mysql_log(log_backup_conf)
    public.writeFile(__log_backup_output_file, '日志备份任务执行完成', 'a+')
