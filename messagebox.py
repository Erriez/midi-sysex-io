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

from PySide6.QtWidgets import QMessageBox, QSizePolicy
from app_config import *


class ResizableMessageBox(QMessageBox):
    def __init__(self, parent=None, title='', message='', icon=None, buttons=QMessageBox.StandardButton.Ok):
        QMessageBox.__init__(self)

        self.parent = parent

        self.setWindowTitle(title)
        self.setText(message)
        self.setIcon(icon)
        self.setStandardButtons(buttons)
        self.setSizeGripEnabled(True)

    def event(self, e):
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


class MessageBoxInfo(ResizableMessageBox):
    def __init__(self, parent=None, title=APP_NAME, message=''):
        ResizableMessageBox.__init__(self, parent=parent, title=title, message=message,
                                     icon=QMessageBox.Icon.Information)
        ResizableMessageBox.exec(self)


class MessageBoxError(ResizableMessageBox):
    def __init__(self, parent=None, title=APP_NAME, message=''):
        ResizableMessageBox.__init__(self, parent=parent, title=title, message=message, icon=QMessageBox.Icon.Critical)
        ResizableMessageBox.exec(self)


class MessageBoxQuestion(ResizableMessageBox):
    def __init__(self, parent=None,
                 title=APP_NAME,
                 message='',
                 buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No):
        ResizableMessageBox.__init__(self, parent=parent, title=title, message=message, icon=QMessageBox.Icon.Question,
                                     buttons=buttons)
        self._answer = ResizableMessageBox.exec(self)

    @property
    def answer(self):
        return self._answer
