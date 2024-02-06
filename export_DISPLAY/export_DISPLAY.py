#!/usr/bin/python3

import os

from curses.textpad import Textbox, rectangle
import curses
from curses import panel
import re
import subprocess


class display_selection(object):
    def __init__(self, stdscreen):
        self.DISPLAY_VAR_NAME = "DISPLAY"
        self.x11_DISPLAY_matcher = re.compile("X(\d+)")
        self.stdscreen = stdscreen
        self.stdscreen.getmaxyx()
        self._get_DISPLAYS()
        self.display_select_index = 0
        self._setup_ui()
        pass

    def _get_current_shell(self):
        shell_bin = os.environ['SHELL']
        return shell_bin

    def _get_DISPLAYS(self):
        x11_path = "/tmp/.X11-unix"
        display_target = os.listdir(x11_path)
        _display_target = []
        for display in display_target:
            matchRes = re.findall(self.x11_DISPLAY_matcher, display)
            if len(matchRes) != 1:
                continue
            matchRes = int(matchRes[0])
            _display_target.append(matchRes)
        display_target = _display_target
        del _display_target
        display_target.append("NULL")
        self.avaiable_display = display_target
        return display_target
        display_target = [item for item in display_target if os.path.isdir(
            os.path.join(x11_path, item))]
        return display_target

    def _get_current_DISPLAY(self):
        current_display = os.environ.get(self.DISPLAY_VAR_NAME)
        return current_display

    def _set_current_DISPLAY(self, display):
        if display == "NULL":
            display = ""
        else:
            display = ":%d" % (display)
        os.environ["self.DISPLAY_VAR_NAME"] = "%s" % (display)
        return

    def _setup_ui(self):
        self.info_window = self.stdscreen.subwin(5, 40, 0, 0)
        self.info_window.addstr(1, 1, "$DISPLAY SELECTER")

        self.select_window = self.stdscreen.subwin(10, 40, 6, 0)

        self.display()
        return

    def display(self):
        __updatedebug = 0
        while True:
            self.info_window.addstr(
                3, 1, "current ${DISPLAY}=%5s %d" % (self._get_current_DISPLAY(), __updatedebug))

            for idx, item in enumerate(self.avaiable_display):
                text = item
                if item != "NULL":
                    text = "X%d" % (item)

                text_style = curses.A_NORMAL
                if idx == self.display_select_index:
                    text_style = curses.A_REVERSE

                self.select_window.addstr(idx+1, 0, text, text_style)

            self.stdscreen.refresh()
            self.info_window.refresh()
            self.select_window.refresh()
            key = self.stdscreen.getch()

            if key == curses.KEY_UP:
                self.display_select_index = max(
                    0, self.display_select_index - 1)
            elif key == curses.KEY_DOWN:
                self.display_select_index = min(
                    len(self.avaiable_display) - 1, self.display_select_index + 1)
            elif key == ord('\n'):
                __selected_display = self.avaiable_display[self.display_select_index]
                self._set_current_DISPLAY(__selected_display)
                curses.endwin()
                os.environ['test'] = 'test'
                print("set $DISPLAY=\":%s\"" % (__selected_display.__str__()))
                subprocess.call(self._get_current_shell(),
                                env=os.environ, shell=True)
                stdscr = curses.initscr()
                stdscr.clear()
                pass

        self.stdscreen.clear()


if __name__ == "__main__":
    curses.wrapper(display_selection)
