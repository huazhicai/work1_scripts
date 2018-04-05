#!/bin/bash
# author: Seven

# update.sh 系统又原来的supervisor的部署方式改为
# docker容器部署的方式，数据的迁移
# 先检查磁盘的空间大小

# 停止旧服务器上所有进程
stop_progress()
{	
	supervisorctl stop all
	mv /etc/supervisord.conf /etc/supervisord.conf.bak 
	killall beam.smp
	systemctl stop rabbitmq-server
	chkconfig rabbitmq-server off
	systemctl stop nginx
	systemctl disable nginx
	systemctl stop redis
	systemctl disable redis
	systemctl disable redis.service
	
}
stop_progress


# 安装阿里云yum源，更新kernel
yum_install()
{
	rm -rf /etc/yum.repos.d/*
	curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo
	curl -o /etc/yum.repos.d/epel.repo http://mirrors.aliyun.com/repo/epel-7.repo
	yum makecache fast
	yum install kernel-3.10.0-693.11.1.el7 -y
	yum -y install git
}
yum_install


# 导出数据
export_data()
{
	yum install -y https://mirrors.aliyun.com/mongodb/yum/redhat/7/mongodb-org/3.2/x86_64/RPMS/mongodb-org-tools-3.2.6-1.el7.x86_64.rpm
	mkdir -p /backup/mongo && mkdir /backup/pg
	sleep 1
	cd /backup/mongo && mongodump 
	cd /backup/pg  && pg_dump -U postgres yfsrobot > dbexport.pgsql
	systemctl stop postgresql-9.5.service
	systemctl disable postgresql-9.5.service
	killall mongod 
	mv /usr/local/mongodb/bin/mongodb.conf /usr/local/mongodb/bin/mongodb.conf.bak
}
export_data


# 检查docker&docker-compose是否安装
docker_install()
{	
	# doc=$(yum list installed | grep docker)
	# if [ -n "$doc" ];then
	# 	yum remove $(yum list installed|grep docker|awk '{print $1}')
	# fi
	yum install -y https://mirrors.aliyun.com/docker-ce/linux/centos/7/x86_64/stable/Packages/docker-ce-17.12.1.ce-1.el7.centos.x86_64.rpm
    curl -L https://github.com/docker/compose/releases/download/1.18.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    systemctl start docker && systemctl enable docker
}
docker_install


# pull docker包
pull_docker()
{
	cd ~
	git clone http://git.listenrobot.com/yunwei/old-telemarket-deploy.git
	cd old-telemarket-deploy
	# 登录docker
	docker login --username=deploy-ls@sun-person -p Deployls1 registry.cn-hangzhou.aliyuncs.com
	sh 1create_secrete.sh
	docker-compose -f docker-base.yml up -d && docker-compose up -d 
	# sh create_db.sh
	sleep 1
}
pull_docker


# 安装mongodump, 提取老数据
import_data()
{	
	cd /root/old-telemarket-deploy
	docker-compose down -v && docker-compose -f docker-base.yml down -v && mv data/postgresql/db/ data/postgresql/db_new_bk
	docker-compose -f docker-base.yml up -d mongodb && docker-compose -f docker-base.yml up -d tm-postgersql 
	cd /root/old-telemarket-deploy/data/mongodb && mv dump dump_bak && mv /backup/mongo/dump .
	mv /backup/pg/* /root/old-telemarket-deploy/data/postgresql/dump
	cd /root/old-telemarket-deploy
	/root/old-telemarket-deploy/restore_mongo.sh
	cd /root/old-telemarket-deploy && docker-compose exec tm-postgersql bash /bin/restore_pgsql.sh
}
import_data


# 录音文件和摸板
extract_recordfile_template()
{
	cd /root/old-telemarket-deploy && docker-compose down -v
	if [ -d "/root/old-telemarket-deploy/data/recodedata/recordfile/" ];then
		cd /root/old-telemarket-deploy/data/recodedata/ && mv recordfile recordfile.bak
	fi
	mv /recodedata/recordfile /root/old-telemarket-deploy/data/recodedata/

	if [ -d "/root/old-telemarket-deploy/data/template/" ]; then
		cd /root/old-telemarket-deploy/data/ && mv template template.bak 
	fi
	mv /data/template /root/old-telemarket-deploy/data/
}
extract_recordfile_template


# 重建Mongo索引, 重启服务
mongo_index()
{
	cd /root/old-telemarket-deploy
	docker-compose -f docker-base.yml exec mongodb mongo --username yfsrobot --password yfsrobotksdw1212180 --authenticationDatabase admin <<EOF
use yfsrobot
db.getCollectionNames().forEach(function(collName) {
	db.runCommand({dropIndexes: collName, index: "*"});
});
EOF
	sleep 2
	cd /root/old-telemarket-deploy && docker-compose -f docker-base.yml up -d && docker-compose up -d 
	sh create_db.sh

}
mongo_index


# 暂停老服务上的celery
pip uninstall celery


