# coding: utf-8

import sys,os
os.chdir("/www/server/panel/")
sys.path.append("/www/server/panel/class/")
import public

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(u'参数错误')
        sys.exit()
    sys.path.insert(0, '/www/server/panel/plugin/enterprise_backup')
    from backup_task import BackupTask

    myobj = BackupTask()
    result = myobj.mysql_full_backup(sys.argv[1])
    print(result['msg'])
    try:
        setting_info = public.M('mysql_backup_setting').where('id=?', sys.argv[1]).find()
        if int(setting_info['inc_backup_need']) == 0:
            myobj.mysql_ddl_backup(sys.argv[1])
    except:
        pass
