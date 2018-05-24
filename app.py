#!/usr/bin/python

import os
import logging
import sys
import time
import datetime
import schedule

DBHOST = os.getenv("DBHOST")
DBUSER = os.getenv("DBUSER")
DBPASSWORD = os.getenv("DBPASSWORD")
DBNAME= os.getenv("DBNAME")
BACKUPPATH= os.getenv("BACKUPPATH")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

if not DBHOST or DBHOST == "":
    logger.error("please set the environment DBHOST.")
    sys.exit(1)

if not DBUSER or DBUSER == "":
    DBUSER = "root"

if not DBPASSWORD or DBPASSWORD == "":
    logger.error("please set the environment DBPASSWORD.")
    sys.exit(1)

if not DBNAME or DBNAME == "":
    logger.error("please set the environment DBNAME.")
    sys.exit(1)

if not BACKUPPATH or BACKUPPATH == "":
    BACKUPPATH = "/backup"

logger.info("get the value of DBHOST: %s", DBHOST)
logger.info("get the value of DBUSER: %s", DBUSER)
logger.info("get the value of DBPASSWORD: %s", DBPASSWORD)
logger.info("get the value of DBNAME: %s", DBNAME)
logger.info("get the value of BACKUPPATH: %s", BACKUPPATH)

BACKUP_FILE = BACKUPPATH + "/" + DBNAME + ".sql"

if not os.path.exists(BACKUPPATH):
    os.makedirs(BACKUPPATH)

dumpcmd = "mysqldump -u" + DBUSER + " -p" + DBPASSWORD + " -h" + DBHOST + " "+ DBNAME + " > " + BACKUP_FILE
logger.info("backup command: `%s`", dumpcmd)

def job():
    result = os.system(dumpcmd)
    if result == 0:
        logger.info("Success to backup the database.")

schedule.every().hour.do(job)

while True:
    schedule.run_pending()
    time.sleep(5)