
import pyxs
import atexit
import threading
import Queue
import time
import re

from straw import Straw

def start():
  xs = pyxs.Client()
  atexit.register(cleanup, xs)

  global my_domid
  my_domid = int(xs.read("domid"))

  straw_top = "data/straw"
  xs.mkdir(straw_top)
  xs.set_permissions(straw_top, [u'b' + str(my_domid)])

  warts_top = "data/warts"
  xs.mkdir(warts_top)
  xs.set_permissions(warts_top, [u'r' + str(my_domid)])

  monitor = xs.monitor()
  monitor.watch(straw_top, "top")
 
  doggie = threading.Thread(target=watchdog, args=[xs,monitor])
  doggie.setDaemon(True)
  doggie.start()

def cleanup(xs):
  xs.rm("data/straw")
  xs.rm("data/warts")

def incoming(env):
  print "MESSAGE ", env["msg"], " TO ", env["addr"]

def watchdog(xs, monitor):
  global mailboxes
  mailboxes = {}

  straws = {}

  while True:
    event = monitor.wait()
    m = re.match("data/straw/([0-9]+)/warts", event.path)
    if m:
      domid = int(m.group(1))

      mailbox = Queue.Queue()
      mailboxes[domid] = mailbox

      straw = Straw(domid, xs, incoming, mailbox)
      monitor.watch(straw.peer_state_path, straw.token)
      straws[straw.peer_state_path] = straw

    elif event.path in straws:
      straw = straws[event.path]
      if not straw.peer_state_changed():
        monitor.unwatch(event.path, straw.token)
        xs.rm(straw.my_data_path)
        del straws[event.path]

def send(domid, name, msg):
  global mailboxes

  if not domid in mailboxes:
    print "No straw to domain %d\n" % domid
    return

  env = {"addr": name, "msg": msg}
  mailboxes[domid].put(env)

