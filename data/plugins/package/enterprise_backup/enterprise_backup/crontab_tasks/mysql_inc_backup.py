# coding: utf-8

import sys,os
os.chdir("/www/server/panel/")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(u'参数错误')
        sys.exit()
    sys.path.insert(0, '/www/server/panel/plugin/enterprise_backup')
    from backup_task import BackupTask

    myobj = BackupTask()
    result = myobj.mysql_inc_backup(sys.argv[1])
    print(result['msg'])
    myobj.mysql_ddl_backup(sys.argv[1])
