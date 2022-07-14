# coding: utf-8

import sys,os
os.chdir("/www/server/panel/")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('参数错误')
        sys.exit()
    sys.path.insert(0, '/www/server/panel/plugin/enterprise_backup')
    from backup_task import BackupTask

    myobj = BackupTask()
    result = myobj.path_full_backup(sys.argv[1])
    print(result['msg'])
