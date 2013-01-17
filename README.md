PyQTFile
========

A Python library for reading, modifying and writing Quicktime files.

Usage
-----

	>> from qtfile import QuickTimeReader
	>> reader = QuickTimeReader()
	>> for atom in reader.open('movie.mov'):
	>>		print atom
