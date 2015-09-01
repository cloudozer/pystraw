
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

    xs.write(self.my_state_path, STATE_INITIALISING)

  def peer_state_changed(self):
    state = self.xs.read(self.peer_state_path)
    if self.is_active and state == STATE_INIT_WAIT:

      ## int pore_straw_open(domid_t domid, grant_ref_t refs[NUM_STRAW_REFS], uint32_t *evtchn)
      refs = (c_uint * NUM_STRAW_REFS)()
      channel = c_uint()
      rs = solib.pore_straw_open(self.domid, refs, byref(channel))
      assert rs == 0

      for (i, ref) in enumerate(refs, start=1):
        self.xs.write(self.my_data_path + "/ring-ref-" + str(i), ref)
      self.xs.write(self.my_data_path + "/event-channel", channel.value)

      self.xs.write(self.my_state_path, STATE_INITIALISED)
      return True

    elif self.is_active and state == STATE_CONNECTED:
      self.xs.write(self.my_state_path, STATE_CONNECTED)
      return True

    else:
      print "TODO"
      return True

