import xml.etree.ElementTree as et
import scummpacker_util as util
from blocks.v5_base import BlockDefaultV5


class BlockOBNAV5(BlockDefaultV5):
    name = "OBNA"

    def _read_data(self, resource, start, decrypt):
        data = resource.read(self.size - (resource.tell() - start))
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        self.obj_name = data[:-1] # remove null-terminating character

    def load_from_file(self, path):
        self.name = "OBNA"
        self._load_header_from_xml(path)
        self.size = len(self.obj_name) + 1 + 8

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        # Shared
        name = root.find("name").text
        if name == None:
            name = ''
        self.obj_name = util.unescape_invalid_chars(name)

    def _write_data(self, outfile, encrypt):
        # write object name + "\x00"
        data = self.obj_name + "\x00"
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)