#
# Quick and dirty script to 
# Drive LCD web service from direwolf program
#  Brent Petit - 2015
#
# 
import requests
import json
import re
import subprocess
import sys
from requests.auth import HTTPBasicAuth

my_hostname="http://127.0.0.1:5000"
my_username="admin"
my_password="password"
my_call="N0CALL-1"

# Execute direwolf and read stdin

args = ("/usr/local/bin/direwolf", "-t", "0")
popen = subprocess.Popen(args, stdout=subprocess.PIPE)
for output in iter(popen.stdout.readline, ''):
   # Had some issues with exceptions due to unrecognized characters
   # not sure yet if this did the trick...
   try:
      output = output.encode('utf-8', errors='replace')
   except:
      print "ERROR: Choked on input - ", sys.exc_info()[0]
      continue

   print output,

   mygroup = re.match("(\[.+\])\s+([A-Za-z0-9\-]+)\>(.+)\:(.+)", output)
   if mygroup != None:
      #print "#1: " + mygroup.group(1)
      #print "#2: " + mygroup.group(2)
      #print "#3: " + mygroup.group(3)
      #print "#4: " + mygroup.group(4)

      call = mygroup.group(2)
      path = mygroup.group(3)

      if mygroup.group(1) == "[ig]":
         continue
      elif len(mygroup.group(1)) == 4:
         type = "transmit"
         if re.search("TCPIP", output):
            mygroup2 = re.match("[A-Za-z0-9\-\,]+\:\}([A-Za-z0-9\-\,]+)\>(.+)", 
                                str(mygroup.group(3)))
            if mygroup2:
               call = mygroup2.group(1)
               path = mygroup2.group(2)
            else:
               print "Error parsing iGate path: ", mygroup.group(3)
            type = "igate"
         elif re.search(my_call + "\*", output):
            type ="digi"
      else:
         type = "receive"

      print "Type = " + type

      description = mygroup.group(4)

      url = "/RPiLCD_Web_Service/api/v1.0/sendEntry"
      headers = {'Content-Type': 'application/json'}
      payload = {'type': type, 'call': call, 'path': path, 'description': description}
      try:
         r = requests.post(my_hostname+url, headers=headers, data=json.dumps(payload),
                           auth=HTTPBasicAuth(my_username, my_password))
      except:
         print "Unexpected Exception: ", sys.exc_info()[0]

