#!/usr/bin/env python
# coding:utf-8
# author: dainel & Seven

import os
from operator import methodcaller
import time
from datetime import datetime
import logging
import smtplib
from email.mime.text import MIMEText
import sys
import subprocess
import paramiko

try:
    from os import scandir
except ImportError:
    from scandir import scandir
# 开发模式用debug, 生产模式用info
logging.basicConfig(level=logging.INFO, format='%(asctime)s-%(levelname)s-%(message)s')

remote_ip = sys.argv[1]


class SyncRecord(object):
    """上传录音的程序"""

    def __init__(self):
        self.recordfile_dir = '/home/recordfile'
        self.scp_dst = 'root@{}:/home/recordfile/'.format(remote_ip)
        if not os.path.exists('/recordfile_bak'):
            os.mkdir("/recordfile_bak")
        self.mv_dst = '/recordfile_bak'
        self.sftp = self._sftp_client

    def send_email(self, sub, content):
        mailto_list = ["936844218@qq.com"]
        # 设置服务器，用户名、口令
        mail_server = "smtp.exmail.qq.com"
        mail_user = "caizhihua@lsrobot.vip"
        mail_passwd = "Listenrobot123"

        msg = MIMEText(content, 'html', 'utf-8')
        msg['Subject'] = sub
        msg['From'] = mail_user + "<new_sync>"
        msg['To'] = ",".join(mailto_list)
        try:
            server = smtplib.SMTP()
            server.connect(mail_server)
            server.login(mail_user, mail_passwd)
            server.sendmail(mail_user, mailto_list, msg.as_string())
            server.close()
            return True
        except Exception as e:
            logging.error("Email failed:" + str(e))
            return False

    @property
    def _sftp_client(self):
        """用paramiko.SFTPClient对象在不同的服务器间传递文件"""
        transport = paramiko.Transport(remote_ip, 22)
        try:
            # 使用秘钥连接
            private_key = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')
            transport.connect(username="root", pkey=private_key)
        except Exception as e:
            logging.warning(str(e))
            # 使用用户名和密码连接
            transport.connect(username='root', password=os.getenv('PASSWORD'))
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp

    def sync(self):
        dir_entities = scandir(self.recordfile_dir)
        # 按inode的modifytime排序，时间倒叙
        dir_entities = sorted(dir_entities, key=methodcaller('inode'))
        # 遍历文件夹'/home/recordfile'内的所有文件
        for dir_entity in dir_entities:
            path = dir_entity.path
            name = path[-3:]
            if name == 'tar':
                cur_time = time.time()
                m_time = os.path.getmtime(path)
                # 复制一分钟前的文件到远程服务器
                if cur_time - m_time > 60:
                    try:
                        self.sftp.put(path, path)
                        logging.info('%s has been copy to %s ' % (path, self.scp_dst))
                        # 复制成功后的文件移到备份目录中
                        try:
                            mv_cmd = 'cp %s %s' % (path, self.mv_dst)
                            subprocess.check_call(mv_cmd, shell=True)
                            logging.info('%s has been moved to %s ' % (path, self.mv_dst))
                        except Exception as e:
                            # 移动文件失败，应该是根目录磁盘满了，发邮件警告
                            logging.error(str(e) + "move failed")
                            host_name = os.popen('hostname').read().strip()
                            self.send_email(host_name, 'Failed to move %s to %s ' % (path, self.mv_dst))
                            # 根目录磁盘满了，退出进程
                            # sys.exit()
                    except Exception as e:
                        # 复制到远程失败，发送警告邮件
                        logging.error(str(e))
                        host_name = os.popen('hostname').read().strip()
                        message1 = '%s: %s, Failed transfer %s to %s \n' % (
                            datetime.now(), e, path, self.scp_dst)
                        message2 = "程序休眠5分钟，检查网络和服务器"
                        self.send_email(host_name, message1 + message2)
                        # 程序休眠5分钟，检查网络
                        time.sleep(300)
                        # 连接断了，socket关闭了，所以此处要重新连接
                        self.sftp = self._sftp_client
            else:
                # 非tar包文件，直接移到备份目录'/recordfile_bak'
                subprocess.check_call('mv %s %s' % (dir_entity.path, self.mv_dst), shell=True)
                logging.warning('%s has been move to %s' % (dir_entity.path, self.mv_dst))


def main():
    sync_record = SyncRecord()
    while True:
        sync_record.sync()

if __name__ == '__main__':
    main()
