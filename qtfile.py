#!/usr/bin/env python


import logging
import struct


LOG = logging.getLogger("qtfile")


class QuickTimeReader:

	def __init__(self):
		self.type_handlers = [ContainerAtom]

	def read(self, stream, size):
		return Atom.from_stream(stream, stream.tell(), size, None, self.type_handlers)


class Atom:

	header = ">L4s"
	header_extsize = ">Q"
	supported_types = []
	container = False
	field_defs = []

	# Set to True to allow a trailing null at the end of the atom (used by some containers).
	trailing_null = False

	def __init__(self, size=0, kind=""):
		self.size = size
		self.kind = kind
		self.parent = None
		self.source = None
		# Note that source_offset specifies the start of data, excluding the header.
		self.source_offset = 0
		self.source_header_size = 0
		self.fields = {}
		self.children = []
		self.extended_header = False

	def __repr__(self):
		return "<%s %s %sb>" % (self.__class__.__name__, self.kind, self.size)


	@classmethod
	def from_stream(cls, stream, start=None, end=0, parent=None, type_handlers=None):
		"""
		Read one or more atoms from a stream.

		If start is set, seek to this position in the stream before reading starts.

		If end is set to 0, read continously until a parse error is encountered.
		If end is set to -1, stop reading after one atom.
		"""

		if not type_handlers:
			type_handlers = []

		if start != None and (stream.tell() != start):
			stream.seek(start)

		while end <= 0 or stream.tell() < end:

			atom = None
			offset = stream.tell()

			try:
				size, kind, extended_header = Atom.read_header(stream)

				LOG.debug("@%d: Found header for %s", offset, kind)

				for handler in type_handlers:
					if handler.supports_type(kind):
						atom = handler(size, kind)
						break

				if not atom:
					LOG.debug("@%d: No type handler for %s" % (stream.tell(), kind))
					atom = cls(size, kind)

				atom.source_header_size = stream.tell() - offset
				atom.parent = parent
				atom.extended_header = extended_header
				atom.source = stream
				atom.source_offset = offset

				atom.read_data(stream, offset + size)

				if atom.container:
					atom.read_children(stream, offset + size, type_handlers)

			except QuickTimeParseError, e:
				LOG.warning("@%d: %s" % (stream.tell(), e))
				LOG.warning("@%d: Stopped reading stream after parsing error" % (stream.tell()))
				break

			yield atom

			if end == -1:
				break

			if stream.tell() != (offset + atom.size):
				LOG.debug("@%d: Atom %s did not completely parse, seeking ahead to %d" % (stream.tell(), kind, offset + atom.size))
				stream.seek(offset + atom.size)

			if parent and parent.trailing_null and (end - stream.tell() == 4):
				LOG.debug("@%d: Trailing null inside container %s" % (stream.tell(), parent))
				stream.read(4)


	@classmethod
	def read_header(self, stream):
		"""Read an atom header from a stream. Returns (size, kind)."""
		size, kind = read_struct(stream, self.header)
		extended_header = False

		if not kind:
			raise QuickTimeParseError("Atom with null type", stream.tell())

		if size == 1:
			LOG.debug("@%d: Reading extended size field for %s" % (stream.tell(), kind))
			size = read_struct(stream, self.header_extsize)
			extended_header = True

		elif size == 0:
			# TODO: If the size field is set to 0, this is the last atom and extends until eof.
			raise QuickTimeParseError("Atoms of size 0 is unsupported")

		return size, kind, extended_header


	@classmethod
	def supports_type(cls, kind):
		"""Returns True if this class can handle the given atom type."""
		return kind in cls.supported_types

	def read_data(self, stream, end):
		"""Parse atom data."""
		for key, format in self.field_defs:
			self.fields[key] = read_struct(stream, format)

	def read_children(self, stream, end, type_handlers):
		self.children = Atom.from_stream(stream, stream.tell(), end, self, type_handlers)

	def write(self, stream, recursive=True):
		"""Write the atom to the stream. If recursive is set to False, containers
		will not output their children."""
		self.write_header(stream)
		self.write_data(stream, recursive)

	def write_header(self, stream):
		"""Write an atom header to the stream."""
		if self.extended_header or self.size > 2**32:
			LOG.debug("@%d: Writing extended size header for %s" % (stream.tell(), self.kind))
			stream.write(struct.pack(self.header, 1, self.kind))
			stream.write(struct.pack(self.header_extsize, self.size))
		else:
			LOG.debug("@%d: Writing basic header for %s" % (stream.tell(), self.kind))
			stream.write(struct.pack(self.header, self.size, self.kind))

	def write_data(self, stream, recursive=True):
		"""Write the atom data to the stream. As the basic Atom class does not
		understand the content of atoms, it simply passes through the data if no
		fields are defined."""
		# FIXME: We should check that we've written enough data.
		if self.field_defs:
			LOG.debug("@%d: Serializing data for %s" % (stream.tell(), self.kind))
			for key, format in self.field_defs:
				stream.write(struct.pack(format, self.fields[key]))
		else:
			LOG.debug("@%d: Passing through data for %s" % (stream.tell(), self.kind))
			self.source.seek(self.source_offset + self.source_header_size)
			stream.write(self.source.read(self.size - self.source_header_size))


class ContainerAtom(Atom):

	container = True

	supported_types = [
	    'aaid', 'akid', '\xa9alb', 'apid', 'aART', '\xa9ART', 'atid', 'clip',
	    '\xa9cmt', '\xa9com', 'covr', 'cpil', 'cprt', '\xa9day', 'dinf', 'disk',
	    'edts', 'geid', 'gnre', '\xa9grp', 'hinf', 'hnti', 'ilst', 'matt',
	    'mdia', 'minf', 'moof', 'moov', '\xa9nam', 'pinf', 'plid', 'rtng',
	    'schi', 'sinf', 'stbl', 'stik', 'tmpo', '\xa9too', 'traf', 'trak', 'trkn',
	    'udta', '\xa9wrt',
	]

	# FIXME: This should probably recalculate the size before writing the header. It's
	# the sum of the serialized size of the fields plus size of each containing atom.

	def write_data(self, stream, recursive=True):
		for key, format in self.field_defs:
			stream.write(struct.pack(format, self.fields[key]))

		if recursive:
			for child in self.children:
				LOG.debug("@%d: Writing child %s" % (stream.tell(), child))
				child.write(stream)
			if self.trailing_null:
				LOG.debug("@%d: Writing trailing null after %s" % (stream.tell(), self))
				stream.write('\x00'*4)


def read_struct(stream, format, unwrap=True):
	"""Read and unpack structured data from a stream. Raises QuickTimeParseError
	if there's not enough data or it has an incorrect format. If unwrap is set,
	tuples with a single value will be unwrapped before returning."""
	need_bytes = struct.calcsize(format)
	buf = stream.read(need_bytes)
	if len(buf) != need_bytes:
		raise QuickTimeParseError("Expected %d bytes, got %d" % (need_bytes, len(buf)), stream.tell())
	try:
		result = struct.unpack(format, buf)
		if len(result) == 1:
			return result[0]
		return result
	except struct.error:
		raise QuickTimeParseError("Could not unpack data", stream.tell())


class QuickTimeParseError(Exception):
	"""Raised if an error is encountered during parsing of a Quicktime movie."""
	def __init__(self, message, offset = 0):
		Exception.__init__(self, message)
		self.message = message
		self.offset = offset

	def __str__(self):
		return "@%d: %s" % (self.offset, self.message)



