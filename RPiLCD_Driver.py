#
# RPiLCD Driver
#   Brent Petit - 2015
#
#   Drive LCD updates as well as button actions
#   Originally written to take APRS info and display
#   on screen
#
# Send Data to the Pi LCD
#
import Adafruit_CharLCD as LCD
import threading
import time
import datetime
import sys

lcd = LCD.Adafruit_CharLCDPlate()
mq_lock       = threading.Lock()
mq_work       = threading.Event()
button_push   = threading.Event()
screen_lock   = threading.Lock()

# Message Queue - Messages pulled from head
#  placed on tail
message_queue = []

# Stat Counters
message_count  = 0
receive_count  = 0
transmit_count = 0
igate_count    = 0
digi_count     = 0
start_time     = datetime.datetime.now()
last_entry     = []

#
# Public: lcdMessageInsert
#  insert message into the message queue
#  TODO: List size management
#
def lcdMessageInsert(type, call, path, description):
   global message_count, last_entry
   call = call + ">"
   print type + ":" + call
   my_entry = [ type, call, path, description ]
   last_entry = my_entry
   mq_lock.acquire()
   message_queue.append(my_entry)
   message_count = message_count + 1
   mq_work.set()
   mq_lock.release()

#  print "Exiting lcdMessageInsert"

#
# Public: lcdGetStats
#  return basic stats for processing
#
def lcdGetStats():
   global message_count, receive_count, transmit_count, igate_count, digi_count
   stat_list = { 
      'message_count'  : message_count,
      'receive_count'  : receive_count,
      'transmit_count' : transmit_count,
      'igate_count'    : igate_count,
      'digi_count'     : digi_count,
      'uptime'         : str(datetime.datetime.now() - start_time),
      'last_entry'     : last_entry
   }

   return stat_list

#  print "Exiting lcdGetStats"

#
# Public: lcdMessageLoop
# Thread: Main Message handler loop
#
def lcdMessageLoop():
   print "Starting LCD Update Loop"
   screen_lock.acquire()
   lcd.clear()
   _lcdSetScreenColor("GRAY")
   lcd.message(sys.argv[0] + "\nWelcome...")
   while len(message_queue) == 0:
      mq_work.wait(.25)
      lcd.move_left()
   screen_lock.release()

   while 1:
   
      # Wait for some work to do
      while len(message_queue) == 0:
         mq_work.wait(30)
      
      _lcdProcessInputQueue()

      # print "Queue depth " + str(len(message_queue)) + "\n"

#     print "Exiting lcdMessageLoop"


#
# Public: lcdButtonLoop
# Thread: Main button handler loop
#
def lcdButtonLoop():
   while 1:
      _lcdCheckButtons()

#  print "Exiting lcdButtonLoop"

#
# Private: _lcdScreenUpdate
# Handle updates to LCD screen
# set new message and set screen color
# Scroll text until more work comes in
# Text1 = static text top row left
# Text2 = scrolling text remaining top row
# Text3 = scrolling text all bottom row
#   Note we loop in this function to handle
#   scrolling.
#
def _lcdScreenUpdate(color, text1, text2, text3):
   # Utility string to clear ranges of screen
   clear_string = "                "

   # Set a color for the background
   _lcdSetScreenColor(color)

   # Clear the current content
   lcd.clear()

   iteration = 0

   # Calculate screen real estate for each text
   # section
   text2_start_pos = len(text1)
   text2_field_len = 16 - text2_start_pos
   text2_len = len(text2)
   text3_start_pos = 0
   text3_field_len = 16
   text3_len = len(text3)

   # Each iteration will scroll text in areas where the string
   # is longer than the available screen
   while 1:
      # First time in set text1. This field does not scroll
      # so it should be shorter than 16 characters
      if iteration == 0:
         # Move to upper left of screen
         lcd.home()
         lcd.message(text1)

      if text2_len > 0:
         # Put cursor n the first row, right after text1
         lcd.set_cursor(text2_start_pos, 0)
      
         # Write text2, and calculate scroll movement if we need to
         # scroll 
         if text2_len > text2_field_len:
            text2_cursor = (iteration % text2_len)
            text2_visible_end = text2_cursor + text2_field_len
            if text2_visible_end > text2_len:
               text2_visible_end = text2_len
            lcd.message(text2[text2_cursor:text2_visible_end])

            past_string_pos = text2_start_pos + (text2_visible_end - text2_cursor)
            if(past_string_pos < 16):
               lcd.set_cursor(past_string_pos, 0)
               lcd.message(clear_string[:(16 - past_string_pos)])
         else:
            # Don't need to scroll
            lcd.message(text2)
      
   
      if text3_len > 0:
         # Put cursor right at the beginning of second row
         lcd.set_cursor(text3_start_pos, 1)

         # Write text3, and calculate scroll movement if we need to
         # scroll
         if text3_len > text3_field_len:
            text3_cursor = (iteration % text3_len)
            text3_visible_end = text3_cursor + text3_field_len
            if text3_visible_end > text3_len:
               text3_visible_end = text3_len
            lcd.message(text3[text3_cursor:text3_visible_end])

            past_string_pos = text3_start_pos + (text3_visible_end - text3_cursor)

            if(past_string_pos < 16):
               lcd.set_cursor(past_string_pos, 1)
               lcd.message(clear_string[:(16 - past_string_pos)])
         else:
            # Don't need to scroll
            lcd.message(text3)

      iteration = (iteration + 1) % 256

      # If it's not a full message then exit immediatly
      # We should be in the button loop in this case
      # TODO: clean up the interaction between messages and 
      #       button text
      if text2_len + text3_len == 0:
         break

      # Button was pushed. fall out to let button handler do its thing
      if button_push.is_set():
         break
      
      # Wait a little
      time.sleep(.20)

      # Break out if there is work to do
      if len(message_queue) > 0:
         # Leave the text up for just a little bit
         break
     
# print "Exiting _lcdScreenUpdate"


# 
# Private: _lcdCheckButtons
# If a button is pressed determine the action and build display
# text. The button pushes take precidence over the message queue
# The screen_lock will hold off updates from the message_queue 
# until the status screen times out or the select button is 
# pressed a second time
#
# TODO: is there a better way to detect button push rather than 
#       polling? If not, what is the right sleep time to ensure 
#       we are responsive enough, but not spinning too hard?
#
def _lcdCheckButtons():
   global message_count, receive_count, transmit_count, igate_count, digi_count
   status_display = 0      # Button has been pushed
   updates_screen = False  # Iteration will update screen
   status_screen = 0       # selector for which info to display
   timeout = 40

   # Loop and watch for button pushes
   while 1:
      update_screen = False

      button_push.clear()

      # Check for Button push
      # SELECT = toggle status display
      # LEFT/RIGHT = move through screens
      if lcd.is_pressed(LCD.SELECT):
         button_push.set()
         if not status_display:
            # Grab Hold of the screen
            status_display = True
            screen_lock.acquire()
            update_screen = True
            status_screen = 0
            timeout = 40
         else:
            update_screen = False
            timeout = 0
      elif lcd.is_pressed(LCD.RIGHT):
         button_push.set()
         if status_display:
            update_screen = True
	    status_screen += 1
      elif lcd.is_pressed(LCD.LEFT):
         button_push.set()
         if status_display:
            update_screen = True
            status_screen -= 1

      # Debug stuff
      #print "status_display=" + str(status_display)
      #print "status_screen=" + str(status_display)
      #print "update_screen=" + str(update_screen)
      #print "timeout=" + str(timeout)

      if status_display:
          if update_screen == False:
             timeout = timeout - 1
             time.sleep(.20)
          elif timeout > 0:
             # Wrap, if off the end of screen list
             status_screen = status_screen % 6

             # Choose a status message
             if status_screen == 0:
                message_string = "Total:\n" + str(message_count)
             elif status_screen == 1:
                message_string = "Queued:\n" + str(len(message_queue))
             elif status_screen == 2:
                message_string = "Received:\n" + str(receive_count)
             elif status_screen == 3:
                message_string = "Transmit:\n" + str(transmit_count)
             elif status_screen == 4:
                message_string = "iGate:\n" + str(igate_count)
             elif status_screen == 5:
                message_string = "Digi:\n" + str(digi_count)
             elif status_screen == 5:
                message_string = "About:\n" + sys.argv[0]

             # Update the message on the screen
             _lcdScreenUpdate("YELLOW", message_string, "", "")

             # Don't spin too hard
             time.sleep(.20)

          if timeout == 0:
             button_push.clear()
             status_display = False
             screen_lock.release() 

      else:
         # Don't spin too hard
         time.sleep(.20)

#  print "Exiting _lcdCheckButtons"



#
#  Private: _lcdProcessInputQueue
#  work off the list of messages to display
#
def _lcdProcessInputQueue():
   global receive_count, transmit_count, igate_count, digi_count
   # Pull an entry off the queue
   mq_lock.acquire()

   # Loop through and drain the message queue
   while message_queue:

      mq_work.clear()

      # Remove the entry right away so we can
      # release the lock
      message_entry = message_queue.pop(0)
      mq_lock.release()
     
      # Set screen color based on the type of message 
      if message_entry[0] == "receive":
         color = "BLUE"
         receive_count += 1
      elif message_entry[0] == "transmit":
         color = "RED"
         transmit_count += 1
      elif message_entry[0] == "igate":
         color = "PURPLE"
         igate_count += 1
      elif message_entry[0] == "digi":
         color = "GREEN"
         digi_count += 1
      else:
         color = "RED"

      call = message_entry[1]
      path = message_entry[2]
      description = message_entry[3]

      # print "processing message"

      screen_lock.acquire()
      _lcdScreenUpdate(color, call, path, description)
      screen_lock.release()

      # We're about to look at the queue at the top of the loop
      mq_lock.acquire()
   
   # We were holding the lock to mess with the queue. 
   # Release it on the way out...
   mq_lock.release()

#  print "Exiting _lcdProcessInputQueue"

#
# Private: _lcdSetScreenColor
#
def _lcdSetScreenColor(color):
 
   # Set a color for the background
   if(color == "RED"):
      lcd.set_color(1, 0, 0)
   elif(color == "GREEN"):
      lcd.set_color(0, 1, 0)
   elif(color == "BLUE"):
      lcd.set_color(0, 0, 1)
   elif(color == "YELLOW"):
      lcd.set_color(1, 1, 0)
   elif(color == "PURPLE"):
      lcd.set_color(.75, 0, 1)
   elif(color == "GRAY"):
      lcd.set_color(.5, .5, .5)
   else:
      lcd.set_color(1, 1, 1)
   
#  print "Exiting _lcdSetScreenColor
