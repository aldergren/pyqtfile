PyQTFile
========

A Python library for reading, modfying and writing QuickTime movies.

A QuickTime movie consists of a list of atoms. An atom can contain other
atoms, allowing for complex data structures.

All atoms have a type, and the structure of atom data is specific to each type.
By registering additional atom classes, this data can then be deserialized, modified 
and serialized as needed.

When reading an existing movie and no atom class is found for a type, the 
PassthroughAtom class is used. This lazily passes through the source data,
which allows manipulation of a movie with only partial understanding of the
atoms it contains.

Usage
-----

	>>> import qtfile
	>>> import qtatoms
	>>> for atom in qtfile.QuickTimeFile('miryumyum.mov', atom_modules=[qtatoms]):
	>>>		print atom, atom.fields

Advanced Usage
--------------

Find any color parameters in a movie, and modify the field values:

	for colr in qt.find("colr"):
		colr["primaries"] = 2
		colr["transfer_func"] = 2
		colr["matrix"] = 2

Find the compressor used for each video track:

	# Find all the handler descriptions, looking for video.
	for hdlr in qt.find("hdlr"):
		if hdlr["handler_type"] == "vide":
			# Step up one level in the tree, find the sample description.
			for stsd in hdlr.parent.find("stsd"):
				# Print the compressor for the first video sample description.
				print stsd[0]["compressor"]


Find the chunk offsets for timecode track, and print the first timecode sample:

	# Find all the handler descriptions, looking for timecode.
	for hdlr in qt.find("hdlr"):
		if hdlr["handler_type"] == "tmcd":
			# Step up one level in the tree, find the chunk offsets.
			for stco in hdlr.parent.find("stco"):
				# Seek to the first offset. We assume "stream" here is
				# the open file object.
				stream.seek(stco["table"][0])
				# Unpack and print the frame number.
				print struct.unpack(">I", stream.read(4))


