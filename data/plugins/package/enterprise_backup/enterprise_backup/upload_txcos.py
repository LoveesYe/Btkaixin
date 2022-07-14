#!/usr/bin/python
# coding: utf-8
# -----------------------------
# 备份 TO TXCOS
# -----------------------------
import sys, os, re

if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
os.chdir('/www/server/panel')
sys.path.insert(0, "class/")
import public, db, time, re, json
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client


# 腾讯云oss 的类
class txcos_main:
    __oss = None
    __bucket_path = None
    __error_count = 0
    __secret_id = None
    __secret_key = None
    __region = None
    __Bucket = None
    __oss_path = None
    __error_msg = "ERROR: 无法连接腾讯云COS !"
    __configPath = '/www/server/panel/plugin/enterprise_backup/config'
    __exclude = ""

    def __init__(self):
        if not os.path.exists(self.__configPath):
            os.makedirs(self.__configPath)
        self.__conn()

    def __conn(self):
        if self.__oss: return

        keys = self.GetConfig()
        self.__secret_id = keys[0]
        self.__secret_key = keys[1]
        self.__region = keys[2]
        self.__Bucket = keys[3]
        self.__bucket_path = self.get_path(keys[4])
        try:
            config = CosConfig(Region=self.__region, SecretId=self.__secret_id, SecretKey=self.__secret_key, Token=None, Scheme='http')
            self.__oss = CosS3Client(config)
        except Exception as ex:
            print(self.__error_msg, str(ex))

    # 获取账号密码设置
    def GetConfig(self, get=None):
        path = self.__configPath + '/txcos.conf'
        # if not os.path.exists(path):
        #     if os.path.exists('/www/server/panel/plugin/txcos/config.conf'):
        #         public.writeFile(path, public.readFile('/www/server/panel/plugin/txcos/config.conf'))
        if not os.path.exists(path): return ['', '', '', '', '/']
        conf = public.readFile(path)
        if not conf: return ['', '', '', '', '/']
        result = conf.split('|')
        if len(result) < 5: result.append('/')
        return result

    # 设置账号密码
    def SetConfig(self, get):
        path = self.__configPath + '/txcos.conf'
        conf = get.secret_id.strip() + '|' + get.secret_key.strip() + '|' + get.region.strip() + '|' + get.bucket.strip() + '|' + get.bucket_path.strip()
        public.writeFile(path, conf)
        return public.returnMsg(True, '设置成功!')

    # 检测txcos是否可用
    def check_config(self):
        try:
            data = []
            dir_list = []
            path = self.__bucket_path + self.get_path('/')
            if 'Contents' in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path):
                for b in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path)['Contents']:
                    tmp = {}
                    b['Key'] = b['Key'].replace(path, '')
                    if not b['Key']: continue
                    tmp['name'] = b['Key']
                    tmp['size'] = b['Size']
                    tmp['type'] = b['StorageClass']
                    tmp['download'] = self.download_file(path + b['Key'])
                    tmp['time'] = b['LastModified']
                    data.append(tmp)
            else:
                pass
            if 'CommonPrefixes' in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path):
                for i in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path)['CommonPrefixes']:
                    if not i['Prefix']: continue
                    dir_dir = i['Prefix'].split('/')[-2] + '/'
                    dir_list.append(dir_dir)
            else:
                pass
            return True
        except:
            return False

    # 上传文件
    def upload_file(self, filename):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            # 断点续传
            filepath, key = os.path.split(filename)
            print(key)
            key = self.__bucket_path + key
            print(key)
            # 短点续传
            response = self.__oss.upload_file(
                Bucket=self.__Bucket,
                Key=key,
                MAXThread=10,
                PartSize=5,
                LocalFilePath=filename)
        except:
            time.sleep(1)
            self.__error_count += 1
            if self.__error_count < 2:  # 重试2次
                self.sync_date()
                self.upload_file(filename)
            print(self.__error_msg)
            return None

    # 上传文件
    def upload_file_by_path(self, filename, bucket_path):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            filepath, key = os.path.split(filename)
            self.__bucket_path = self.get_path(bucket_path)
            key = self.__bucket_path + '/' + key
            # print(key)
            # 断点续传
            response = self.__oss.upload_file(Bucket=self.__Bucket, Key=key, MAXThread=10, PartSize=5, LocalFilePath=filename)
            # print(u'上传文件到腾讯云COS返回结果：', response)
            return True
        except Exception as ex:
            # print(ex)
            time.sleep(1)
            self.__error_count += 1
            if self.__error_count < 2:  # 重试2次
                self.sync_date()
                self.upload_file_by_path(filename, bucket_path)
            return False

    # 创建目录
    def create_dir(self, get):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        path = self.get_path(get.path + get.dirname)
        filename = '/tmp/dirname.pl'
        public.writeFile(filename, '')
        response = self.__oss.put_object(Bucket=self.__Bucket, Body=b'', Key=path)
        os.remove(filename)
        return public.returnMsg(True, '创建成功!')

    def get_list(self, get):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            data = []
            dir_list = []
            # path = self.get_path(get.path) ant修改
            path = self.__bucket_path + self.get_path(get.path)
            if 'Contents' in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path):
                for b in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path)['Contents']:
                    tmp = {}
                    b['Key'] = b['Key'].replace(path, '')
                    if not b['Key']: continue
                    tmp['name'] = b['Key']
                    tmp['size'] = b['Size']
                    tmp['type'] = b['StorageClass']
                    tmp['download'] = self.download_file(path + b['Key'])
                    tmp['time'] = b['LastModified']
                    data.append(tmp)
            else:
                pass
            if 'CommonPrefixes' in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path):
                for i in self.__oss.list_objects(Bucket=self.__Bucket, MaxKeys=100, Delimiter='/', Prefix=path)['CommonPrefixes']:
                    if not i['Prefix']: continue
                    dir_dir = i['Prefix'].split('/')[-2] + '/'
                    dir_list.append(dir_dir)
            else:
                pass
            mlist = {}
            mlist['path'] = get.path
            mlist['list'] = data
            mlist['dir'] = dir_list
            return mlist
        except:
            mlist = {}
            if self.__oss:
                mlist['status'] = True
            else:
                mlist['status'] = False
            mlist['path'] = get.path
            mlist['list'] = data
            mlist['dir'] = dir_list
            return mlist

    def sync_date(self):
        import config
        config.config().syncDate(None)

    def download_file(self, filename, Expired=300):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            response = self.__oss.get_presigned_download_url(Bucket=self.__Bucket, Key=filename)
            response = re.findall('([^?]*)?.*', response)[0]
            return response
        except:
            print(self.__error_msg)
            return None

    def get_path(self, path):
        if path == '/': path = ''
        if path[:1] == '/':
            path = path[1:]
            if path[-1:] != '/': path += '/'
        return path

    def delete_file(self, filename):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            response = self.__oss.delete_object(Bucket=self.__Bucket, Key=filename)
            return response
        except Exception as ex:
            self.__error_count += 1
            if self.__error_count < 2:
                self.sync_date()
                self.delete_file(filename)
            print(self.__error_msg)
            return None

    # 删除文件
    def remove_file(self, get):
        path = self.get_path(get.path)
        filename = path + get.filename
        self.delete_file(filename)
        return public.returnMsg(True, '删除文件成功!')
