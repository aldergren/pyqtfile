#!/usr/bin/env python


import os
import sys
import logging
import optparse

import qtfile
import qtatoms


USAGE = """Usage: %prog [options] <movie ...>

Dump atom tree (including fields and values) from QuickTime movies.
"""


def main(argv):
	parser = optparse.OptionParser(usage=USAGE)
	parser.add_option("-D", "--debug", action="store_true", help="Enable debugging output")
	parser.add_option("-T", "--types", default=None, help="Only show atoms of specific types")
	parser.add_option("-F", "--no-fields", dest="fields", action="store_false", default=True, help="Do not show atom fields and values")

	opts, args = parser.parse_args(argv)
	if opts.types:
		types = opts.types.split(",")
	else:
		types = []

	if opts.debug:
		logging.basicConfig(format="%(asctime)s | %(levelname)-8s | %(message)s", level=logging.DEBUG)
	else:
		logging.basicConfig(format="%(asctime)s | %(levelname)-8s | %(message)s", level=logging.INFO)


	def dump_atoms(atoms, level=0):
		indent = " "*4*level

		for atom in atoms:
			print indent + "%s" % (atom)
			if opts.fields:
				for key, value in atom.fields.items():
					if isinstance(value, str):
						print indent + " | %s='%s'" % (key, value)
					else:
						print indent + " | %s=%s" % (key, value)

			dump_atoms(atom, level+1)

	for qt_path in args[1:]:
		print "[%s]" % (qt_path)
		qt = qtfile.QuickTimeFile(qt_path, atom_modules=[qtatoms])

		if types:
			dump_atoms(qt.find(types))
		else:
			dump_atoms(qt)

	return 0




if __name__ == "__main__":
	sys.exit(main(sys.argv))