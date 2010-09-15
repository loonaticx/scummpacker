import struct
import xml.etree.ElementTree as et
import scummpacker_util as util
from blocks.v5_base import BlockDefaultV5

class BlockIMHDV5(BlockDefaultV5):
    name = "IMHD"
    xml_structure = (
        ("image", 'n', (
            ("x", 'i', 'x'),
            ("y", 'i', 'y'),
            ("width", 'i', 'width'),
            ("height", 'i', 'height'),
            ("flags", 'h', 'flags'),
            ("unknown", 'h', 'unknown'),
            ("num_images", 'i', 'num_imnn'),
            ("num_zplanes", 'i', 'num_zpnn')
            )
        ),
    )

    def _read_data(self, resource, start, decrypt):
        """
        obj id       : 16le
        num imnn     : 16le
        num zpnn     : 16le (per IMnn block)
        flags        : 8
        unknown      : 8
        x            : 16le
        y            : 16le
        width        : 16le
        height       : 16le

        not sure about the following, I think it's only applicable for SCUMM V6+:
        num hotspots : 16le (usually one for each IMnn, but there is one even
                       if no IMnn is present)
        hotspots
          x          : 16le signed
          y          : 16le signed
        """

        data = resource.read(16)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<3H2B4H", data)
        del data

        # Unpack the values
        self.obj_id, self.num_imnn, self.num_zpnn, self.flags, self.unknown, \
            self.x, self.y, self.width, self.height = values
        del values

    def load_from_file(self, path):
        self.name = "IMHD"
        self.size = 16 + 8 # data + block header
        self._load_header_from_xml(path)

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        # Shared
        self.obj_id = util.xml2int(root.find("id").text)
        # Read image metadata using XML structure
        self.read_xml_node(root)

    def save_to_file(self, path):
        """ Combined OBHD.xml is saved in the ObjectBlockContainer."""
        return

    def _write_data(self, outfile, encrypt):
        data = struct.pack("<3H2B4H", self.obj_id, self.num_imnn, self.num_zpnn, self.flags, self.unknown,
            self.x, self.y, self.width, self.height)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)
