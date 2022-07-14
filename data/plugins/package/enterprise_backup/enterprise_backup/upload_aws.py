#!/usr/bin/python
# coding: utf-8
# -----------------------------
# 备份 TO TXCOS
# -----------------------------
import sys
import os
import time
import re

from boto3 import client

if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
os.chdir('/www/server/panel')
sys.path.insert(0, "class/")
import public, db


class aws_main:
    __oss = None
    __bucket_path = None
    __error_count = 0
    __secret_id = None
    __secret_key = None
    __Bucket = None
    __oss_path = None
    __error_msg = "ERROR: 无法连接亚马逊S3云存储!"
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
        self.__Bucket = keys[2]
        self.__bucket_path = self.get_path(keys[3])
        try:
            self.__oss = client('s3', aws_access_key_id=self.__secret_id, aws_secret_access_key=self.__secret_key)
        except Exception as ex:
            print(self.__error_msg, public.get_error_info())

    # 获取账号密码设置
    def GetConfig(self, get=None):
        path = self.__configPath + '/aws.conf'
        if not os.path.exists(path): return ['', '', '', '/']
        conf = public.readFile(path)
        if not conf: return ['', '', '', '/']
        result = conf.split('|')
        if len(result) < 4: result.append('/')
        return result

    # 设置账号密码
    def SetConfig(self, get):
        path = self.__configPath + '/aws.conf'
        conf = get.secret_id.strip() + '|' + get.secret_key.strip() + '|' + get.bucket.strip() + '|' + get.bucket_path.strip()
        public.writeFile(path, conf)
        return public.returnMsg(True, '设置成功!')

    # 检测txcos是否可用
    def check_config(self):
        try:
            path = self.__bucket_path + self.get_path('/')
            self.__oss.list_objects_v2(Bucket=self.__Bucket, MaxKeys=1000, Delimiter='/', Prefix=path)
            return True
        except:
            print(public.get_error_info())
            return False

    # 上传文件到指定目录
    def upload_file_by_path(self, filename, bucket_path):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            filepath, key = os.path.split(filename)
            self.__bucket_path = self.get_path(bucket_path)
            key = self.__bucket_path + '/' + key
            print(key)
            self.__oss.upload_file(Bucket=self.__Bucket, Key=key, Filename=filename)
            return True
        except Exception as ex:
            print(public.get_error_info())
            time.sleep(1)
            self.__error_count += 1
            if self.__error_count < 2:  # 重试2次
                print("重试上传文件....")
                self.sync_date()
                self.upload_file_by_path(filename, bucket_path)
            return False

    def get_list(self, get):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            data = []
            path = self.get_path(get.path)
            max_keys = 1000
            objects = self.__oss.list_objects_v2(Bucket=self.__Bucket, MaxKeys=max_keys, Delimiter='/', Prefix=path)
            if 'Contents' in objects:
                for b in objects['Contents']:
                    tmp = {}
                    b['Key'] = b['Key'].replace(path, '')
                    if not b['Key']: continue
                    tmp['name'] = b['Key']
                    tmp['size'] = b['Size']
                    tmp['type'] = b['StorageClass']
                    tmp['download'] = ""
                    tmp['time'] = b['LastModified'].timestamp()
                    data.append(tmp)
            if 'CommonPrefixes' in objects:
                for i in objects['CommonPrefixes']:
                    if not i['Prefix']: continue
                    dir_dir = i['Prefix'].split('/')[-2] + '/'
                    tmp = {}
                    tmp["name"] = dir_dir
                    tmp["type"] = None
                    data.append(tmp)

            mlist = {}
            mlist['path'] = path
            mlist['list'] = data
            return mlist
        except Exception as e:
            print("获取文件列表失败，失败原因：" + public.get_error_info())

    def sync_date(self):
        import config
        config.config().syncDate(None)

    def download_file(self, key, local_file):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            print(self.__error_msg)
            return False

        try:
            print(key, local_file)
            with open(local_file, 'wb') as fp:
                self.__oss.download_fileobj(self.__Bucket, key, fp)
        except:
            print(self.__error_msg, public.get_error_info())

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
            print(self.__error_msg, public.get_error_info())

    # 删除文件
    def remove_file(self, get):
        path = self.get_path(get.path)
        filename = path + get.filename
        self.delete_file(filename)
        return public.returnMsg(True, '删除文件成功!')
