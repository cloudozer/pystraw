
from pyxs import Client

import atexit
import threading
import time

def setup():
  print "register cleanup"
  atexit.register(cleanup)
  print "setup XS directories"
  print "cleanup shared directories"
  print "start watchdog thread"
  _watchdog = threading.Thread(target=doggie)
  _watchdog.setDaemon(True)
  _watchdog.start()

def cleanup():
  print "cleanup shared directories"

def doggie():
  while True:
    print "woof"
    time.sleep(1)

setup()

#def initialise():
#  global _xs
#  _xs = Client()
#
#  global my_domid
#  my_domid = int(_xs.read("domid"))
#
#  straw_top = "data/straw"
#  _xs.mkdir(straw_top)
#  _xs.set_permissions(straw_top, [u'b' + str(my_domid)])
#
#  warts_top = "data/warts"
#  _xs.mkdir(warts_top)
#  _xs.set_permissions(warts_top, [u'r' + str(my_domid)])
#
#  monitor = _xs.monitor()
#  monitor.watch(straw_top, "token1")
# 
#  _watchdog = Thread(target=watchdog, args=[monitor], group=None)
#  _watchdog.start()
#
#def watchdog(monitor):
#  while True:
#    event = monitor.wait()
#    print event

