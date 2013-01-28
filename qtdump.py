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
	parser.add_option("-M", "--metadata", action="store_true", default=False, help="Show related metadata key and value atoms")

	opts, args = parser.parse_args(argv)
	if opts.types:
		types = opts.types.split(",")
	else:
		types = []

	if opts.debug:
		logging.basicConfig(format="%(asctime)s | %(levelname)-8s | %(message)s", level=logging.DEBUG)
	else:
		logging.basicConfig(format="%(asctime)s | %(levelname)-8s | %(message)s", level=logging.INFO)


	def dump_metadata(atoms):
		indent = " "*4

		for meta in qt.find("meta"):
			keys = meta.find("keys")[0]
			values = meta.find("ilst")[0]

			print meta.parent
			print indent + str(meta)

			for n, item in enumerate(keys['keys']):
				namespace, key = item
				data = values[n].find('data')[0]
				print "%s%s:%s=%s" % (indent * 2, namespace, key, data["value"])

	def dump_atoms(atoms, level=0):
		indent = " "*4*level

		for atom in atoms:
			print indent + "%s" % (atom)
			if opts.fields:
				for key, value in atom.fields.items():
					if isinstance(value, str) or isinstance(value, unicode):
						print indent + " | %s='%s'" % (key, value)
					else:
						print indent + " | %s=%s" % (key, value)

			dump_atoms(atom, level+1)

	for qt_path in args[1:]:
		print "[%s]" % (qt_path)
		qt = qtfile.QuickTimeFile(qt_path, atom_modules=[qtatoms])

		if opts.metadata:
			dump_metadata(qt)
		else:
			if types:
				dump_atoms(qt.find(types))
			else:
				dump_atoms(qt)

	return 0




if __name__ == "__main__":
	sys.exit(main(sys.argv))