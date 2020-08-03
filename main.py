# -*- coding: utf-8 -*-
"""
Created on Wed Jul 29 22:24:51 2020

@author: apple
"""

from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
r = urlopen('http://www.boc.cn/sourcedb/whpj/')

c=r.read().decode('utf8')
bs_obj = bs(c,'html.parser')
t = bs_obj.find_all('table')[1]
all_tr = t.find_all('tr')
pound =all_tr[8]

a= pound.text[0:37]
print(a)


import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv
import os

#env_path = Path('.') / 'simple.env'
# 把env里的变量写进 电脑里
#load_dotenv(dotenv_path=env_path)
load_dotenv()


#设置服务器所需信息
#163邮箱服务器地址ss
mail_host = os.getenv('EMAIL_HOST')
#163用户名
mail_user = os.getenv('USER')  
#密码(部分邮箱为授权码)
mail_pass = os.getenv('PASS')   
#邮件发送方邮箱地址
sender = os.getenv('EMAIL')
receiver = os.getenv('EMAIL')

receivers = [receiver]  

print('sender', sender)

#设置email信息
#邮件内容设置
message = MIMEText(a)
#邮件主题       
message['Subject'] = 'title' 
#发送方信息
message['From'] = sender 
#接受方信息     
message['To'] = receivers[0]  

#登录并发送邮件
try:
    smtpObj = smtplib.SMTP() 
    #连接到服务器
    smtpObj.connect(mail_host,25)
    #登录到服务器
    smtpObj.login(mail_user,mail_pass) 
    #发送
    smtpObj.sendmail(
        sender,receivers,message.as_string()) 
    #退出
    smtpObj.quit() 
    print('success')
except smtplib.SMTPException as e:
    print('error',e) #打印错误