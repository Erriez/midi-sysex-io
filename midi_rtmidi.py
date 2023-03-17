# MIT License
#
# Copyright (c) 2023 Erriez
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Source: https://github.com/Erriez/midi-sysex-io
#

import rtmidi
import sys
import time
import midi_util


class MIDI:
    def __init__(self, verbose=False):
        self._verbose = verbose
        self._midi_in = None
        self._midi_out = None
        self._midi_in_port_id = None
        self._midi_out_port_id = None
        self._midi_in_port_name = None
        self._midi_out_port_name = None

    @staticmethod
    def _get_rtmidi_port_name(port_name):
        # Transform MIDI port name:
        #   From: UM-ONE:UM-ONE MIDI 1 20:0 OUT
        #   To:          UM-ONE MIDI 1 OUT
        if sys.platform == 'linux':
            # Remove first :
            if ':' in port_name:
                port_name = port_name.split(':')[1]
            # Remove bus number
            port_name = port_name.rsplit(' ', 1)[0]
        return port_name

    @staticmethod
    def get_backend_name():
        return 'python-rtmidi'

    @staticmethod
    def get_backend_version():
        return rtmidi.get_rtmidi_version()

    def get_ports_in(self):
        ports = []
        midi_in = rtmidi.MidiIn()
        for port in midi_in.get_ports(encoding='utf-8'):
            ports.append(self._get_rtmidi_port_name(port))
        return ports

    def is_port_in_open(self):
        if self._midi_in:
            return self._midi_in.is_port_open()
        return False

    def port_in_open(self, port_id):
        if self.is_port_in_open():
            return True

        # Open MIDI in port
        self._midi_in = rtmidi.MidiIn()
        if port_id < 0 or port_id >= self._midi_in.get_port_count():
            return False

        #  Get MIDI input port id
        self._midi_in_port_id = port_id

        # Get MIDI in port name
        self._midi_in_port_name = self._get_rtmidi_port_name(self._midi_in.get_port_name(port_id))

        # Enable SYSEX receive
        self._midi_in.ignore_types(sysex=False, timing=False)

        # Return MIDI in port status
        return self._midi_in.open_port(port_id)

    def port_in_close(self):
        if self.is_port_in_open():
            self._midi_in.close_port()
            self._midi_in = None
        self._midi_in_port_id = None
        self._midi_in_port_name = None

    def get_port_in_id(self):
        if self._midi_in_port_id:
            return self._midi_in_port_id

    def get_port_in_name(self):
        if self._midi_in_port_name:
            return self._midi_in_port_name

    def get_ports_out(self):
        ports = []
        midi_out = rtmidi.MidiOut()
        for port in midi_out.get_ports(encoding='utf-8'):
            ports.append(self._get_rtmidi_port_name(port))
        return ports

    def is_port_out_open(self):
        if self._midi_out:
            return self._midi_out.is_port_open()
        return False

    def port_out_open(self, port_id):
        if self.is_port_out_open():
            return True

        # Create MIDI out object
        self._midi_out = rtmidi.MidiOut()

        # Check MIDI output port ID
        if port_id < 0 or port_id >= self._midi_out.get_port_count():
            if self._verbose:
                print('Error: Invalid MIDI output port ID {}'.format(port_id))
            return False

        #  Get MIDI output port id
        self._midi_out_port_id = port_id

        # Get MIDI output port name
        self._midi_out_port_name = self._get_rtmidi_port_name(self._midi_out.get_port_name(port_id))

        # Open MIDI output port
        if not self._midi_out.open_port(port_id):
            if self._verbose:
                print('Error: "{}: Cannot open MIDI output port {}'.format(port_id, self._midi_out_port_name))
            return False

        # Return MIDI output port open status
        return self.is_port_out_open()

    def port_out_close(self):
        if self._midi_out:
            self._midi_out.close_port()
            self._midi_out = None
        self._midi_out_port_id = None
        self._midi_out_port_name = None

    def get_port_out_id(self):
        if self._midi_out_port_id:
            return self._midi_out_port_id

    def get_port_out_name(self):
        if self._midi_out_port_name:
            return self._midi_out_port_name

    def send_message(self, message):
        if not self.is_port_out_open():
            if self._verbose:
                print('MIDI output port not open')
            return False

        if self._verbose:
            midi_util.print_message('TX', message)

        # Write SYSEX message asynchronous to MIDI output port
        self._midi_out.send_message(message)

        # Wait until message transferred
        time.sleep(len(message) * midi_util.MIDI_BYTE_TIME)

    def receive_message(self, timeout=0.2):
        if not self.is_port_in_open():
            if self._verbose:
                print('MIDI input port not open')
            return False

        # Asynchronous MIDI receive protected with a timeout
        t_start = time.time()
        while self.is_port_in_open() and (time.time() - t_start) < timeout:
            # Read one 4 Bytes MIDI message
            message = self._midi_in.get_message()
            if message:
                message = message[0]
                if self._verbose:
                    midi_util.print_message('RX', message)
                return message
