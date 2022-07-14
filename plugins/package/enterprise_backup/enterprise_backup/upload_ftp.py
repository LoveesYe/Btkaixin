#!/usr/bin/python
# coding: utf-8
# -----------------------------
# 备份 TO FTP
# -----------------------------
import sys, os, re

if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
os.chdir('/www/server/panel')
sys.path.insert(0, "class/")
import public, db, time


class ftp_main:
    __configPath = '/www/server/panel/plugin/enterprise_backup/config'
    __path = '/'

    def __init__(self):
        if not os.path.exists(self.__configPath):
            os.makedirs(self.__configPath)
        self.__path = self.GetConfig(None)[3]

    def GetConfig(self, get=None):
        path = self.__configPath + '/ftp.conf'
        # if not os.path.exists(path):
        #     if os.path.exists('/www/server/panel/plugin/ftp/config.conf'):
        #         public.writeFile(path, public.readFile('/www/server/panel/plugin/ftp/config.conf'))
        if not os.path.exists(path): return ['', '', '', '/']
        conf = public.readFile(path)
        if not conf: return ['', '', '', '/']
        return conf.split('|')

    def SetConfig(self, get):
        path = self.__configPath + '/ftp.conf'

        conf = get.ftp_host + '|' + get.ftp_user + '|' + get.ftp_pass + '|' + get.ftp_path
        public.writeFile(path, conf)
        return public.returnMsg(True, '设置成功!')

    # 连接FTP
    def connentFtp(self):
        from ftplib import FTP
        tmp = self.GetConfig()
        if tmp[0].find(':') == -1: tmp[0] += ':21'
        host = tmp[0].split(':')
        if host[1] == '': host[1] = '21'
        ftp = FTP()
        ftp.set_debuglevel(0)
        ftp.connect(host[0], int(host[1]))
        ftp.login(tmp[1], tmp[2])
        if self.__path != '/':
            self.dirname = self.__path
            self.path = '/'
            self.createDir(self, ftp)
        ftp.cwd(self.__path)
        return ftp

    # 检测ftp是否可用
    def check_config(self):
        try:
            ftp = self.connentFtp()
            if ftp: return True
        except:
            return False

    # 创建目录
    def createDir(self, get, ftp=None):
        try:
            if not ftp: ftp = self.connentFtp()
            dirnames = get.dirname.split('/')
            ftp.cwd(get.path)
            for dirname in dirnames:
                if not dirname: continue
                if not dirname in ftp.nlst(): ftp.mkd(dirname)
                ftp.cwd(dirname)
            return public.returnMsg(True, '目录创建成功!')
        except:
            return public.returnMsg(False, '目录创建失败!')

    # 上传文件
    def updateFtp(self, filename):
        try:
            ftp = self.connentFtp()
            bufsize = 1024
            file_handler = open(filename, 'rb')
            ftp.storbinary('STOR %s' % os.path.basename(filename), file_handler, bufsize)
            file_handler.close()
            ftp.quit()
        except:
            if os.path.exists(filename): os.remove(filename)
            print('连接服务器失败!')
            return {'status': False, 'msg': '连接服务器失败!'}

    # 上传文件到指定目录
    def upload_file_by_path(self, filename, back_path):
        try:
            ftp = self.connentFtp()
            root_path = self.GetConfig(None)[3]
            get = public.dict_obj()
            if back_path[0] == "/":
                back_path = back_path[1:]
            get.path = root_path
            get.dirname = back_path
            self.createDir(get)
            target_path = os.path.join(root_path, back_path)
            print("目标上传目录：{}".format(target_path))
            ftp.cwd(target_path)
            bufsize = 1024
            file_handler = open(filename, 'rb')
            ftp.storbinary('STOR %s' % os.path.basename(filename), file_handler, bufsize)
            file_handler.close()
            ftp.quit()
            return True
        except:
            # if os.path.exists(filename): os.remove(filename)
            print(public.get_error_info())
            return False

    # 从FTP删除文件
    def deleteFtp(self, filename):
        try:
            ftp = self.connentFtp()
            try:
                ftp.rmd(filename)
            except:
                ftp.delete(filename)
            return True
        except Exception as ex:
            print(ex)
            return False

    # 删除文件或目录
    def rmFile(self, get):
        root_path = self.GetConfig(None)[3]
        if get.path[0] == "/":
            get.path = get.path[1:]
        self.__path = os.path.join(root_path, get.path)
        if self.deleteFtp(get.filename):
            return public.returnMsg(True, '删除成功!')
        return public.returnMsg(False, '删除失败!')

    # 获取列表
    def getList(self, get=None):
        try:
            self.__path = get.path
            ftp = self.connentFtp()
            result = ftp.nlst()
            dirs = []
            files = []
            data = []
            for dt in result:
                if dt == '.' or dt == '..': continue
                sfind = public.M('backup').where('name=?', (dt,)).field('size,addtime').find()
                if not sfind:
                    sfind = {}
                    sfind['addtime'] = '1970/01/01 00:00:01'
                tmp = {}
                tmp['name'] = dt
                tmp['time'] = int(time.mktime(time.strptime(sfind['addtime'], '%Y/%m/%d %H:%M:%S')))
                try:
                    tmp['size'] = ftp.size(dt)
                    tmp['dir'] = False
                    tmp['download'] = self.getFile(dt)
                    files.append(tmp)
                except:
                    tmp['size'] = 0
                    tmp['dir'] = True
                    tmp['download'] = ''
                    dirs.append(tmp)

            data = dirs + files
            mlist = {}
            mlist['path'] = self.__path
            mlist['list'] = data
            return mlist
        except Exception as ex:
            return {'status': False, 'msg': str(ex)}

    # 获取文件地址
    def getFile(self, filename):
        tmp = self.GetConfig()
        if tmp[0].find(':') == -1: tmp[0] += ':21'
        host = tmp[0].split(':')
        if host[1] == '': host[1] = '21'
        return 'ftp://' + tmp[1] + ':' + tmp[2] + '@' + host[0] + ':' + host[1] + (self.__path + '/' + filename).replace('//', '/')

    # 获取文件地址2
    def download_file(self, filename):
        return self.getFile(filename)


# if  __name__ == "__main__":
#     get = public.dict_obj()
#     get.path = "/enterprise_backup/path/full"
#     get.filename = "2021-08-10_17-22-51_www_wwwroot_www.bt.cn.tar.gz"
#     ftp = ftp_main()
#     print(ftp.rmFile(get))