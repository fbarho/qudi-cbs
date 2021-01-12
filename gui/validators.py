# -*- coding: utf-8 -*-
"""
Created on Wed Jan  6 13:12:34 2021

@author: admin
"""


import os
import re
from qtpy import QtCore, QtGui
from qtpy import QtWidgets



class NameValidator(QtGui.QValidator):
    """
    This is a validator for strings that should be compatible with filenames.
    So no special characters (except '_') and blanks are allowed.
    If the flag path = True, / and \ are additionally allowed.
    """

    name_re = re.compile(r'([\w]+)')
    path_re = re.compile(r'([/\\:\w]+)')  # simple version : allow additionally to words \w / and \\. should be modified for finer control

    def __init__(self, *args, empty_allowed=False, path=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._empty_allowed = bool(empty_allowed)
        self._path = bool(path)  # flag that is used to select the path_re instead of name_re

    def validate(self, string, position):
        """
        This is the actual validator. It checks whether the current user input is a valid string
        every time the user types a character. There are 3 states that are possible.
        1) Invalid: The current input string is invalid. The user input will not accept the last
                    typed character.
        2) Acceptable: The user input in conform with the regular expression and will be accepted.
        3) Intermediate: The user input is not a valid string yet but on the right track. Use this
                         return value to allow the user to type fill-characters needed in order to
                         complete an expression.
        @param string: The current input string (from a QLineEdit for example)
        @param position: The current position of the text cursor
        @return: enum QValidator::State: the returned validator state,
                 str: the input string, int: the cursor position
        """
        # Return intermediate status when empty string is passed
        if not string:
            if self._empty_allowed:
                return self.Acceptable, '', position
            else:
                return self.Intermediate, string, position

        if self._path:  # flag for path validator
            match = self.path_re.match(string)
        else:
            match = self.name_re.match(string)
        if not match:
            return self.Invalid, '', position

        matched = match.group()
        if matched == string:
            return self.Acceptable, string, position

        return self.Invalid, matched, position

    def fixup(self, text):
        if self._path:
            match = self.path_re.search(text)
        else:
            match = self.name_re.search(text)
        if match:
            return match.group()
        return ''