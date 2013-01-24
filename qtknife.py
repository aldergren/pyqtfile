#!/usr/bin/env python


import sys
import logging
import optparse
import os

import qtfile
import qtatoms


USAGE = """Usage: %prog [options] <input_movie> <output_movie>

Modify atoms and fields in a QuickTime movie. Multiple atoms and fields
can be specified separated by commas. Field modifications should be specified
in the format key:converter:value, for example:

	$ qtknife.py -M colr -F matrix:int:2 input.mov output.mov
"""



def main(argv):
	parser = optparse.OptionParser(usage=USAGE)
	parser.add_option("-D", "--debug", action="store_true", help="Enable debugging output")
	parser.add_option("-M", "--modify-types", default=None, help="Modify specific atom types")
	parser.add_option("-F", "--fields", default=None, help="Modify atom field values")
	parser.add_option("-S", "--strip-types", default=None, help="Strip specific atom types")

	opts, args = parser.parse_args(argv)
	if opts.modify_types:
		modify_types = opts.modify_types.split(",")
	else:
		modify_types = []

	if opts.fields:
		fields = opts.fields.split(",")
	else:
		fields = []

	if opts.strip_types:
		strip_types = opts.strip_types.split(",")
	else:
		strip_types = []

	converters = {"str": str,
				  "int": int}

	if len(args) == 3:
		source, dest = args[1:]
	else:
		parser.error("missing mandatory arguments (need source and destination path)")

	if opts.debug:
		logging.basicConfig(format="%(asctime)s | %(message)s", level=logging.DEBUG)
	else:
		logging.basicConfig(format="%(asctime)s | %(message)s", level=logging.INFO)

	qt = qtfile.QuickTimeFile(source, atom_modules=[qtatoms])
	target = open(dest, 'wb', 0)

	for kind in strip_types:
		for atom in qt.find(kind):
			print "%s -> [free]" % (atom)
			atom.free()

	for kind in modify_types:
		for atom in qt.find(kind):
			print atom
			for key, converter, value in [f.split(":") for f in fields]:
				if atom.has_key(key):
					previous_value = atom[key]
					atom[key] = converters.get(converter, str)(value)
					print "| %s=%s -> %s" % (key, previous_value, value)
				else:
					print "| %s (no such field)" % (key)

	qt.write(target)
	return 0

if __name__ == "__main__":
	sys.exit(main(sys.argv))