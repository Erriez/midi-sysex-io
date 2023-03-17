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

# Suppress pygame console strings
from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import pygame.midi
import pygame.version
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

    def _init(self):
        if not self._midi_in and not self._midi_out:
            # Initialize PyGame MIDI
            pygame.midi.init()

    def _end(self):
        if not self._midi_in and not self._midi_out:
            # Quit PyGame MIDI
            pygame.midi.quit()

    @staticmethod
    def get_backend_name():
        return 'pygame'

    @staticmethod
    def get_backend_version():
        return pygame.version.ver

    # def print_available_ports(self):
    #     # Initialize PyGame MIDI
    #     self._init()
    #
    #     # Print MIDI input and output port ID's and names
    #     print('MIDI output ports:')
    #     port_id = 1
    #     for i in range(pygame.midi.get_count()):
    #         (midi_interface, midi_name, midi_input, midi_output, opened) = pygame.midi.get_device_info(i)
    #         if midi_output:
    #             print('  {}: {} OUT'.format(port_id, midi_name.decode('utf-8')))
    #             port_id += 1
    #
    #     # Print MIDI input and output port ID's and names
    #     print('MIDI input ports:')
    #     port_id = 1
    #     for i in range(pygame.midi.get_count()):
    #         (midi_interface, midi_name, midi_input, midi_output, opened) = pygame.midi.get_device_info(i)
    #         if midi_input:
    #             print('  {}: {} IN'.format(port_id, midi_name.decode('utf-8')))
    #             port_id += 1
    #
    #     # End PyGame MIDI
    #     self._end()

    def get_ports_in(self):
        # Initialize PyGame MIDI
        self._init()

        ports = []
        for i in range(pygame.midi.get_count()):
            (midi_interface, midi_name, midi_input, midi_output, opened) = pygame.midi.get_device_info(i)
            if midi_input:
                ports.append(midi_name.decode('utf-8'))

        # End PyGame MIDI
        self._end()

        return ports

    def is_port_in_open(self):
        if self._midi_in:
            return True
        return False

    def port_in_open(self, port_id):
        if self.is_port_in_open():
            return True

        # Initialize PyGame MIDI
        self._init()

        # Open MIDI input port
        port_in_id = 0
        for i in range(pygame.midi.get_count()):
            (midi_interface, midi_name, midi_input, midi_output, opened) = pygame.midi.get_device_info(i)
            if midi_input:
                if port_id == port_in_id:
                    # Open MIDI input port
                    self._midi_in = pygame.midi.Input(i)

                    #  Get MIDI input port id
                    self._midi_in_port_id = port_in_id

                    #  Get MIDI input port name
                    self._midi_in_port_name = midi_name.decode('utf-8')
                    self._midi_in_port_name += ' IN'

                    break
                port_in_id += 1

        if not self._midi_in:
            return False

        # Return MIDI input port open status
        return self.is_port_in_open()

    def port_in_close(self):
        if self._midi_in:
            self._midi_in.close()
            self._midi_in = None
        self._midi_in_port_name = None

        # End PyGame MIDI
        self._end()

    def get_port_in_id(self):
        if self._midi_in_port_id:
            return self._midi_in_port_id

    def get_port_in_name(self):
        if self._midi_in_port_name:
            return self._midi_in_port_name

    def get_ports_out(self):
        # Initialize PyGame MIDI
        self._init()

        ports = []
        for i in range(pygame.midi.get_count()):
            (midi_interface, midi_name, midi_input, midi_output, opened) = pygame.midi.get_device_info(i)
            if midi_output:
                ports.append(midi_name.decode('utf-8'))

        # End PyGame MIDI
        self._end()

        return ports

    def is_port_out_open(self):
        if self._midi_out:
            return True
        return False

    def port_out_open(self, port_id):
        if self.is_port_out_open():
            return True

        # Initialize PyGame MIDI
        self._init()

        # Check MIDI output port ID
        if port_id < 0:
            if self._verbose:
                print('Error: Invalid MIDI output port ID {}'.format(port_id))
            return False

        # Open MIDI output port
        port_out_id = 0
        for i in range(pygame.midi.get_count()):
            (midi_interface, midi_name, midi_input, midi_output, opened) = pygame.midi.get_device_info(i)
            if midi_output:
                if port_out_id == port_id:
                    # Open MIDI output port
                    self._midi_out = pygame.midi.Output(i)

                    # MIDI output port id
                    self._midi_out_port_id = port_out_id

                    # Get MIDI output port name
                    self._midi_out_port_name = midi_name.decode('utf-8')
                    self._midi_out_port_name += ' OUT'

                    break
                port_out_id += 1

        # Check if MIDI port is output
        if not self._midi_out:
            if self._verbose:
                print('Error: "{}: {}" is not a MIDI output port'.format(port_id, self._midi_out_port_name))
            return False

        # Return MIDI output port open status
        return self.is_port_out_open()

    def port_out_close(self):
        if self._midi_out:
            self._midi_out.close()
            self._midi_out = None
        self._midi_out_port_name = None

        # End PyGame MIDI
        self._end()

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

        t_start = time.time()
        if message[0] == 0xf0:
            # Write SYSEX message asynchronous to MIDI output port
            self._midi_out.write_sys_ex(pygame.midi.time(), message)
        else:
            # Write MIDI message asynchronous to MIDI output port
            self._midi_out.write(message)

        # Wait until message transferred
        wait_time = len(message) * midi_util.MIDI_BYTE_TIME
        wait_time -= time.time() - t_start
        if wait_time > 0:
            time.sleep(wait_time)

        return True

    def receive_message(self):
        if not self.is_port_in_open():
            if self._verbose:
                print('MIDI output port not open')
            return

        # Asynchronous MIDI receive
        if self._midi_in.poll():
            # Read one 4 Bytes MIDI message
            message = self._midi_in.read(1)[0][0]

            if self._verbose:
                midi_util.print_message('RX', message)

            return message
