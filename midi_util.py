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

MIDI_BAUDRATE = 31250  # Maximum MIDI UART transfer speed
MIDI_BYTES_PER_SEC = MIDI_BAUDRATE / 10  # 10 Bits per UART character
MIDI_BYTE_TIME = 1 / MIDI_BYTES_PER_SEC


def print_message(msg, data):
    line = '{} ({}): '.format(msg, len(data))
    for b in data:
        line += '{:02x} '.format(b)
    print(line)


def get_sysex_message(offset, data):
    tx_chunk = bytearray()

    sysex_data = False
    for i in range(offset, len(data)):
        b = data[i]
        if b == 0xf0:
            sysex_data = True
        if sysex_data:
            tx_chunk.append(b)
        if b == 0xf7:
            return i + 1, tx_chunk

    return None, None
