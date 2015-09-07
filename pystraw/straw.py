
import os
import select
import threading
import Queue
import struct
import json

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
  def __init__(self, domid, xs, deliver, mailbox):
    self.token = str(hash(self))

    self.domid = domid
    self.xs = xs
    self.deliver = deliver
    self.mailbox = mailbox

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
      channel = solib.pore_straw_alloc_unbound(self.domid, self.evtchn_fd)

      for (i, ref) in enumerate(refs, start=1):
        self.xs.write(self.my_data_path + "/ring-ref-" + str(i), ref)
      self.xs.write(self.my_data_path + "/event-channel", channel)

      self.ring = ring
      self.channel = channel

      self.xs.write(self.my_data_path + "/format", "json")

      self.xs.write(self.my_state_path, STATE_INITIALISED)
      return True

    elif self.is_active and state == STATE_CONNECTED:

      spud = threading.Thread(target=shovel, args=[self])
      spud.setDaemon(True)
      spud.start()
      self.spud = spud

      self.xs.write(self.my_state_path, STATE_CONNECTED)
      return True

    else:
      print "TODO"
      return True

  def dispatch(env):
    print "TODO: inject data into spud"

def shovel(self):
  inp = ""
  outp = ""

  ia,oa = update_avail(self.ring)
  exp_size = None

  while True:

    if len(outp) > 0 and oa > 0:
      ch,outp = chip(oa, outp)
      # void pore_straw_write(straw_ring_t *ring, uint8_t *data, int len)
      solib.pore_straw_write(c_void_p(self.ring), c_char_p(ch), len(ch))
      solib.pore_straw_poke(self.channel, self.evtchn_fd)
      ia,oa = update_avail(self.ring)

    elif exp_size == None and len(inp) >= 4:
      ch,inp = chip(4, inp)
      exp_size, = struct.unpack(">L", ch)

    elif exp_size != None and len(inp) >= exp_size:
      ch,inp = chip(exp_size, inp)
      self.deliver(json.loads(ch))
      exp_size = None

    elif ia > 0:
      # int pore_straw_read(straw_ring_t *ring, uint8_t *data, int len)
      buf = (c_ubyte * 16384)()
      n = solib.pore_straw_read(c_void_p(self.ring), buf, 16384)
      inp += str(bytearray(buf[:n]))
      solib.pore_straw_poke(self.channel, self.evtchn_fd)
      ia,oa = update_avail(self.ring)

    else:
      # waiting for irq
      ep = select.epoll(1)
      ep.register(self.evtchn_fd, select.EPOLLIN | select.EPOLLOUT)
      ep.poll(100)
      ep.close()

      if not self.mailbox.empty():
        env = self.mailbox.get()
        j = json.dumps(env)
        outp += struct.pack(">L", len(j))
        outp += j

      ia,oa = update_avail(self.ring)

def update_avail(ring):
    x = c_int()
    y = c_int()
    solib.pore_straw_avail(c_void_p(ring), byref(x), byref(y))
    return x.value,y.value

def chip(n, s):
    if n > len(s):
        n = len(s)
    return s[:n],s[n:]

