#
# Drive LCD web service from direwolf program
#  Brent Petit - 2015
#
# 
import time
import random
import requests
import json
import re
import subprocess

type_list = [ "receive", "transmit", "digi" ]

# Execute direwolf and read stdin

args = ("/usr/local/bin/direwolf", "-t", "0")
popen = subprocess.Popen(args, stdout=subprocess.PIPE)
for output in iter(popen.stdout.readline, ''):
   # Had some issues with exceptions due to unrecognized characters
   # not sure yet if this did the trick...
   output = output.encode('utf-8')
   print output,

   mygroup = re.match("(\[.+\])\s+([A-Za-z0-9\-]+)\>(.+)\:(.+)", output)
   if mygroup != None:
      #print "#1: " + mygroup.group(1)
      #print "#2: " + mygroup.group(2)
      #print "#3: " + mygroup.group(3)
      #print "#4: " + mygroup.group(4)

      if mygroup.group(1) == "[ig]":
         type = "gate"
      elif len(mygroup.group(1)) == 4:
         type = "transmit"
      else:
         type = "receive"

      print "Type = " + type

      call = mygroup.group(2)
      path = mygroup.group(3)

      description = mygroup.group(4)

      url = "/RPiLCD_Web_Service/api/v1.0/sendEntry"
      hostname = "http://127.0.0.1:5000"
      headers = {'Content-Type': 'application/json'}
      payload = {'type': type, 'call': call, 'path': path, 'description': description}
      r = requests.post(hostname+url, headers=headers, data=json.dumps(payload))
