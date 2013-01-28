"""
PyQTFile
========

This module provides classes for useful atom types encountered in the wild, and 
serves as an example of how to write custom type classes.
"""


import struct
from qtfile import Atom, read_struct, QuickTimeParseError


class ContainerAtom(Atom):

	supported_types = ["aaid", "akid", "\xa9alb", "apid", "aART", "\xa9ART", "atid", "clip",
	    			   "\xa9cmt", "\xa9com", "covr", "cpil", "cprt", "\xa9day", "dinf", "disk",
	    			   "edts", "geid", "gnre", "\xa9grp", "hinf", "hnti", "matt",
	    			   "mdia", "minf", "moof", "moov", "\xa9nam", "pinf", "plid", "rtng",
	    			   "schi", "sinf", "stbl", "stik", "tmpo", "\xa9too", "traf", "trak", "trkn",
	    			   "\xa9wrt",
					  ]

	container = True

	def write_data(self, stream, recursive=True):
		super(ContainerAtom, self).write_data(stream, recursive)
		if recursive:
			for child in self:
				child.write(stream)


class FileTypeAtom(Atom):

	supported_types = ["ftyp"]
	field_defs = [("major_brand", ">4s"),
			  	  ("minor_brand", ">I"),
			  	 ]

	def read_data(self, stream, end=None):
		"""Parse atom data."""
		super(FileTypeAtom, self).read_data(stream, end)

		self.fields["compatible_brands"] = []

		while stream.tell() < end:
			self.fields["compatible_brands"].append(read_struct(stream, ">4s"))

	@property
	def size(self):
		return super(FileTypeAtom, self).size + struct.calcsize(">4s") * len(self.fields["compatible_brands"])

	def write_data(self, stream, recursive):
		super(FileTypeAtom, self).write_data(stream, recursive)

		for v in self.fields["compatible_brands"]:
			stream.write(struct.pack(">4s", v))


class SampleDescriptionsAtom(ContainerAtom):

	supported_types = ["stsd"]

	field_defs = [("version", ">c"),
	              ("flags", ">3s"),
	              ("num_descriptions", ">I"),
	             ]


class VideoDescriptionAtom(ContainerAtom):

	supported_types = ["apcn", 
					   "apch", 
					   "ap4h"]

	trailing_null = True

	field_defs = [("reserved", ">6s"),
				  ("index", ">H"),
				  ("version", ">H"),
				  ("revision", ">H"),
				  ("vendor", ">4s"),
				  ("temporal_quality", ">I"),
				  ("spatial_quality", ">I"),
				  ("width", ">H"),
				  ("height", ">H"),
				  ("horizontal_res", ">I"),
				  ("vertical_res", ">I"),
				  ("zero_data_size", ">I"),
				  ("frame_count", ">H",),
				  # NOTE: Apple specs says this is a Pascal string, but we've
				  # seen NULs mid-string in here and we'd like to preserve it all.
				  ("compressor", ">32s"),
				  ("depth", ">h"),
				  ("color_table", ">h"),
				 ]

	# FIXME: If color_table is 0, we'll need to read that before getting the children.


class TimecodeSampleDescription(ContainerAtom):

	supported_types = ["tmcd"]
	trailing_null = True

	field_defs = [("_reserved", ">6s"),
				   ("index", ">H"),
				   ("reserved2", ">I"),
				   ("flags", ">I"),
				   ("timescale", ">I"),
				   ("duration", ">I"),
				   ("fps", ">b"),
				   # ???: Docs says this should be a 24-bit field.
				   ("reserved3", ">1s"),
				  ]


class UserDataAtom(ContainerAtom):

	supported_types = ["udta"]
	trailing_null = True


class SampleToChunkAtom(Atom):

	supported_types = ["stsc"]
	table_row_format = ">III"

	field_defs = [("version", ">c"),
	              ("flags", ">3s"),
	              ("num_table_entries", ">I"),
				 ]

	def read_data(self, stream, end = None):
		"""Parse atom data."""
		super(SampleToChunkAtom, self).read_data(stream, end)
		self.fields["table"] = []
		while stream.tell() < end:
			self.fields["table"].append(read_struct(stream, self.table_row_format))

	def write_data(self, stream, recursive):
		super(SampleToChunkAtom, self).write_data(stream, recursive)
		for v in self.fields["table"]:
			stream.write(struct.pack(self.table_row_format, *v))

	@property
	def size(self):
		return super(SampleToChunkAtom, self).size + struct.calcsize(self.table_row_format) * len(self.fields["table"])


class ChunkOffsetAtom(Atom):


	# FIXME: Make this support the 64-bit variant ('co64') too.
	
	supported_types = ["stco"]
	table_row_format = ">I"

	field_defs = [("version", ">c"),
	              ("flags", ">3s"),
	              ("num_table_entries", ">I"),
				 ]

	def read_data(self, stream, end = None):
		"""Parse atom data."""
		super(ChunkOffsetAtom, self).read_data(stream, end)
		self.fields["table"] = []
		while stream.tell() < end:
			self.fields["table"].append(read_struct(stream, self.table_row_format))

	def write_data(self, stream, recursive):
		super(ChunkOffsetAtom, self).write_data(stream, recursive)
		for v in self.fields["table"]:
			stream.write(struct.pack(">I", v))

	@property
	def size(self):
		return super(ChunkOffsetAtom, self).size + struct.calcsize(self.table_row_format) * len(self.fields["table"])


class ColorParametersAtom(Atom):
	"""
	https://developer.apple.com/quicktime/icefloe/dispatch019.html#extensions
	"""

	supported_types = ["colr"]

	field_defs = [("parameter_type", ">4s"),
	 			  ("primaries", ">H"),
	 			  ("transfer_func", ">H"),
	 			  ("matrix", ">H"),
	 			 ]


class MetadataHandlerAtom(Atom):

	supported_types = ["hdlr"]
	reserved_format = ">4s"
	reserved_count = 3

	field_defs = [("version", ">c"),
				  ("flags", ">3s"),
				  ("predefined", ">I"),
				  ("handler_type", ">4s")]

	def read_data(self, stream, end = None):
		"""Parse atom data."""
		super(MetadataHandlerAtom, self).read_data(stream, end)
		self.fields["reserved"] = []
		for _ in range(self.reserved_count):
			self.fields["reserved"].append(read_struct(stream, self.reserved_format))
		self.fields["name"] = stream.read(end - stream.tell())

	def write_data(self, stream, recursive):
		super(MetadataHandlerAtom, self).write_data(stream, recursive)
		for v in self.fields["reserved"]:
			stream.write(struct.pack(self.reserved_format, v))
		stream.write(self.fields["name"])

	@property
	def size(self):
		return super(MetadataHandlerAtom, self).size + len(self.fields["name"]) + struct.calcsize(self.reserved_format) * self.reserved_count


class MetadataAtom(ContainerAtom):

	supported_types = ["meta"]


class MetadataKeysAtom(Atom):

	supported_types = ["keys"]
	key_header_format = ">I4s"

	field_defs = [("version", ">c"),
				  ("flags", ">3s"),
				  ("entry_count", ">I")]

	def read_data(self, stream, end = None):
		"""Parse atom data."""
		super(MetadataKeysAtom, self).read_data(stream, end)
		self.fields["keys"] = []

		for _ in range(self.fields["entry_count"]):
			size, namespace = read_struct(stream, self.key_header_format)
			value = stream.read(size - struct.calcsize(self.key_header_format))
			if size != len(value) + struct.calcsize(self.key_header_format):
				raise QuickTimeParseError("Size mismatch [%s->%s] in key structure" % (size, len(value)), stream.tell())

			self.fields["keys"].append((namespace, value))

	def write_data(self, stream, recursive):
		super(MetadataKeysAtom, self).write_data(stream, recursive)
		for v in self.fields["keys"]:
			namespace, value = v
			size = struct.calcsize(self.key_header_format) + len(value)
			stream.write(struct.pack(self.key_header_format, size, namespace))
			stream.write(value)

	@property
	def size(self):
		return super(MetadataKeysAtom, self).size + \
			sum([struct.calcsize(self.key_header_format) + len(v[1]) for v in self.fields["keys"]])


class MetadataItemAtom(ContainerAtom):

	# These atoms resuse the type field to indicate their index in the parent list.
	# Therefore, this class repsponds to all types and should never be part of module-level
	# registration.

	explicit_registration = True

	def __repr__(self):
		return "<%s index=%d>" % (self.__class__.__name__, struct.unpack(">I", self.kind)[0])

	@classmethod
	def supports_type(cls, kind):
		return True


class MetadataItemListAtom(ContainerAtom):
	"""
	https://developer.apple.com/library/mac/#documentation/QuickTime/qtff/Metadata/Metadata.html#//apple_ref/doc/uid/TP40000939-CH1-SW1
	"""

	# All children in this container are metadata items.

	supported_types = ["ilst"]
	force_child_class = MetadataItemAtom


class DataAtom(Atom):

	supported_types = ["data"]

	field_defs = [("type", ">I"),
	              ("locale", ">I")]

	type_handlers = {1: (lambda d: unicode(d, 'utf8'),
						 lambda d: d,
						 None),
					 2: (lambda d: unicode(d, 'utf16'),
					   	 lambda d: d,
					   	 None),
					 21: (lambda d: struct.unpack(">i", d)[0],
					      lambda d: struct.pack(">i", d),
					   	  4),
					 22: (lambda d: struct.unpack(">I", d)[0],
					   	  lambda d: struct.pack(">i", d),
					   	  4),
					 23: (lambda d: struct.unpack(">f", d)[0],
					  	  lambda d: struct.pack(">f", d),
					  	  4),
					 24: (lambda d: struct.unpack(">d", d)[0],
					  	  lambda d: struct.pack(">d", d),
					  	  4)}

	def read_data(self, stream, end=None):
		super(DataAtom, self).read_data(stream, end)
		data = stream.read(end - stream.tell())
		decoder, _, _ = self.type_handlers.get(self.fields["type"], (None, None, None))
		if decoder:
			self.fields["value"] = decoder(data)
		else:
			self.fields["value"] = data

	def write_data(self, stream, recursive):
		super(DataAtom, self).write_data(stream, recursive)
		data = self.fields["value"]
		_, encoder, _ = self.type_handlers.get(self.fields["type"], (None, None, None))
		if encoder:
			stream.write(encoder(data))
		else:
			stream.write(data)

	@property
	def size(self):
		_, _, size = self.type_handlers.get(self.fields["type"], (None, None, None))
		if size:
			return super(DataAtom, self).size + size
		else:
			return super(DataAtom, self).size + len(self.fields["value"])

