#!/usr/bin/python
# coding=UTF-8

import pyglet

from game import *
from fwk.ui.main_window import MainWindow

if __name__ == '__main__':
	window = MainWindow( )
	window.set_size(1024,600)
	pyglet.app.run( )
