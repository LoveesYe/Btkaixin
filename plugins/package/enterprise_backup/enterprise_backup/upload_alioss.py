#!/usr/bin/python
# coding: utf-8
# -----------------------------
# 备份 TO ALIOSS
# -----------------------------
import sys
import os
import time
import oss2

if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
os.chdir('/www/server/panel')
sys.path.insert(0, "class/")
import public, db


class alioss_main:
    __oss = None
    __bucket_name = None
    __bucket_domain = None
    __bucket_path = None
    __bucket_path_bak = None
    __error_count = 0
    __error_msg = "ERROR: 无法连接到阿里云OSS服务器，请检查[AccessKeyId/AccessKeySecret/Endpoint]设置是否正确!"
    __configPath = '/www/server/panel/plugin/enterprise_backup/config'
    __exclude = ""

    def __init__(self):
        if not os.path.exists(self.__configPath):
            os.makedirs(self.__configPath)
        self.__conn()

    def __conn(self):
        if self.__oss: return
        # 获取阿里云秘钥
        keys = self.GetConfig()

        self.__bucket_name = keys[2]
        if keys[3].find(keys[2]) != -1: keys[3] = keys[3].replace(keys[2] + '.', '')
        self.__bucket_domain = keys[3]
        self.__bucket_path = self.get_path(keys[4] + '/bt_backup/')
        self.__bucket_path_bak = self.__bucket_path
        if self.__bucket_path[:1] == '/': self.__bucket_path = self.__bucket_path[1:]

        try:
            # 构建鉴权对象
            self.__oss = oss2.Auth(keys[0], keys[1])
        except Exception as ex:
            print(self.__error_msg, str(ex))

    def GetConfig(self, get=None):
        path = self.__configPath + '/alioss.conf'
        # if not os.path.exists(path):
        #     if os.path.exists('/www/server/panel/plugin/alioss/config.conf'):
        #         public.writeFile(path, public.readFile('/www/server/panel/plugin/alioss/config.conf'))
        if not os.path.exists(path): return ['', '', '', '', '/']
        conf = public.readFile(path)
        if not conf: return ['', '', '', '', '/']
        result = conf.split('|')
        if len(result) < 5: result.append('/')
        return result

    def SetConfig(self, get):
        path = self.__configPath + '/alioss.conf'
        conf = get.access_key.strip() + '|' + get.secret_key.strip() + '|' + get.bucket_name.strip() + '|' + get.bucket_domain.strip() + '|' + get.bucket_path.strip()
        public.writeFile(path, conf)
        return public.returnMsg(True, '设置成功!')

    # 检测alioss是否可用
    def check_config(self):
        try:
            self.__conn()

            from itertools import islice
            bucket = oss2.Bucket(self.__oss, self.__bucket_domain, self.__bucket_name)
            result = oss2.ObjectIterator(bucket)
            data = []
            path = self.get_path('/')
            '''key, last_modified, etag, type, size, storage_class'''
            for b in islice(oss2.ObjectIterator(bucket, delimiter='/', prefix=path), 1000):
                b.key = b.key.replace(path, '')
                if not b.key: continue
                tmp = {}
                tmp['name'] = b.key
                tmp['size'] = b.size
                tmp['type'] = b.type
                tmp['download'] = self.download_file(path + b.key, False)
                tmp['time'] = b.last_modified
                data.append(tmp)
            return True
        except:
            return False

    # 上传文件到指定目录
    def upload_file_by_path(self, filename, bucket_path):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            # 保存的文件名
            key = filename.split('/')[-1]
            self.__bucket_path = self.get_path(bucket_path)
            key = self.__bucket_path + '/' + key

            # 获取存储对象
            bucket = oss2.Bucket(self.__oss, self.__bucket_domain, self.__bucket_name)

            # 使用断点续传
            oss2.defaults.connection_pool_size = 4
            # print(bucket, key, filename)
            result = oss2.resumable_upload(bucket, key, filename,
                                           store=oss2.ResumableStore(root='/tmp'),  # 进度保存目录
                                           multipart_threshold=1024 * 1024 * 2,
                                           part_size=1024 * 1024,  # 分片大小
                                           num_threads=1)  # 线程数
            # print(u'上传文件到阿里云OSS返回结果：', result)
            return True
        except Exception as ex:
            # print(ex)
            if ex.status == 403:
                time.sleep(5)
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
        bucket = oss2.Bucket(self.__oss, self.__bucket_domain, self.__bucket_name)
        result = bucket.put_object_from_file(path, filename)
        os.remove(filename)
        return public.returnMsg(True, '创建成功!')

    # 取回文件列表
    def get_list(self, get):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            from itertools import islice
            bucket = oss2.Bucket(self.__oss, self.__bucket_domain, self.__bucket_name)
            result = oss2.ObjectIterator(bucket)
            data = []
            path = self.get_path(get.path)
            '''key, last_modified, etag, type, size, storage_class'''
            for b in islice(oss2.ObjectIterator(bucket, delimiter='/', prefix=path), 1000):
                b.key = b.key.replace(path, '')
                if not b.key: continue
                tmp = {}
                tmp['name'] = b.key
                tmp['size'] = b.size
                tmp['type'] = b.type
                tmp['download'] = self.download_file(path + b.key, False)
                tmp['time'] = b.last_modified
                data.append(tmp)
            mlist = {}
            mlist['path'] = get.path
            mlist['list'] = data
            return mlist
        except Exception as ex:
            return public.returnMsg(False, str(ex))

    def sync_date(self):
        import config
        config.config().syncDate(None)

    # 下载文件
    def download_file(self, filename, m=True):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        if m:
            import re
            m_type = 'site'
            if filename[:2] == 'Db':
                m_type = 'database'
                m_name = re.search('Db_(.+)_20\d+_\d+\.', filename).groups()[0]
            else:
                m_name = re.search('Web_(.+)_20\d+_\d+\.', filename).groups()[0]

            filename = self.__bucket_path + m_type + '/' + m_name + '/' + filename
        try:
            bucket = oss2.Bucket(self.__oss, self.__bucket_domain, self.__bucket_name)
            private_url = bucket.sign_url('GET', filename, 3600)
            return private_url
        except:
            print(self.__error_msg)
            return None

    # 取目录路径
    def get_path(self, path):
        if path == '/': path = ''
        if path[:1] == '/':
            path = path[1:]
            if path[-1:] != '/': path += '/'
        if path == '/': path = ''
        return path.replace('//', '/')

    # 删除文件
    def delete_file(self, filename):
        # 连接OSS服务器
        self.__conn()
        if not self.__oss:
            return False

        try:
            bucket = oss2.Bucket(self.__oss, self.__bucket_domain, self.__bucket_name)
            result = bucket.delete_object(filename)
            return result.status
        except Exception as ex:
            if ex.status == 403:
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
