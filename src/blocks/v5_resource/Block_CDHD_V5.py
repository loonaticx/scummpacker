import struct
import xml.etree.ElementTree as et
import scummpacker_util as util
from blocks.v5_base import BlockDefaultV5

class BlockCDHDV5(BlockDefaultV5):
    name = "CDHD"
    xml_structure = (
        ("code", 'n', (
            ("x", 'i', 'x'),
            ("y", 'i', 'y'),
            ("width", 'i', 'width'),
            ("height", 'i', 'height'),
            ("flags", 'h', 'flags'),
            ("parent", 'i', 'parent'),
            ("walk_x", 'i', 'walk_x'),
            ("walk_y", 'i', 'walk_y'),
            ("actor_dir", 'i', 'actor_dir')
            )
        ),
    )

    def _read_data(self, resource, start, decrypt, room_start=0):
        """
          obj id    : 16le
          x         : 8
          y         : 8
          width     : 8
          height    : 8
          flags     : 8
          parent    : 8
          walk_x    : 16le signed
          walk_y    : 16le signed
          actor dir : 8 (direction the actor will look at when standing in front
                         of the object)
        """
        data = resource.read(13)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<H6B2hB", data)
        del data

        # Unpack the values
        self.obj_id, self.x, self.y, self.width, self.height, self.flags, \
            self.parent, self.walk_x, self.walk_y, self.actor_dir = values
        del values

    def load_from_file(self, path):
        self.name = "CDHD"
        self.size = 13 + 8 # data + header
        self._load_header_from_xml(path)

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        # Shared
        obj_id = util.xml2int(root.find("id").text)
        self.obj_id = obj_id

        self.read_xml_node(root)

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<H6B2hB", self.obj_id, self.x, self.y, self.width, self.height, self.flags,
            self.parent, self.walk_x, self.walk_y, self.actor_dir)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)

