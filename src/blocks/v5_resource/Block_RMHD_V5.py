import os
import struct
import xml.etree.ElementTree as et
import scummpacker_util as util
from blocks.v5_base import BlockDefaultV5

class BlockRMHDV5(BlockDefaultV5):
    name = "RMHD"
    xml_structure = (
        ("width", 'i', 'width'),
        ("height", 'i', 'height'),
        ("num_objects", 'i', 'num_objects')
    )

    def _read_data(self, resource, start, decrypt):
        """
        width 16le
        height 16le
        num_objects 16le
        """
        data = resource.read(6)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<3H", data)
        del data

        # Unpack the values
        self.width, self.height, self.num_objects = values
        del values

    def load_from_file(self, path):
        self.name = "RMHD"
        self.size = 6 + 8
        self._load_header_from_xml(path)

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        self.read_xml_node(root)

    def save_to_file(self, path):
        root = et.Element("room")

        self.generate_xml_node(root)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "RMHD.xml"))

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<3H", self.width, self.height, self.num_objects)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)
