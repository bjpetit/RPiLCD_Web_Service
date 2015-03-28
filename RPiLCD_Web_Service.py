#
# RPiLCD Web Service
#  Brent Petit - 2015
#
# take in messages via a Web Service and update the 
# Raspberry Pi LCD screen.
#
from flask import Flask, jsonify, abort, request
import datetime
import threading
import RPiLCD_Driver

# Use flask for Web Services
app = Flask(__name__)

#
# sendEntry handler
#  This is THE web service call for updating the LCD screen
#   The arguments for this web service are
#   type = what type of messsage? (receive, transmit, digi, gate)
#   call = what was the call sign of the station?
#   path = what AX.25 path did the packet take?
#   description = what additional info was in the packet?
#  TODO: Add authentication
@app.route('/RPiLCD_Web_Service/api/v1.0/sendEntry', methods=['POST'])
def _create_aprs_entry():
   # Do simple validation
   if not request.json or not 'call' in request.json:
      abort(400)

   type = request.json['type'] 
   call = request.json['call']
   path = request.json.get('path', "")
   description = request.json.get('description', "") 

   # Insert the data into the PiLDC_Driver message queue
   RPiLCD_Driver.lcdMessageInsert(type, call, path, description)

   return jsonify({'Message': 'Added Entry'}), 201

#
# 404 Handler
#
@app.errorhandler(404)
def _not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

def start_LCD_thread():
   RPiLCD_Driver.lcdMessageLoop()

def start_button_thread():
   RPiLCD_Driver.lcdButtonLoop()

#
# Main Task: Fire up threads and start Flask service
#
if __name__ == '__main__':
   print "Starting LCD Update Thread..."
   lcd = threading.Thread(target=start_LCD_thread)
   lcd.setDaemon(True)
   lcd.start()
   print "LCD Update Thread Started"

   print "Starting Button Handler Thread..."
   buttons = threading.Thread(target=start_button_thread)
   buttons.setDaemon(True)
   buttons.start()
   print "Button Handler Thread Started"

   print "Entering Web Service Loop"
   app.run(host='0.0.0.0')
   print "Exiting..."

