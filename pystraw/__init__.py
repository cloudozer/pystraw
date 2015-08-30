
from pyxs import Client
from threading import Thread

def initialise():
  global _xs
  _xs = Client()

  global my_domid
  my_domid = int(_xs.read("domid"))

  straw_top = "data/straw"
  _xs.mkdir(straw_top)
  _xs.set_permissions(straw_top, [u'b' + str(my_domid)])

  warts_top = "data/warts"
  _xs.mkdir(warts_top)
  _xs.set_permissions(warts_top, [u'r' + str(my_domid)])

  monitor = _xs.monitor()
  monitor.watch(straw_top, "token1")
 
  _watchdog = Thread(target=watchdog, args=[monitor], group=None)
  _watchdog.start()

def watchdog(monitor):
  while True:
    event = monitor.wait()
    print event

initialise()

