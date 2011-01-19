
import os
import struct
import xml.etree.ElementTree as et
import scummpacker_util as util
from v5_base import BlockDefaultV5

class BlockMAXSV6(BlockDefaultV5):
    name = "MAXS"

    def _read_data(self, resource, start, decrypt, room_start=0):
        """
        Block Name	   (4 bytes)
        Block Size	   (4 bytes BE)
        Variables	   (2 bytes)
        Unknown	   (2 bytes)
        Bit Variables	   (2 bytes)
        Local Objects	   (2 bytes)
        Arrays		   (2 bytes)
        Unknown	   (2 bytes)
        Verbs		   (2 bytes)
        Floating Objects  (2 bytes)
        Inventory Objects (2 bytes)
        Rooms		   (2 bytes)
        Scripts	   (2 bytes)
        Sounds  	   (2 bytes)
        Character Sets	   (2 bytes)
        Costumes	   (2 bytes)
        Global Objects	   (2 bytes)
        """
        data = resource.read(30)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<15H", data)
        del data

        self.num_vars, self.unknown_1, self.bit_vars, self.local_objects, \
            self.num_arrays, self.unknown_2, self.verbs, self.floating_objects, \
            self.inventory_objects, self.rooms, self.scripts, self.sounds, \
            self.char_sets, self.costumes, self.global_objects = values

    def save_to_file(self, path):
        root = et.Element("maximums")

        et.SubElement(root, "variables").text = util.int2xml(self.num_vars)
        et.SubElement(root, "unknown_1").text = util.int2xml(self.unknown_1)
        et.SubElement(root, "bit_variables").text = util.int2xml(self.bit_vars)
        et.SubElement(root, "local_objects").text = util.int2xml(self.local_objects)
        et.SubElement(root, "arrays").text = util.int2xml(self.num_arrays)
        et.SubElement(root, "unknown_2").text = util.int2xml(self.unknown_2)
        et.SubElement(root, "verbs").text = util.int2xml(self.verbs)
        et.SubElement(root, "floating_objects").text = util.int2xml(self.floating_objects)
        et.SubElement(root, "inventory_objects").text = util.int2xml(self.inventory_objects)
        et.SubElement(root, "rooms").text = util.int2xml(self.rooms)
        et.SubElement(root, "scripts").text = util.int2xml(self.scripts)
        et.SubElement(root, "sounds").text = util.int2xml(self.sounds)
        et.SubElement(root, "character_sets").text = util.int2xml(self.char_sets)
        et.SubElement(root, "costumes").text = util.int2xml(self.costumes)
        et.SubElement(root, "global_objects").text = util.int2xml(self.global_objects)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "maxs.xml"))

    def load_from_file(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        self.size = 30 + self.block_name_length + 4

        self.num_vars = util.xml2int(root.find("variables").text)
        self.unknown_1 = util.xml2int(root.find("unknown_1").text)
        self.bit_vars = util.xml2int(root.find("bit_variables").text)
        self.local_objects = util.xml2int(root.find("local_objects").text)
        self.arrays = util.xml2int(root.find("arrays").text)
        self.unknown_2 = util.xml2int(root.find("unknown_2").text)
        self.verbs = util.xml2int(root.find("verbs").text)
        self.floating_objects = util.xml2int(root.find("floating_objects").text)
        self.inventory_objects = util.xml2int(root.find("inventory_objects").text)
        self.rooms = util.xml2int(root.find("rooms").text)
        self.scripts = util.xml2int(root.find("scripts").text)
        self.sounds = util.xml2int(root.find("sounds").text)
        self.char_sets = util.xml2int(root.find("character_sets").text)
        self.costumes = util.xml2int(root.find("costumes").text)
        self.global_objects = util.xml2int(root.find("global_objects").text)

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<15H", self.num_vars, self.unknown_1, self.bit_vars, self.local_objects,
            self.arrays, self.unknown_2, self.verbs, self.floating_objects, self.inventory_objects,
            self.rooms, self.scripts, self.sounds, self.char_sets, self.costumes, self.global_objects)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)