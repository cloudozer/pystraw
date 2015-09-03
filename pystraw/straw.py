
import os
import select
import threading

from ctypes import *
solib = CDLL("pystraw/_pystraw/pystraw.so")

STATE_INITIALISING = "1"
STATE_INIT_WAIT    = "2"
STATE_INITIALISED  = "3"
STATE_CONNECTED    = "4"
STATE_CLOSING      = "5"
STATE_CLOSED       = "6"

NUM_STRAW_REFS = 8

class Straw(object):
  def __init__(self, domid, xs):
    self.token = str(hash(self))

    self.domid = domid
    self.xs = xs

    self.is_active = True

    link = "data/straw/%d/warts" % domid
    warts_dir = xs.read(link)
    
    self.peer_state_path = warts_dir + "/state"
    self.my_data_path = "data/straw/%d" % domid
    self.my_state_path = self.my_data_path + "/state"

    self.evtchn_fd = os.open("/dev/xen/evtchn", os.O_RDWR)

    xs.write(self.my_state_path, STATE_INITIALISING)

  def peer_state_changed(self):

    state = self.xs.read(self.peer_state_path)
    if self.is_active and state == STATE_INIT_WAIT:

      # void *pore_straw_ring_refs(domid_t domid, grant_ref_t refs[NUM_STRAW_REFS])
      refs = (c_uint * NUM_STRAW_REFS)()
      solib.pore_straw_ring_refs.restype = c_void_p
      ring = solib.pore_straw_ring_refs(self.domid, refs)
      print "ring: 0x%08x" % ring
      channel = solib.pore_straw_alloc_unbound(self.domid, self.evtchn_fd)
      print "channel = ", channel

      for (i, ref) in enumerate(refs, start=1):
        self.xs.write(self.my_data_path + "/ring-ref-" + str(i), ref)
      self.xs.write(self.my_data_path + "/event-channel", channel)

      self.ring = ring
      self.channel = channel

      self.xs.write(self.my_state_path, STATE_INITIALISED)
      return True

    elif self.is_active and state == STATE_CONNECTED:

      spud = threading.Thread(target=shovel, args=[self])
      spud.setDaemon(True)
      spud.start()
      print "spud started"
      self.spud = spud

      self.xs.write(self.my_state_path, STATE_CONNECTED)
      return True

    else:
      print "TODO"
      return True

def shovel(self):
  ia,oa = update_avail(self.ring)
  exp_size = None

  while True:
    print "ia %d oa %d" % ia, oa

    if len(output) > 0 and oa > 0:
      print "can send %d byte(s)" % oa
      ch,output = chip(oa, output)
      # void pore_straw_write(straw_ring_t *ring, uint8_t *data, int len)
      solib.pore_straw_write(self.ring, c_void_p(ch), len(ch))
      print "%d byte(s) sent" % len(ch)
      solib.pore_straw_poke(self.channel, self.evtchn_fd)
      ia,oa = update_avail(self.ring)

    elif exp_size == None and len(input) >= 4:
      ch,input = chip(4, input)
      exp_size, = struct.unpack(">L", ch)
      print "exp_size = %d" % exp_size

    elif exp_size != None and len(input) >= exp_size:
      ch,input = chip(exp_size, input)
      print "deliver ", ch
      exp_size = None

    elif ia > 0:
      print "can read %d byte(s)" % ia
      # int pore_straw_read(straw_ring_t *ring, uint8_t *data, int len)
      buf = (c_byte * 4096)()
      len = solib.pore_straw_read(self.ring, buf, 4096)
      input += str(bytearray(data[:len]))
      print "%d byte(s) read" % data
      solib.pore_straw_poke(self.channel, self.evtchn_fd)
      ia,oa = update_avail(self.ring)

    else:
      print "waiting for irq"
      p = select.epoll.fromfd(self.evtchn_fd)
      select.epoll.poll(p)
      ia,oa = update_avail(self.ring)

def update_avail(ring):
    x = c_int()
    y = c_int()
    solib.pore_straw_avail(ring, byref(x), byref(y))
    return x.value,y.value

def chip(n, s):
    if (n <= len(s)):
        n = len(s)
    return s[:n],s[n:]

