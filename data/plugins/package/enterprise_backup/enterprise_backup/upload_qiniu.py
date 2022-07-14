#!/usr/bin/python
# coding: utf-8

from __future__ import absolute_import, print_function
import os, json, sys
from qiniu import Auth, put_file, etag

if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
os.chdir('/www/server/panel')
sys.path.insert(0, "class/")
import public


class qiniu_main:
    __oss = None
    __bucket_name = None
    __bucket_domain = None
    __bucket_path = None
    __bucket_path_bak = None
    __error_count = 0
    __error_msg = "ERROR: 无法连接到七牛云OSS服务器，请检查[AccessKeyId/AccessKeySecret]设置是否正确!"
    __configPath = '/www/server/panel/plugin/enterprise_backup/config'
    __exclude = ""

    def __init__(self):
        if not os.path.exists(self.__configPath):
            os.makedirs(self.__configPath)
        self.__conn()

    def __conn(self):
        if self.__oss: return
        # 获取秘钥
        keys = self.GetConfig()

        self.__bucket_name = keys[2]
        if keys[3].find(keys[2]) != -1: keys[3] = keys[3].replace(keys[2] + '.', '')
        self.__bucket_domain = keys[3]
        self.__bucket_path = self.get_path(keys[4] + '/bt_backup/')
        self.__bucket_path_bak = self.__bucket_path
        if self.__bucket_path[:1] == '/': self.__bucket_path = self.__bucket_path[1:]

        try:
            # 构建鉴权对象
            self.__oss = Auth(keys[0], keys[1])
        except Exception as ex:
            print(self.__error_msg, str(ex))

    def GetConfig(self, get=None):
        path = self.__configPath + '/qiniu.conf'
        # if not os.path.exists(path):
        #     if os.path.exists('/www/server/panel/plugin/qiniu/config.conf'):
        #         public.writeFile(path, public.readFile('/www/server/panel/plugin/qiniu/config.conf'))
        if not os.path.exists(path): return ['', '', '', '', '/']
        conf = public.readFile(path)
        if not conf: return ['', '', '', '', '/']
        result = conf.split('|')
        if len(result) < 5: result.append('/')
        return result

    def SetConfig(self, get):
        path = self.__configPath + '/qiniu.conf'
        conf = get.access_key.strip() + '|' + get.secret_key.strip() + '|' + get.bucket_name.strip() + '|' + get.bucket_domain.strip() + '|' + get.bucket_path.strip()
        public.writeFile(path, conf)
        return public.returnMsg(True, '设置成功!')

    # 检测是否可用
    def check_config(self):
        try:
            path = ''
            bucket = self.get_bucket()
            delimiter = '/'
            marker = None
            limit = 1000
            path = self.get_path(path)
            ret, eof, info = bucket.list(self.__bucket_name, path, marker, limit, delimiter)
            if ret:
                return True
            else:
                return False
        except:
            return False

    def get_bucket(self):
        """获取存储空间"""

        from qiniu import BucketManager
        bucket = BucketManager(self.__oss)
        return bucket

    def create_dir(self, dir_name):
        """创建远程目录

        :param dir_name: 目录名称
        :return:
        """

        try:
            dir_name = self.get_path(dir_name)
            local_file_name = '/tmp/dirname.pl'
            public.writeFile(local_file_name, '')
            token = self.__oss.upload_token(self.__bucket_name, dir_name)
            ret, info = put_file(token, dir_name, local_file_name)

            try:
                os.remove(local_file_name)
            except:
                pass

            if info.status_code == 200:
                return True
            return False
        except Exception as e:
            raise RuntimeError("创建目录出现错误:" + str(e))

    def get_list(self, path="/"):
        if path == '/': path = ''
        bucket = self.get_bucket()
        delimiter = '/'
        marker = None
        limit = 1000
        path = self.get_path(path)
        ret, eof, info = bucket.list(self.__bucket_name, path, marker, limit, delimiter)
        data = []
        if ret:
            commonPrefixes = ret.get("commonPrefixes")
            if commonPrefixes:
                for prefix in commonPrefixes:
                    tmp = {}
                    key = prefix.replace(path, '')
                    tmp['name'] = key
                    tmp['type'] = None
                    data.append(tmp)

            items = ret['items']
            for item in items:
                tmp = {}
                key = item.get("key")
                key = key.replace(path, '')
                if not key:
                    continue
                tmp['name'] = key
                tmp['size'] = item.get("fsize")
                tmp['type'] = item.get("type")
                tmp['time'] = item.get("putTime")
                tmp['download'] = self.generate_download_url(path + key)
                data.append(tmp)
        else:
            if hasattr(info, "error"):
                raise RuntimeError(info.error)
        mlist = {'path': path, 'list': data}
        return mlist

    def generate_download_url(self, object_name, expires=60 * 60):
        """生成时效下载链接"""
        domain = self.__bucket_domain
        base_url = 'http://%s/%s' % (domain, object_name)
        timestamp_url = self.__oss.private_download_url(base_url, expires=expires)
        return timestamp_url

    def resumable_upload(self, local_file_name, bucket_path, object_name=None, progress_callback=None, progress_file_name=None, retries=5):
        """断点续传

        :param local_file_name: 本地文件名称
        :param object_name: 指定OS中存储的对象名称
        :param progress_callback: 进度回调函数，默认是把进度信息输出到标准输出。
        :param progress_file_name: 进度信息保存文件，进度格式参见[report_progress]
        :param retries: 上传重试次数
        :return: True上传成功/False or None上传失败
        """

        try:
            upload_expires = 60 * 60

            if object_name is None:
                temp_file_name = os.path.split(local_file_name)[1]
                self.__bucket_path = self.get_path(bucket_path)
                object_name = self.__bucket_path + '/' + temp_file_name

            token = self.__oss.upload_token(self.__bucket_name, object_name, upload_expires)

            if object_name[:1] == "/":
                object_name = object_name[1:]

            # print("|-正在上传到 {}...".format(object_name))
            ret, info = put_file(token,
                                 object_name,
                                 local_file_name,
                                 check_crc=True,
                                 progress_handler=progress_callback,
                                 bucket_name=self.__bucket_name,
                                 part_size=1024 * 1024 * 4,
                                 version="v2")

            upload_status = False
            if sys.version_info[0] == 2:
                upload_status = ret['key'].encode('utf-8') == object_name
            elif sys.version_info[0] == 3:
                upload_status = ret['key'] == object_name
            if upload_status:
                return ret['hash'] == etag(local_file_name)
            return False
        except Exception as e:
            print("文件上传出现错误：", str(e))

        # 重试断点续传
        if retries > 0:
            print("重试上传文件....")
            return self.resumable_upload(
                local_file_name,
                bucket_path,
                object_name=object_name,
                progress_callback=progress_callback,
                progress_file_name=progress_file_name,
                retries=retries - 1,
            )
        return False

    # 上传文件到指定目录
    def upload_file_by_path(self, filename, bucket_path):
        return self.resumable_upload(filename, bucket_path)

    def delete_object_by_os(self, object_name):
        """删除对象"""

        bucket = self.get_bucket()
        res, info = bucket.delete(self.__bucket_name, object_name)
        return res == {}

    def get_object_info(self, object_name):
        """获取文件对象信息"""
        try:
            bucket = self.get_bucket()
            result = bucket.stat(self.__bucket_name, object_name)
            return result[0]
        except:
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
    def remove_file(self, get):
        try:
            filename = get.filename
            path = get.path

            if path[-1] != "/":
                file_name = path + "/" + filename
            else:
                file_name = path + filename

            if file_name[-1] == "/":
                return public.returnMsg(False, "暂时不支持目录删除！")

            if file_name[:1] == "/":
                file_name = file_name[1:]

            if self.delete_object_by_os(file_name):
                return public.returnMsg(True, '删除成功')
            return public.returnMsg(False, '文件{}删除失败, path:{}'.format(file_name, get.path))
        except:
            print(self.__error_msg)
            return False
