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
from logging.handlers import TimedRotatingFileHandler
import sys

try:
    from os import scandir
except ImportError:
    from scandir import scandir

remote_ip = sys.argv[1]


class SyncRecord(object):
    """上传录音的程序"""

    def __init__(self, logger):
        self.recordfile_dir = '/home/recordfile'
        self.scp_dst = 'root@{}:/home/recordfile/'.format(remote_ip)
        if not os.path.exists('/recordfile_bak'):
            os.mkdir("/recordfile_bak")
        self.mv_dst = '/recordfile_bak'
        self.log = logger

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
            self.log.error("Email failed:" + str(e))
            return False

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
                        scp_cmd = 'scp %s %s' % (path, self.scp_dst)
                        assert os.popen(scp_cmd)
                        self.log.info('%s has been copy to %s ' % (path, self.scp_dst))
                        self.log.error(path)
                        # 复制成功后的文件移到备份目录中
                        try:
                            mv_cmd = 'mv %s %s' % (path, self.mv_dst)
                            assert os.popen(mv_cmd).read()
                            os.popen(mv_cmd)
                            self.log.info('%s has been moved to %s ' % (path, self.mv_dst))
                        except AssertionError as e:
                            # 移动文件失败，应该是根目录磁盘满了，发邮件警告
                            self.log.error(str(e) + path)
                            host_name = os.popen('hostname').read().strip()
                            self.send_email(host_name, 'Failed to move %s to %s ' % (path, self.mv_dst))
                            # 根目录磁盘满了，退出进程
                            # sys.exit()
                    except Exception as e:
                        # 复制到远程失败，发送警告邮件
                        self.log.error(str(e) + path)
                        host_name = os.popen('hostname').read().strip()
                        message1 = '%s: %s, Failed transfer %s to %s \n' % (
                                        datetime.now(), e, path, self.scp_dst)
                        message2 = "程序休眠10分钟，检查网络是否通畅"
                        self.send_email(host_name, message1 + message2)
                        # 程序休眠10分钟，检查网络
                        time.sleep(600)
            else:
                # 非tar包文件，直接移到备份目录'/recordfile_bak'
                # os.chdir(self.recordfile_dir)
                os.popen('mv %s %s' % (dir_entity.path, self.mv_dst))


def main():
    # 日志回滚
    logging.basicConfig()
    logger = logging.getLogger('logger')
    logger.setLevel(logging.INFO)
    if not os.path.exists('./log'):
        os.mkdir("./log")
    # 创建日志处理对象，保留7天内的日志
    timefile_handler = TimedRotatingFileHandler('log/sync.log', when='M', interval=1, backupCount=7)
    timefile_handler.suffix = "%Y-%m-%d"
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    timefile_handler.setFormatter(formatter)
    logger.addHandler(timefile_handler)

    sync_record = SyncRecord(logger)
    while True:
        sync_record.sync()


if __name__ == '__main__':
    main()
