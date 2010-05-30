import os
import struct
import xml.etree.ElementTree as et
import scummpacker_control as control
import scummpacker_util as util
from common import *
from v5_base import *

class BlockRNAMV5(BlockDefaultV5):
    name_length = 9
    name = "RNAM"

    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        self.room_names = []
        while resource.tell() < end:
            room_no = util.str_to_int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            if room_no == 0: # end of list marked by 0x00
                break
            room_name = resource.read(self.name_length)
            if decrypt:
                room_name = util.crypt(room_name, self.crypt_value)
            room_name = util.crypt(room_name, 0xFF).rstrip("\x00")
            self.room_names.append((room_no, room_name))
            control.global_index_map.map_index(self.name, room_no, room_name)

    def save_to_file(self, path):
        root = et.Element("room_names")

        for room_no, room_name in self.room_names:
            room = et.SubElement(root, "room")
            et.SubElement(room, "id").text = util.output_int_to_xml(room_no)
            et.SubElement(room, "name").text = util.escape_invalid_chars(room_name)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "roomnames.xml"))

    def load_from_file(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        self.room_names = []
        for room in root.findall("room"):
            room_no = util.parse_int_from_xml(room.find("id").text)
            room_name = room.find("name").text
            if room_name == None:
                room_name = ''
            room_name = util.unescape_invalid_chars(room_name)
            self.room_names.append((room_no, room_name))
            control.global_index_map.map_index(self.name, room_no, room_name)

    def save_to_resource(self, resource, room_start=0):
        self.size = 10 * len(self.room_names) + 1 + self.block_name_length + 4
        self._write_header(resource, True)
        for room_no, room_name in self.room_names:
            resource.write(util.int_to_str(room_no, 1, crypt_val=self.crypt_value))
            # pad/truncate room name to 8 characters
            room_name = (room_name + ("\x00" * (self.name_length - len(room_name)))
                if len(room_name) < self.name_length
                else room_name[:self.name_length])
            resource.write(util.crypt(room_name, self.crypt_value ^ 0xFF))
        resource.write(util.int_to_str(0, 1, crypt_val=self.crypt_value))

class BlockMAXSV5(BlockDefaultV5):
    name = "MAXS"

    def _read_data(self, resource, start, decrypt):
        """
        Block Name         (4 bytes)
        Block Size         (4 bytes BE)
        Variables          (2 bytes)
        Unknown            (2 bytes)
        Bit Variables      (2 bytes)
        Local Objects      (2 bytes)
        New Names?         (2 bytes)
        Character Sets     (2 bytes)
        Verbs?             (2 bytes)
        Array?             (2 bytes)
        Inventory Objects  (2 bytes)
        """
        data = resource.read(18)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<9H", data)
        del data

        self.num_vars, self.unknown_1, self.bit_vars, self.local_objects, \
            self.unknown_2, self.char_sets, self.unknown_3, self.unknown_4, \
            self.inventory_objects = values

    def save_to_file(self, path):
        root = et.Element("maximums")

        et.SubElement(root, "variables").text = util.output_int_to_xml(self.num_vars)
        et.SubElement(root, "unknown_1").text = util.output_int_to_xml(self.unknown_1)
        et.SubElement(root, "bit_variables").text = util.output_int_to_xml(self.bit_vars)
        et.SubElement(root, "local_objects").text = util.output_int_to_xml(self.local_objects)
        et.SubElement(root, "unknown_2").text = util.output_int_to_xml(self.unknown_2)
        et.SubElement(root, "character_sets").text = util.output_int_to_xml(self.char_sets)
        et.SubElement(root, "unknown_3").text = util.output_int_to_xml(self.unknown_3)
        et.SubElement(root, "unknown_4").text = util.output_int_to_xml(self.unknown_4)
        et.SubElement(root, "inventory_objects").text = util.output_int_to_xml(self.inventory_objects)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "maxs.xml"))

    def load_from_file(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        self.size = 18 + self.block_name_length + 4

        self.num_vars = util.parse_int_from_xml(root.find("variables").text)
        self.unknown_1 = util.parse_int_from_xml(root.find("unknown_1").text)
        self.bit_vars = util.parse_int_from_xml(root.find("bit_variables").text)
        self.local_objects = util.parse_int_from_xml(root.find("local_objects").text)
        self.unknown_2 = util.parse_int_from_xml(root.find("unknown_2").text)
        self.char_sets = util.parse_int_from_xml(root.find("character_sets").text)
        self.unknown_3 = util.parse_int_from_xml(root.find("unknown_3").text)
        self.unknown_4 = util.parse_int_from_xml(root.find("unknown_4").text)
        self.inventory_objects = util.parse_int_from_xml(root.find("inventory_objects").text)

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<9H", self.num_vars, self.unknown_1, self.bit_vars, self.local_objects,
            self.unknown_2, self.char_sets, self.unknown_3, self.unknown_4,
            self.inventory_objects)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)

class BlockDOBJV5(BlockDefaultV5):
    name = "DOBJ"

    def _read_data(self, resource, start, decrypt):
        num_items = util.str_to_int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        self.objects = []
        # Write all owner+state values
        for _ in xrange(num_items):
            owner_and_state = util.str_to_int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            owner = (owner_and_state & 0xF0) >> 4
            state = owner_and_state & 0x0F
            self.objects.append([owner, state])
        # Write all class data values
        for i in xrange(num_items):
            class_data = util.str_to_int(resource.read(4), crypt_val=(self.crypt_value if decrypt else None))
            self.objects[i].append(class_data)

    def load_from_file(self, path):
        tree = et.parse(path)

        self.objects = []
        for obj_node in tree.getiterator("object-entry"):
            obj_id = int(obj_node.find("id").text)
            if obj_id != obj_id == len(self.objects) + 1:
                raise util.ScummPackerException("Entries in object ID XML must be in sorted order with no gaps in ID numbering.")
            owner = util.parse_int_from_xml(obj_node.find("owner").text)
            state = util.parse_int_from_xml(obj_node.find("state").text)
            class_data = util.parse_int_from_xml(obj_node.find("class-data").text)
            self.objects.append([owner, state, class_data])

    def save_to_file(self, path):
        root = et.Element("object-directory")

        for i in xrange(len(self.objects)):
            owner, state, class_data = self.objects[i]
            obj_node = et.SubElement(root, "object-entry")
            et.SubElement(obj_node, "id").text = util.output_int_to_xml(i + 1)
            et.SubElement(obj_node, "owner").text = util.output_int_to_xml(owner)
            et.SubElement(obj_node, "state").text = util.output_int_to_xml(state)
            et.SubElement(obj_node, "class-data").text = util.output_hex_to_xml(class_data)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "dobj.xml"))

    def save_to_resource(self, resource, room_start=0):
        """ TODO: allow filling of unspecified values (e.g. if entries for
        86 and 88 exist but not 87, create a dummy entry for 87."""
        num_items = len(self.objects)

        self.size = 5 * num_items + 2 + self.block_name_length + 4
        self._write_header(resource, True)

        resource.write(util.int_to_str(num_items, 2, crypt_val=self.crypt_value))
        for owner, state, _ in self.objects:
            combined_val = ((owner & 0x0F) << 4) | (state & 0x0F)
            resource.write(util.int_to_str(combined_val, 1, crypt_val=self.crypt_value))
        for _, _, class_data in self.objects:
            resource.write(util.int_to_str(class_data, 4, crypt_val=self.crypt_value))

class BlockDROOV5(BlockDefaultV5):
    """DROO indexes don't seem to be used in V5.

    Each game seems to have a different padding length."""
    name = "DROO"
    DEFAULT_PADDING_LENGTHS = {
        "MI1CD" : 100,
        "MI2" : 127,
        "FOA" : 99
    }

    def __init__(self, *args, **kwds):
        # default padding length is 127 for now
        self.padding_length = kwds.get('padding_length',
                                       self.DEFAULT_PADDING_LENGTHS[control.global_args.game])
        super(BlockDROOV5, self).__init__(*args, **kwds)

    """Directory of offsets to ROOM blocks."""
    def save_to_file(self, path):
        """This block is generated when saving to a resource."""
        return

    def save_to_resource(self, resource, room_start=0):
        """DROO blocks do not seem to be used in V5 games."""
#        room_num = control.global_index_map.get_index("LFLF", room_start)
#        room_offset = control.global_index_map.get_index("ROOM", room_num)
        self.size = 5 * self.padding_length + 2 + self.block_name_length + 4
        self._write_header(resource, True)
        resource.write(util.int_to_str(self.padding_length, 2, crypt_val=self.crypt_value))
        for _ in xrange(self.padding_length):
            resource.write(util.int_to_str(0, 1, crypt_val=self.crypt_value))
        for _ in xrange(self.padding_length):
            resource.write(util.int_to_str(0, 4, crypt_val=self.crypt_value))
