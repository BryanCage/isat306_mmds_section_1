#===============================================================
#    !/usr/bin/env python
#    encoding: utf-8
#    -*- coding: utf-8 -*-#    MMDS v. 6.0
#    (c) 2018, Bryan Cage
#    This is an Open Source Project
#    http://opensource.org/licenses/MIT

#    MIT license, all text above must be included in any redistribution
#    **********************************************************************

#    This script will run with cron job to upload all new data records, pictures, and video to the database
#    bryancag_mmds_records stored on the server at BlueHost
    
#===============================================================

import mysql.connector
import base64
import io
from PIL import Image
import cStringIO
import sys
import PIL.Image

config = {
    
    'user':'bryancag_mmds',
    'password':'$Banner15',
    'host':'50.87.192.61',
    'database': 'bryancag_mmds_records'
    
    }
##db = mysql.connector.connect(**config)
##image = Image.open('/home/pi/mammal_monitor/UI/10282018185531.jpg')
##blob_value = open('/home/pi/mammal_monitor/UI/10282018185531.jpg','rb').read()
##print type(blob_value)
##sql = 'INSERT INTO records (images) VALUES (%s)'
##args = (blob_value,)
##cursor = db.cursor()
##cursor.execute(sql, args)
##sql1='SELECT * from records'
##db.commit()
##cursor.execute(sql1)
##data=cursor.fetchall()
##print type(data[0][0])
##file_like = cStringIO.StringIO(data[0][0])
##img = PIL.Image.open(file_like)
##img.show()
##
##db.close()


with open('12092018130821.jpg', 'rb') as f:
    photo = f.read()
encodestring = base64.b64encode(photo)
db = mysql.connector.connect(**config)
mycursor= db.cursor()
print("Inseting in db")
sql = ("INSERT INTO records (images) VALUES (%s)")

mycursor.execute(sql,(encodestring,))
db.commit()
sql1 ="SELECT * from records"
mycursor.execute(sql1)
data = mycursor.fetchall()
print(data)
data1=base64.b64decode(data[0][0])
print type(data1)
file_like=io.BytesIO(data1)
img=PIL.Image.open(file_like)
img.show()
db.close()
