#!/usr/bin/python

import os
import logging
import sys
import time
import datetime
import schedule

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE= os.getenv("MYSQL_DATABASE")
BACKUP_PATH= os.getenv("BACKUP_PATH")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

if not MYSQL_HOST or MYSQL_HOST == "":
    logger.error("please set the environment MYSQL_HOST.")
    sys.exit(1)

if not MYSQL_USER or MYSQL_USER == "":
    DBUSER = "root"

if not MYSQL_PASSWORD or MYSQL_PASSWORD == "":
    logger.error("please set the environment MYSQL_PASSWORD.")
    sys.exit(1)

if not MYSQL_DATABASE or MYSQL_DATABASE == "":
    logger.error("please set the environment MYSQL_DATABASE.")
    sys.exit(1)

if not BACKUP_PATH or BACKUP_PATH == "":
    BACKUP_PATH = "./backup"

logger.info("get the value of MYSQL_HOST: %s", MYSQL_HOST)
logger.info("get the value of MYSQL_USER: %s", MYSQL_USER)
logger.info("get the value of MYSQL_PASSWORD: %s", MYSQL_PASSWORD)
logger.info("get the value of MYSQL_DATABASE: %s", MYSQL_DATABASE)
logger.info("get the value of BACKUP_PATH: %s", BACKUP_PATH)

BACKUP_FILE = BACKUP_PATH + "/" + MYSQL_DATABASE + ".sql"

if not os.path.exists(BACKUP_PATH):
    os.makedirs(BACKUP_PATH)

dumpcmd = "mysqldump -u" + MYSQL_USER + " -p" + MYSQL_PASSWORD + " -h" + MYSQL_HOST + " "+ MYSQL_DATABASE + " > " + BACKUP_FILE
logger.info("backup command: `%s`", dumpcmd)

def job():
    result = os.system(dumpcmd)
    if result == 0:
        logger.info("Success to backup the database.")

job()
schedule.every().hour.do(job)
while True:
    schedule.run_pending()
    time.sleep(5)