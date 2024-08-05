#!/usr/bin/env python3
#
# MIT License
#
# Copyright (c) 2023-2024 Erriez
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

import PySide6
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QTextEdit, QProgressBar, QPushButton, QGridLayout,\
    QLabel, QVBoxLayout, QFileDialog, QWidget, QComboBox, QHBoxLayout, QMessageBox, QSizePolicy, QGroupBox
from PySide6.QtCore import Qt, QSettings, QSize, QPoint, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QFont, QClipboard
from pathlib import Path
from tqdm import tqdm
import argparse
import os
import platform
import sys
import time
import webbrowser

from app_config import *
import messagebox
import midi_util

if USE_PYGAME and USE_RTMIDI:
    raise 'Error: Multiple MIDI backends configured'
elif USE_PYGAME:
    import midi_pygame as midi_backend
elif USE_RTMIDI:
    import midi_rtmidi as midi_backend
else:
    raise 'Error: No MIDI backend configured'

if sys.platform == 'linux':
    import distro

SYSEX_KN2000 = bytes([0xf0, 0x50, 0x21, 0x01, 0x18, 0x10, 0xf7])
SYSEX_KN2000_PNL = bytes([0xf0, 0x50, 0x2d, 0x01, 0x18, 0x10, 0x40])
SYSEX_KN2000_SND = bytes([0xf0, 0x50, 0x2d, 0x01, 0x18, 0x10, 0x30])
SYSEX_KN2000_CMP = bytes([0xf0, 0x50, 0x2d, 0x01, 0x18, 0x10, 0x50])
SYSEX_KN2000_SEQ = bytes([0xf0, 0x50, 0x2d, 0x01, 0x18, 0x10, 0x60])


# Find images with Nuitka build option "--include-data-dir=src=dst"
def resource_path(filename):
    # Get the absolute path of the directory containing the executable
    exe_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path to the dst file
    dst_path = os.path.join(exe_dir, filename)

    # Return the image path
    return dst_path


def get_app_version():
    app_version = 'Unknown'
    version_file = resource_path(r'data/version.txt')
    if version_file:
        try:
            with open(version_file, 'r') as f:
                app_version = f.readline()
        except OSError:
            pass
    return app_version.strip()


def bytes_to_str(num_bytes):
    if num_bytes < 1024:
        msg = '{} Bytes'.format(num_bytes)
    elif num_bytes < (1024 * 1024):
        msg = '{:0.1f} kB'.format(num_bytes / 1024.0)
    else:
        msg = '{:0.1f} MB'.format(num_bytes / (1024.0 * 1024.0))
    return msg


def print_midi_ports(verbose=False):
    midi = midi_backend.MIDI(verbose=verbose)
    # midi.print_available_ports()

    print('MIDI input ports:')
    for i, port_name in enumerate(midi.get_ports_in()):
        print('  {}: {}'.format(i, port_name))

    print('MIDI output ports:')
    for i, port_name in enumerate(midi.get_ports_out()):
        print('  {}: {}'.format(i, port_name))


def transmit_sysex_file(midi_port_id, sysex_file, verbose=False):
    try:
        # Open and read SYSEX file
        with open(sysex_file, 'rb') as f:
            sysex_data = f.read()
    except OSError as e:
        print(e)
        sys.exit(1)

    # Check SYSEX data
    if not sysex_data:
        print('No SYEX data found')
        sys.exit(1)
    if len(sysex_data) < 2 or sysex_data[0] != 0xf0 or sysex_data[-1] != 0xf7:
        print('Error: Invalid SYSEX data')
        sys.exit(1)

    # Create MIDI object
    midi = midi_backend.MIDI(verbose=verbose)
    if not midi.port_out_open(midi_port_id):
        sys.exit(1)

    # Print transmit info
    print('SYSEX transmit:')
    print('  File: {}'.format(os.path.basename(sysex_file)))
    print('  Size: {}'.format(bytes_to_str(len(sysex_data))))
    print('  Time: {:.03f}ms'.format(len(sysex_data) * midi_util.MIDI_BYTE_TIME))
    print('  MIDI: {}'.format(midi.get_port_out_name()))

    # Transmit SYSEX data
    t_begin = time.time()
    offset = 0
    for _ in tqdm(range(sysex_data.count(0xf0)), desc='SYSEX TX', unit='msg', mininterval=1.0, maxinterval=0.5):
        offset, sysex_chunk = midi_util.get_sysex_message(offset, sysex_data)
        if not sysex_chunk:
            break
        midi.send_message(sysex_chunk)

    # Close MIDI port
    midi.port_out_close()

    # Finish
    print('Done ({:.03f} ms)'.format(time.time() - t_begin))


def receive_sysex_file(midi_port_id, sysex_file, verbose=False):
    # Check if directory is writable
    sysex_file = os.path.abspath(sysex_file)
    if not os.access(os.path.dirname(sysex_file), os.W_OK):
        print('Error: File "{}" is not writable'.format(sysex_file))
        sys.exit(1)

    # Create MIDI object
    midi = midi_backend.MIDI(verbose=verbose)
    if not midi.port_in_open(midi_port_id):
        print('Error: Cannot open MIDI port')
        sys.exit(1)

    print('Receive SYSEX port "{}"...'.format(midi.get_port_in_name()))

    # Receive SYSEX data
    sysex_data = []
    rx_sysex_data = False
    t_begin = 0
    while True:
        sysex_chunk = midi.receive_message()
        if sysex_chunk:
            t_begin = time.time()

            if sysex_chunk[0] == 0xf0:
                # SYSEX begin
                rx_sysex_data = True

            if rx_sysex_data:
                # Copy SYSEX data until end of SYSEX
                for b in sysex_chunk:
                    sysex_data += bytes([b])
                    if b == 0xf7:
                        rx_sysex_data = False
                        sys.stdout.write('\rSYSEX RX: {}'.format(bytes_to_str(len(sysex_data))))
                        if verbose:
                            print()
                        break

        # Receive completed when not receiving data anymore
        if t_begin and (time.time() - t_begin) > MIDI_RX_COMPLETE_SEC:
            break

    # Save received SYSEX data to file
    print('\nSaving to "{}"...'.format(sysex_file))
    try:
        with open(sysex_file, 'wb') as f:
            f.write(bytearray(sysex_data))
    except OSError as e:
        print(e)
        sys.exit(1)

    # Close MIDI port
    midi.port_in_close()

    print('Done ({:.03f} ms)'.format(time.time() - t_begin))


class SysexTransmitThread(QThread):
    transmit_bytes = Signal(int)
    transmit_completed = Signal(bool)
    transmit_abort = False

    def __init__(self, midi, sysex_buffer):
        QThread.__init__(self)

        self.midi = midi
        self.sysex_buffer = sysex_buffer

    def run(self):
        tx_byte = 0
        while not self.transmit_abort:
            tx_chunk = bytearray()

            # Create SYSEX transmit chunk 0xf0 ... 0xf7
            for tx_byte in range(tx_byte, len(self.sysex_buffer)):
                b = self.sysex_buffer[tx_byte]
                tx_chunk.append(b)
                if b == 0xf7:
                    tx_byte += 1
                    break
            if not tx_chunk:
                # No more data
                break

            # Transmit SYSEX chunk is asynchronous
            self.midi.send_message(tx_chunk)

            # Update GUI with number of transmitted Bytes
            self.transmit_bytes.emit(tx_byte)

        # SYSEX transmit completed
        self.transmit_completed.emit(True)


class SysexTransmitWindow(QDialog):
    def __init__(self, midi, sysex_buffer, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.midi = midi
        self.sysex_buffer = sysex_buffer

        self.setFixedWidth(210)
        self.setFixedHeight(130)
        self.setWindowTitle('SYSEX Transmit')

        self.lbl_bytes_total = QLabel('Total: {}'.format(bytes_to_str(len(sysex_buffer))))
        self.lbl_bytes_sent = QLabel('Sent: ')

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)

        self.btn_cancel = QPushButton('Cancel')
        self.btn_cancel.setFixedWidth(75)
        self.btn_cancel.clicked.connect(self.on_btn_cancel)

        grid = QVBoxLayout()
        grid.addWidget(self.lbl_bytes_total)
        grid.addWidget(self.lbl_bytes_sent)
        grid.addWidget(self.progress)
        grid.addWidget(self.btn_cancel, alignment=Qt.AlignCenter)

        self.setLayout(grid)

        self.sysex_transmit_thread = SysexTransmitThread(midi=self.midi, sysex_buffer=sysex_buffer)
        self.sysex_transmit_thread.transmit_bytes.connect(self.on_update_progress)
        self.sysex_transmit_thread.transmit_completed.connect(self.on_transmit_completed)
        self.sysex_transmit_thread.start()

    def on_btn_cancel(self):
        self.sysex_transmit_thread.transmit_abort = True

    def on_transmit_completed(self):
        self.accept()

    def on_update_progress(self, bytes_sent):
        self.lbl_bytes_sent.setText('Sent: {}'.format(bytes_to_str(bytes_sent)))
        self.progress.setValue((bytes_sent / len(self.sysex_buffer)) * 100)


class SysexReceiveThread(QThread):
    receive_bytes = Signal(int)
    receive_completed = Signal(bool)
    receive_done = False

    def __init__(self, midi):
        QThread.__init__(self)

        self.midi = midi
        self.sysex_buffer = bytes()

    def run(self):
        rx_sysex_data = False

        while not self.receive_done:
            rx_data = self.midi.receive_message()
            if rx_data:
                if rx_data[0] == 0xf0:
                    rx_sysex_data = True

                if rx_sysex_data:
                    for b in rx_data:
                        self.sysex_buffer += bytes([b])
                        if b == 0xf7:
                            rx_sysex_data = False
                            self.receive_bytes.emit(len(self.sysex_buffer))
                            break

        self.receive_completed.emit(True)


class SysexReceiveWindow(QDialog):
    def __init__(self, midi, parent=None):
        super().__init__(parent)
        self.midi = midi
        self.parent = parent
        self.sysex_buffer = bytes()

        self.setFixedWidth(210)
        self.setFixedHeight(130)
        self.setWindowTitle('SYSEX Receive')

        self.bytes_received = QLabel('Bytes received: 0 Bytes')

        self.button_done = QPushButton('Done')
        self.button_done.setFixedWidth(75)
        self.button_done.clicked.connect(self.on_btn_done)

        grid = QVBoxLayout()
        grid.addWidget(self.bytes_received)
        grid.addWidget(self.button_done, alignment=Qt.AlignCenter)

        self.setLayout(grid)

        self.sysex_receive_thread = SysexReceiveThread(self.midi)
        self.sysex_receive_thread.receive_bytes.connect(self.on_update_progress)
        self.sysex_receive_thread.receive_completed.connect(self.on_completed)
        self.sysex_receive_thread.start()

    def closeEvent(self, event):
        self.sysex_receive_thread.receive_done = True
        event.ignore()

    def on_btn_done(self):
        self.sysex_receive_thread.receive_done = True

    def on_update_progress(self, bytes_received):
        self.bytes_received.setText('Bytes received: {}'.format(bytes_to_str(bytes_received)))

    def on_completed(self):
        self.sysex_buffer = bytes(self.sysex_receive_thread.sysex_buffer)
        self.accept()


class StatisticsMessageBox(QMessageBox):
    def __init__(self, parent=None):
        QMessageBox.__init__(self)

        # Store parent
        self.parent = parent

        # Enable size grip on lower right corner
        self.setSizeGripEnabled(True)

    def event(self, e):
        # Undocumented: The only way of resizing a QMessageBox is from an event
        result = QMessageBox.event(self, e)

        # Set min/max sizes QMessageBox
        self.setMinimumSize(275, 125)
        self.setMaximumSize(500, 500)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Show dialog on center of parent window
        if self.parent:
            geo = self.geometry()
            geo.moveCenter(self.parent.geometry().center())
            self.setGeometry(geo)

        # Return event
        return result


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(500, 400)
        self.setWindowTitle('About')

        python_version = 'v{}.{}.{}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2])

        txt_info = QTextEdit()

        font = txt_info.font()
        font.setFamily('')
        font.setFixedPitch(True)
        font.setKerning(0)
        font.setWeight(QFont.Normal)
        font.setPixelSize(14)
        font.setItalic(False)

        txt_info.setFont(font)
        txt_info.setReadOnly(True)

        txt_info.append('---')
        txt_info.append('App name:  {}'.format(APP_NAME))
        txt_info.append('Version:   {}'.format(get_app_version()))
        txt_info.append('Developer: {}'.format(APP_DEVELOPER))
        txt_info.append('Copyright: {}'.format(APP_YEAR))
        txt_info.append('License:   {}'.format(APP_LICENSE))
        txt_info.append('Source:    {}'.format(APP_WEBSITE))
        txt_info.append('Python:    {}'.format(python_version))
        txt_info.append('Pyside6:   {}'.format(PySide6.__version__))
        txt_info.append('Backend:   {} v{}'.format(parent.midi.get_backend_name(), parent.midi.get_backend_version()))
        txt_info.append('---')
        if sys.platform == 'linux':
            txt_info.append('System:   {}'.format(platform.system()))
            txt_info.append('Machine:  {}'.format(platform.machine()))
            txt_info.append('Version:  {}'.format(platform.version()))
            txt_info.append('Distro:   {}'.format(distro.name(pretty=True)))
            txt_info.append('Name:     {}'.format(distro.codename().capitalize()))
            txt_info.append('Desktop   {}'.format(os.environ.get('XDG_SESSION_TYPE').capitalize()))
        elif sys.platform == 'win32':
            txt_info.append('OS:       {}'.format('Windows'))
        txt_info.append('---')

        btn_ok = QPushButton('Ok')
        btn_ok.clicked.connect(self.accept)
        btn_ok.resize(btn_ok.sizeHint())

        # Add button to window
        layout = QVBoxLayout(self)
        layout.addWidget(txt_info)
        layout.addWidget(btn_ok)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self, sysex_file=None, sysex_transmit=False, verbose=False):
        super().__init__()

        # Create exit action with icon, shortcut, status tip and close window click event
        path = Path(__file__).resolve().parent

        # Load application settings
        self.settings = QSettings(APP_DEVELOPER, APP_NAME)

        # Variables
        self.verbose = verbose
        self.initialized = False
        self.sysex_data = None
        self.file_saved = False
        self.callback_sysex_file = sysex_file
        self.callback_sysex_transmit = sysex_transmit

        # Create MIDI object
        self.midi = midi_backend.MIDI(verbose=self.verbose)

        # Get / set window size
        self.resize(self.settings.value('mainwindow/size', QSize(600, 500)))
        # Get / set window position
        self.move(self.settings.value('mainwindow/position', QPoint(500, 500)))
        # Set minimum window size
        self.setMinimumSize(500, 200)
        # Set window title
        self.setWindowTitle('{} v{} by {}'.format(APP_NAME, get_app_version(), APP_DEVELOPER))
        # Set window icon
        self.setWindowIcon(QIcon(os.path.join(path, 'images', 'midi.png')))

        self.lbl_midi_in = QLabel('MIDI IN:')
        self.lbl_midi_out = QLabel('MIDI OUT:')
        self.cmb_midi_port_in = QComboBox(self)
        self.cmb_midi_port_out = QComboBox(self)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.addWidget(self.lbl_midi_in, 0, 0)
        grid.addWidget(self.cmb_midi_port_in, 0, 1)
        grid.addWidget(self.lbl_midi_out, 1, 0)
        grid.addWidget(self.cmb_midi_port_out, 1, 1)
        grid.setVerticalSpacing(10)

        port_box1 = QGroupBox()
        port_box1.setLayout(grid)
        port_box1.setFixedHeight(100)

        # self.lbl_info = QLabel('Info:')
        # self.lbl_info.setFixedHeight(15)
        # self.txt_info = QTextEdit()
        # self.txt_info.setReadOnly(True)
        # self.txt_info.setFixedHeight(100)

        # Create text edit and center on window
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setHidden(False if self.settings.value('view/log', 'true') == 'true' else True)

        vbox = QVBoxLayout()
        vbox.addWidget(port_box1)
        # vbox.addWidget(self.lbl_info)
        # vbox.addWidget(self.txt_info)
        vbox.addWidget(self.txt_log)

        widget = QWidget(self)
        widget.setLayout(vbox)
        self.setCentralWidget(widget)

        # Create menubar
        menubar = self.menuBar()

        # Add File menu
        self.file_new_action = QAction(QIcon(os.path.join(path, 'images', 'new.png')), '&New', self)
        self.file_new_action.setShortcut('Ctrl+N')
        self.file_new_action.triggered.connect(self.file_new)

        self.file_open_action = QAction(QIcon(os.path.join(path, 'images', 'open.png')), '&Open', self)
        self.file_open_action.setShortcut('Ctrl+O')
        self.file_open_action.setStatusTip('Open SYSEX file')
        self.file_open_action.triggered.connect(self.file_open)

        self.file_save_action = QAction(QIcon(os.path.join(path, 'images', 'save.png')), '&Save', self)
        self.file_save_action.setShortcut('Ctrl+S')
        self.file_save_action.setStatusTip('Save SYSEX to file')
        self.file_save_action.setEnabled(False)
        self.file_save_action.triggered.connect(self.file_save)

        self.file_exit_action = QAction(QIcon(os.path.join(path, 'images', 'exit.png')), '&Exit', self)
        self.file_exit_action.setShortcut('Ctrl+Q')
        self.file_exit_action.setStatusTip('Exit application')
        self.file_exit_action.triggered.connect(self.close)

        menu_file = menubar.addMenu('&File')
        menu_file.addAction(self.file_new_action)
        menu_file.addAction(self.file_open_action)
        menu_file.addAction(self.file_save_action)
        menu_file.addSeparator()
        menu_file.addAction(self.file_exit_action)

        # Add Edit menu
        self.copy_action = QAction('&Copy', self)
        self.copy_action.setShortcut('Ctrl+C')
        self.copy_action.setEnabled(False)
        self.copy_action.triggered.connect(self.edit_copy)
        # self.paste_action = QAction('&Paste', self)
        # self.paste_action.setShortcut('Ctrl+V')
        self.select_all_action = QAction('&Select all', self)
        self.select_all_action.setShortcut('Ctrl+A')
        self.select_all_action.setEnabled(False)
        self.select_all_action.triggered.connect(self.edit_select_all)

        menu_edit = menubar.addMenu('&Edit')
        menu_edit.addAction(self.copy_action)
        # menu_edit.addAction(paste_action)
        menu_edit.addSeparator()
        menu_edit.addAction(self.select_all_action)

        # Add MIDI menu
        self.transmit_sysex_action = QAction(QIcon(os.path.join(path, 'images', 'sysex_transmit.png')),
                                             '&Transmit SYSEX', self)
        self.transmit_sysex_action.setShortcut('Ctrl+T')
        self.transmit_sysex_action.setStatusTip('Transmit SYSEX to device')
        self.transmit_sysex_action.setEnabled(False)
        self.transmit_sysex_action.triggered.connect(self.midi_transmit_sysex)
        self.receive_sysex_action = QAction(QIcon(os.path.join(path, 'images', 'sysex_receive.png')),
                                            '&Receive SYSEX', self)
        self.receive_sysex_action.setShortcut('Ctrl+R')
        self.receive_sysex_action.setStatusTip('Receive SYSEX from device')
        self.receive_sysex_action.triggered.connect(self.midi_receive_sysex)
        self.midi_refresh_action = QAction(QIcon(os.path.join(path, 'images', 'midi.png')), '&Refresh ports', self)
        self.midi_refresh_action.setShortcut('F5')
        self.midi_refresh_action.setStatusTip('Refresh MIDI ports')
        self.midi_refresh_action.triggered.connect(self.midi_refresh_ports)

        menu_midi = menubar.addMenu('&MIDI')
        menu_midi.addAction(self.receive_sysex_action)
        menu_midi.addAction(self.transmit_sysex_action)
        menu_midi.addSeparator()
        menu_midi.addAction(self.midi_refresh_action)

        # Add View menu
        self.view_log_action = QAction('&Show log', self)
        self.view_log_action.setCheckable(True)
        self.view_log_action.setChecked(True if self.settings.value('view/log', 'true') == 'true' else False)
        self.view_log_action.triggered.connect(self.view_log_change)

        self.view_statistics_action = QAction('&Statistics', self)
        self.view_statistics_action.setShortcut('Ctrl+I')
        self.view_statistics_action.setStatusTip('View statistics')
        self.view_statistics_action.triggered.connect(self.view_statistics)

        menu_view = menubar.addMenu('&View')
        menu_view.addAction(self.view_log_action)
        menu_view.addAction(self.view_statistics_action)

        # Add Help menu
        self.help_action = QAction(QIcon(os.path.join(path, 'images', 'web.png')), '&Help', self)
        self.help_action.setShortcut('F1')
        self.help_action.setStatusTip('Open developers website on Github')
        self.help_action.triggered.connect(self.help_website)

        self.about_action = QAction(QIcon(os.path.join(path, 'images', 'about.png')), '&About', self)
        self.about_action.setShortcut('Ctrl+?')
        self.about_action.setStatusTip('About application')
        self.about_action.triggered.connect(self.help_about)

        menu_help = menubar.addMenu('&Help')
        menu_help.addAction(self.help_action)
        menu_help.addSeparator()
        menu_help.addAction(self.about_action)

        # Create toolbar
        toolbar = self.addToolBar('Toolbar')
        toolbar.addAction(self.file_new_action)
        toolbar.addAction(self.file_open_action)
        toolbar.addAction(self.file_save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.receive_sysex_action)
        toolbar.addAction(self.transmit_sysex_action)
        toolbar.addSeparator()
        toolbar.addAction(self.file_exit_action)

        # Create statusbar
        self.statusBar()

        # Refresh MIDI ports
        self.midi_refresh_ports()

        # Set selected MIDI port
        for i in range(0, self.cmb_midi_port_in.count()):
            if self.cmb_midi_port_in.itemText(i).endswith(self.settings.value('midi/port-in', '')):
                self.cmb_midi_port_in.setCurrentIndex(i)
                break

        for i in range(0, self.cmb_midi_port_out.count()):
            if self.cmb_midi_port_out.itemText(i).endswith(self.settings.value('midi/port-out', '')):
                self.cmb_midi_port_out.setCurrentIndex(i)
                break

    def __del__(self):
        pass

    def enterEvent(self, _):
        if not self.initialized:
            self.initialized = True

            # Open SYSEX file
            if self.callback_sysex_file:
                self.file_open(load_sysex_file=self.callback_sysex_file,
                               sysex_transmit=self.callback_sysex_transmit)

    def settings_save(self):
        # Window settings
        self.settings.beginGroup("mainwindow")
        self.settings.setValue("size", self.size())
        self.settings.setValue("position", self.pos())
        self.settings.endGroup()

        # MIDI settings
        self.settings.beginGroup("midi")
        self.settings.setValue("port-in", self.cmb_midi_port_in.currentText())
        self.settings.setValue("port-out", self.cmb_midi_port_out.currentText())
        self.settings.endGroup()

        # View
        self.settings.setValue('view/log', self.view_log_action.isChecked())

    def closeEvent(self, _):
        self.settings_save()

    def file_new(self):
        if self.sysex_data and not self.file_saved:
            msgbox = messagebox.MessageBoxQuestion(self,
                                                   message='Do you want to save changes?',
                                                   buttons=QMessageBox.StandardButton.Yes |
                                                           QMessageBox.StandardButton.No |
                                                           QMessageBox.StandardButton.Cancel)
            if msgbox.answer == QMessageBox.StandardButton.Yes:
                if not self.file_save():
                    self.statusBar().showMessage('File save aborted')
                    return
            elif msgbox.answer == QMessageBox.StandardButton.Cancel:
                return

        self.sysex_data = None
        self.file_save_action.setEnabled(False)
        self.copy_action.setEnabled(False)
        self.select_all_action.setEnabled(False)
        self.transmit_sysex_action.setEnabled(False)
        self.txt_log.clear()
        self.file_saved = False

    def file_open(self, load_sysex_file=None, sysex_transmit=False):
        if load_sysex_file:
            path = load_sysex_file
        else:
            path = self.settings.value('history/path', str(Path.home()))
            if not os.path.exists(path):
                path = str(Path.home())
            path, _ = QFileDialog.getOpenFileName(self, 'Open file', path, 'SYSEX Files (*.syx)')

        # Make absolute path
        path = os.path.abspath(path)

        # Check path
        if not path:
            self.statusBar().showMessage('No file selected'.format())
        elif not os.path.exists(path):
            self.statusBar().showMessage('File {} not found'.format(path))
        else:
            self.settings.setValue('history/path', os.path.dirname(path))
            try:
                # Read file
                with open(path, 'rb') as f:
                    self.sysex_data = f.read()
                    if not self.sysex_data or not len(self.sysex_data) > 2:
                        messagebox.MessageBoxError(self, message='Error: Invalid SYSEX file')
                        return
                    if not self.sysex_data[0] == 0xf0 or not self.sysex_data[-1] == 0xf7:
                        messagebox.MessageBoxError(self, message='Error: Invalid SYSEX data')
                        return
            except OSError as err:
                self.statusBar().showMessage(err)
                return

            # Activate buttons
            self.file_save_action.setEnabled(True)
            self.copy_action.setEnabled(True)
            self.select_all_action.setEnabled(True)
            self.transmit_sysex_action.setEnabled(True)
            self.statusBar().showMessage('File "{}" opened'.format(os.path.basename(path)))
            self.file_saved = True

            # Add SYSEX data to textbox
            self.midi_print_sysex()

            # Ask for confirmation
            if not load_sysex_file or not sysex_transmit:
                msgbox = messagebox.MessageBoxQuestion(self, message='Transmit SYSEX?')
                if msgbox.answer == QMessageBox.StandardButton.Yes:
                    sysex_transmit = True
                else:
                    self.statusBar().showMessage('SYSEX transmit aborted')

            if sysex_transmit:
                # Transmit SYSEX
                self.midi_transmit_sysex()
                self.statusBar().showMessage('SYSEX transmit completed')

    def file_save(self):
        path = self.settings.value('history/path', str(Path.home()))
        if not os.path.exists(path):
            path = str(Path.home())
        path, _ = QFileDialog.getSaveFileName(self, 'Save file', path, 'SYSEX Files (*.syx)')

        if not path:
            self.statusBar().showMessage('No file selected'.format())
            return False
        elif not os.access(os.path.dirname(path), os.W_OK):
            self.statusBar().showMessage('Directory {} not writable'.format(path))
            return False
        else:
            self.settings.setValue('history/path', os.path.dirname(path))

            if not path.endswith('.syx'):
                path += '.syx'

            try:
                with open(path, 'wb') as f:
                    f.write(self.sysex_data)
            except OSError as err:
                self.statusBar().showMessage(err)
                return False

            self.file_saved = True
            self.statusBar().showMessage('File "{}" saved'.format(os.path.basename(path)))

        return True

    def edit_copy(self):
        clipboard = QClipboard()
        clipboard.setText(self.txt_log.textCursor().selectedText())

    def edit_select_all(self):
        self.txt_log.selectAll()

    def midi_refresh_ports(self):
        selected_port_in_name = self.cmb_midi_port_in.currentText()
        selected_port_out_name = self.cmb_midi_port_out.currentText()

        self.cmb_midi_port_in.clear()
        self.cmb_midi_port_in.addItem('Disconnect')
        for port_name in self.midi.get_ports_in():
            self.cmb_midi_port_in.addItem('{}'.format(port_name))

        self.cmb_midi_port_out.clear()
        self.cmb_midi_port_out.addItem('Disconnect')
        for port_name in self.midi.get_ports_out():
            self.cmb_midi_port_out.addItem('{}'.format(port_name))

        index = self.cmb_midi_port_in.findText(selected_port_in_name, Qt.MatchEndsWith)
        if index < 0:
            index = 0
        self.cmb_midi_port_in.setCurrentIndex(index)

        index = self.cmb_midi_port_out.findText(selected_port_out_name, Qt.MatchEndsWith)
        if index < 0:
            index = 0
        self.cmb_midi_port_out.setCurrentIndex(index)

    def midi_transmit_sysex(self):
        # Open MIDI output port
        if not self.midi.port_out_open(port_id=self.cmb_midi_port_out.currentIndex()-1):
            messagebox.MessageBoxError(self, message='Cannot open MIDI output port.')
            return

        # Show SYSEX transmit dialog box
        dialog = SysexTransmitWindow(midi=self.midi, sysex_buffer=self.sysex_data, parent=self)

        # Wait until True (Ok / accepted) or False (Cancel / rejected) clicked
        if dialog.exec():
            self.statusBar().showMessage('SYSEX transmit completed')

        # Close MIDI port
        self.midi.port_out_close()

    def midi_receive_sysex(self):
        # Open MIDI input port
        if not self.midi.port_in_open(port_id=self.cmb_midi_port_in.currentIndex()-1):
            messagebox.MessageBoxError(self, message='Cannot open MIDI input port.')
            return

        # Create custom model dialog
        dialog = SysexReceiveWindow(midi=self.midi, parent=self)

        # Wait until True (Ok / accepted) or False (Cancel / rejected) clicked
        if dialog.exec():
            # Get received SYSEX data
            self.sysex_data = dialog.sysex_buffer

            # Add received SYSEX data to log
            self.midi_print_sysex()

            if self.sysex_data:
                self.file_save_action.setEnabled(True)
                self.copy_action.setEnabled(True)
                self.select_all_action.setEnabled(True)
                self.transmit_sysex_action.setEnabled(True)
                self.statusBar().showMessage('SYSEX receive completed')

        # Close MIDI port
        self.midi.port_in_close()

    def midi_print_sysex(self):
        self.txt_log.clear()

        if not self.sysex_data:
            return

        byte_color = '<span style="color:#0000ff;">{:02x}</span>'
        byte_normal = '{:02x}'

        line = ''
        for b in self.sysex_data:
            if line:
                line += ' '

            if b == 0xf0 or b == 0xf7:
                line += byte_color.format(b)
            else:
                line += byte_normal.format(b)

            if b == 0xf7:
                self.txt_log.append(line)
                line = ''

        if line:
            self.txt_log.append(line)

    def view_log_change(self):
        if self.view_log_action.isChecked():
            self.txt_log.setHidden(False)
            self.setMinimumSize(500, 300)
            self.resize(600, 400)
        else:
            self.txt_log.setHidden(True)
            self.setMinimumSize(500, 200)
            self.resize(0, 0)

    def view_statistics(self):
        if not self.sysex_data or not len(self.sysex_data):
            message = 'No SYSEX data loaded.\n'
        else:
            message = 'SYSEX data: {}.\n'.format(bytes_to_str(len(self.sysex_data)))
            if SYSEX_KN2000 in self.sysex_data:
                message += 'Technics KN2000:\n'
                if SYSEX_KN2000_PNL in self.sysex_data:
                    message += ' - Panel memory\n'
                if SYSEX_KN2000_SND in self.sysex_data:
                    message += ' - Sound memory\n'
                if SYSEX_KN2000_CMP in self.sysex_data:
                    message += ' - Composer\n'
                if SYSEX_KN2000_SEQ in self.sysex_data:
                    message += ' - Sequencer\n'
            else:
                message += 'Unknown\n'

        # Create resizable messagebox and show centered on window
        messagebox.MessageBoxInfo(self, title='Statistics', message=message)

    @staticmethod
    def help_website():
        webbrowser.open(APP_WEBSITE)

    def help_about(self):
        dialog = AboutDialog(self)
        dialog.exec()


def main():
    print('{} v{} by {} (c) {}'.format(APP_NAME, get_app_version(), APP_DEVELOPER, APP_YEAR))

    # Argument parser
    parser = argparse.ArgumentParser()

    parser.add_argument('-o', '--open', help='Open SYSEX file in GUI')
    parser.add_argument('-t', '--transmit', help='Transmit SYSEX commandline')
    parser.add_argument('-r', '--receive', help='Receive SYSEX commandline')
    parser.add_argument('-p', '--port-id', help='MIDI port ID for --transmit or --receive', type=int)
    parser.add_argument('-l', '--list-midi-ports', help='Print MIDI ports commandline', action="store_true")
    parser.add_argument('-v', '--verbose', help='Print verbose commandline', action="store_true")

    args = parser.parse_args()

    if (args.transmit or args.receive) and args.port_id is None:
        print('Error: Missing argument -p or --port-id')
        sys.exit(1)

    if args.verbose:
        midi = midi_backend.MIDI()
        print('Using {} MIDI v{}'.format(midi.get_backend_name(), midi.get_backend_version()))

    if args.list_midi_ports:
        # Print MIDI ports commandline
        print_midi_ports(args.verbose)
    elif args.transmit:
        # Transmit SYSEX file commandline
        transmit_sysex_file(midi_port_id=args.port_id, sysex_file=args.transmit, verbose=args.verbose)
    elif args.receive:
        # Receive SYSEX and write to file commandline
        receive_sysex_file(midi_port_id=args.port_id, sysex_file=args.receive, verbose=args.verbose)
    else:
        # Start GUI
        app = QApplication(sys.argv)
        main_window = MainWindow(sysex_file=args.open,
                                 sysex_transmit=args.transmit,
                                 verbose=args.verbose)
        main_window.show()
        sys.exit(app.exec())


if __name__ == '__main__':
    main()
