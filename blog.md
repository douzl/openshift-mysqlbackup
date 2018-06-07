# 备份运行在 openshift 3 的 MySQL 数据库

因为遇到了mysql数据库文件影响了数据库的正常运行，且没有找到原因，因此先考虑 mysql 备份恢复方案，做为应对数据库出现问题时的应对方案。

在 openshift 3 上部署的 mysql-persistent 应用，数据文件保存在 PVC上。可以考虑有两种备份恢复策略，

方案一是定期保存 glusterfs 上的文件到备份 PVC，恢复方案是mysql实例启动挂空 PVC 和备份 PVC，从备份 PVC 复制文件到空PVC，并重新启动容器实例。

方案二时启动备份实例定期 dump 数据库到备份 PVC，恢复方案是mysql实例启动挂载空 PVC，从备份实例操作导入备份 dump 到数据库中。

两种方案都可行，不过出于个人意愿选择第二种。

## 备份准备工作

### 备份脚本
首先遇到的问题，如何定时运行 mysqldump 的命令？通常操作是在Linux 服务器上配置crontab的任务，openshift也支持 cron job。

https://docs.openshift.com/container-platform/3.6/dev_guide/cron_jobs.html

经过短暂思考，决定用 python 脚本定时调用命令 mysqldump，数据库连接信息用环境变量传递给脚本。python 定时module用 dbader/schedule。
https://github.com/dbader/schedule

备份脚本：https://github.com/douzl/openshift-mysqlbackup/blob/master/app.py

代码片段
获取环境变量：
```
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE= os.getenv("MYSQL_DATABASE")
BACKUP_PATH= os.getenv("BACKUP_PATH")
```
dump命令
```
dumpcmd = "mysqldump -u" + MYSQL_USER + " -p" + MYSQL_PASSWORD + " -h" + MYSQL_HOST + " "+ MYSQL_DATABASE + " > " + BACKUP_FILE
```
定时任务
```
def job():
    result = os.system(dumpcmd)
    if result == 0:
        logger.info("Success to backup the database.")

job()
schedule.every().hour.do(job)
while True:
    schedule.run_pending()
    time.sleep(5)
```

在文件 requirements.txt 增加 ```schedule```。

### S2I 镜像 Dockerfile

遇到的第二个问题，当我用 python:3.6 的S2I的镜像，运行这个脚本的时候提示没有 mysqldump 的命令，在 [s2i-python-container](https://github.com/sclorg/s2i-python-container/blob/master/3.6/)的 Dockerfile中看到，基础镜像是 centos7，可以运行```yum```命令安装。

下载S2I命令行工具
https://github.com/openshift/source-to-image/releases/download/v1.1.11/source-to-image-v1.1.11-78a76d97-linux-amd64.tar.gz

下载解压后进目录，运行命令创建新s2i镜像的工作目录
```
 ./s2i create python36-mysql python36-mysql
```

复制 python:3.6 的镜像源码文件到 python36-mysql，修改文件 Dockerfile，增加 mariadb 包的安装和创建 /backup 目录。
```
FROM centos/s2i-base-centos7
...
...
RUN INSTALL_PKGS="mariadb rh-python36 rh-python36-python-devel rh-python36-python-setuptools rh-python36-python-pip nss_wrapper \
        httpd24 httpd24-httpd-devel httpd24-mod_ssl httpd24-mod_auth_kerb httpd24-mod_ldap \
        httpd24-mod_session atlas-devel gcc-gfortran libffi-devel libtool-ltdl enchant" && \
    yum install -y centos-release-scl && \
    yum -y --setopt=tsflags=nodocs install --enablerepo=centosplus $INSTALL_PKGS && \
    rpm -V $INSTALL_PKGS && \
    # Remove centos-logos (httpd dependency) to keep image size smaller.
    rpm -e --nodeps centos-logos && \
    yum -y clean all --enablerepo='*'
...
...
RUN source scl_source enable rh-python36 && \
    virtualenv ${APP_ROOT} && \
    chown -R 1001:0 ${APP_ROOT} && \
    fix-permissions ${APP_ROOT} -P && \
    mkdir -p /backup && \
    chown -R 1001:0 /backup && \
    fix-permissions /backup -P && \
    rpm-file-permissions
...
...
CMD $STI_SCRIPTS_PATH/usage
```
然后运行命令 ```make``` 创建镜像，并推送镜像到 openshift 可以拉取镜像的镜像仓库，然后执行导入镜像到 image stream 的操作。

### 创建 template 文件

模板文件内容
https://github.com/douzl/openshift-mysqlbackup/blob/master/template/python-mysql-backup-template.json

## 部署备份应用

参考
https://github.com/douzl/openshift-mysqlbackup/blob/master/README.md