# 备份运行在 openshift 3 的 MySQL 数据库

在 openshift 3 上使用 mysql-persistent 模版创建数据库应用，数据文件保存在 glusterfs 的存储卷（PVC）上。虽然已经做了数据持久化，仍然
需要考虑 mysql 的备份方案，想起来有两种备份恢复策略：

* 方案一是定期备份 PVC 上的数据文件到另外的存储卷，需要恢复时，从备份存储卷的数据库文件恢复，但是要小心文件的属主和权限问题，会导致备份的
文件并不能被 mysql 实例使用。这个方案是备份 mysql 数据目录中的文件。

* 方案二是定期 dump 要备份的数据库到备份存储卷，需要恢复时，从备份存储卷导入 dump 的文件到数据库中。

这里选用方案二，我们启动一个长期运行的应用进行定期 dump 数据，查看日志可以了解备份操作，进入终端可以查看备份文件，或者进行导入恢复的操作。

## 备份工作

备份工作分几个阶段，准备备份脚本，准备 S2I 构建镜像，编写 template 文件和创建备份应用。

### 备份脚本
首先遇到的问题，如何定时运行 mysqldump 的命令？常规操作是在 Linux 服务器上配置 crontab 的任务。我决定用 python 脚本定时调用命令 
mysqldump，数据库连接信息用环境变量传递给脚本。使用 python 的 dbader/schedule 模块设置定时任务。

https://github.com/dbader/schedule

完成的备份脚本：

https://github.com/douzl/openshift-mysqlbackup/blob/master/app.py

这里展示部分代码。

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
设置定时任务
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

在文件 requirements.txt 增加 ```schedule```，后面构建应用镜像时，S2I 的构建镜像会用这个文件安装 python 的模块依赖。 

### 准备 S2I 构建镜像

遇到的第二个问题，当我用 python:3.6 的 S2I 镜像构建应用镜像时，应用镜像运行的 Pod 总是异常退出，日志显示没有 mysqldump 的命令，在 
[s2i-python-container](https://github.com/sclorg/s2i-python-container/blob/master/3.6/)的 Dockerfile中看到，基础镜像是 
centos7，表明可以运行```yum```命令安装 package mariadb。

下载S2I命令行工具
```
# wget https://github.com/openshift/source-to-image/releases/download/v1.1.11/source-to-image-v1.1.11-78a76d97-linux-amd64.tar.gz
```
下载解压后进目录，运行命令创建新s2i镜像的工作目录
```
# ./s2i create python36-mysql python36-mysql
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

具体模板文件内容，打开下面的链接。
https://github.com/douzl/openshift-mysqlbackup/blob/master/template/python-mysql-backup-template.json

### 部署备份应用

在 openshift 的 WEB 控制台的某个项目下面，选择 ```Add to project``` 中的 ```Using Import YAML/JSON```, 把上面创建好的模板文件粘
贴到对话框里，并应用模板。添加要备份的数据库的信息，创建备份应用，此时，将会创建出 build config, depoly config, image, pvc 等资源。
Build config 完成后，会自动创建备份应用和 pod, 可以通过查看 pod 的日志了解应用运行的情况和备份的情况。

具体的文档，请参考。

https://github.com/douzl/openshift-mysqlbackup/blob/master/README.md

## 总结
使用 mysqldump 做备份不算完整，两次备份间是会有数据丢失的，需要开启数据库的 binlog 做增量备份，这次就不继续补充了，有兴趣的同学可以自行
尝试。

其实我是困惑的，只是想备份个数据库，要不要搞这么多事情。这个问题先留这里，以后等我想明白了再说。