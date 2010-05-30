#! /usr/bin/python
from __future__ import with_statement
import logging
import os
import struct
import xml.etree.ElementTree as et
import scummpacker_control as control
import scummpacker_util as util
from common import *
from v4_base import *

class BlockFOV4(BlockDefaultV4):
    name = "FO"

    def _read_data(self, resource, start, decrypt):
        num_rooms = util.str_to_int(resource.read(1),
                                    crypt_val=(self.crypt_value if decrypt else None))

        for _ in xrange(num_rooms):
            room_no = util.str_to_int(resource.read(1),
                                      crypt_val=(self.crypt_value if decrypt else None))
            lf_offset = util.str_to_int(resource.read(4),
                                      crypt_val=(self.crypt_value if decrypt else None))

            control.global_index_map.map_index("LF", lf_offset, room_no)
            control.global_index_map.map_index("RO", lf_offset + self.block_name_length + 4, lf_offset) # HACK
        print control.global_index_map.items("LF")

    def save_to_file(self, path):
        """Don't need to save offsets since they're calculated when packing."""
        return

    def save_to_resource(self, resource, room_start=0):
        """This method should only be called after write_dummy_block has been invoked,
        otherwise this block may have no size attribute initialised."""
        # Write name/size (probably again, since write_dummy_block also writes it)
        self._write_header(resource, True)
        # Write number of rooms, followed by offset table
        # Possible inconsistency, in that this uses the global index map for ROOM blocks,
        #  whereas the "write_dummy_block" just looks at the number passed in, which
        #  comes from the number of entries in the file system.
        room_table = sorted(control.global_index_map.items("RO"))
        num_of_rooms = len(room_table)
        resource.write(util.int_to_str(num_of_rooms, 1, util.LE, self.crypt_value))
        for room_num, room_offset in room_table:
            room_num = int(room_num)
            resource.write(util.int_to_str(room_num, 1, util.LE, self.crypt_value))
            resource.write(util.int_to_str(room_offset, 4, util.LE, self.crypt_value))

    def write_dummy_block(self, resource, num_rooms):
        """This method should be called before save_to_resource. It just
        reserves space until the real block is written.

        The reason for doing this is that the block begins at the start of the
        resource file, but contains the offsets of all of the room blocks, which
        won't be known until after they've all been written."""
        block_start = resource.tell()
        self._write_dummy_header(resource, True)
        resource.write(util.int_to_str(num_rooms, 1, util.BE, self.crypt_value))
        for _ in xrange(num_rooms):
            resource.write("\x00" * 5)
        block_end = resource.tell()
        self.size = block_end - block_start

class BlockLFV4(BlockLucasartsFile, BlockContainerV4, BlockGloballyIndexedV4):
    is_unknown = False
    
    def _read_data(self, resource, start, decrypt):
        """LF blocks store the room number before any child blocks.

        Also, first LF file seems to store (junk?) data after the last child block, at least
        for LOOM CD and Monkey Island 1."""
        logging.debug("Reading children from container block...")
        # NOTE: although we read index in here, it gets overridden in load_from_resource.
        self.index = util.str_to_int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        super(BlockLFV4, self)._read_data(resource, start, decrypt)

class BlockLSV4(BlockLocalScript, BlockDefaultV4):
    name = "LS"

class BlockOCV4(BlockDefaultV4):
    name = "OC"
    xml_structure = (
        ("code", 'n', (
            ("x", 'i', 'x'),
            ("y", 'i', 'y'),
            ("width", 'i', 'width'),
            ("height", 'i', 'height'),
            ("unknown", 'h', 'unknown'),
            ("parent_state", 'h', 'parent_state'),
            ("parent", 'h', 'parent'),
            ("walk_x", 'i', 'walk_x'),
            ("walk_y", 'i', 'walk_y'),
            )
        ),
    )

    def _read_data(self, resource, start, decrypt):
        """
          obj id    : 16le
          unknown   : 8
          x         : 8
          y, parent state : 8 (parent state is the high bit, y is ANDed 0x7F)
          width     : 8
          parent    : 8
          walk_x    : 16le signed
          walk_y    : 16le signed
          height and actor_dir : 8 (actor_dir is ANDed 0x07, height ANDed 0xF8)
          name_offset : 8 (offset from start of the block)
          verb table : variable
          obj_name  : variable, null-terminated
        """
        data = resource.read(13)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<H5B2h2B", data)
        del data

        # Unpack the values
        self.obj_id, self.unknown, self.x, y_and_parent_state, self.width, \
        self.parent, self.walk_x, self.walk_y, height_and_actor_dir, name_offset = values
        del values

        self.parent_state = y_and_parent_state & 0x80
        self.y = y_and_parent_state & 0x7F
        self.height = height_and_actor_dir & 0xF8
        self.actor_dir = height_and_actor_dir & 0x07

        # Read the event table
        event_table_size = (start + name_offset) - resource.tell()
        #logging.debug("event table size: %s, thing1: %s, resource tell: %s" % (event_table_size, (start + name_offset), resource.tell()))
        data = self._read_raw_data(resource, event_table_size - 1, decrypt)
        self.event_table = data

        # Read object name (null-terminated string)
        #resource.seek(name_offset, os.SEEK_SET)
        self.obj_name = ''
        while True:
            c = resource.read(1)
            if decrypt:
                c = util.crypt(c, self.crypt_value)
            if c == "\x00":
                break
            self.obj_name += c

        # Read the script data (raw)
        #logging.debug("self size: %s, thing1: %s, thing2: %s, resource tell: %s" % (self.size, (resource.tell() - start), self.size - (resource.tell() - start), resource.tell()))
        data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)
        self.script_data = data

    def load_from_file(self, path):
        self._load_header_from_xml(os.path.join(path, "OBHD.xml"))
        self._load_script_from_file(os.path.join(path, "OC.dmp"))
        self.size = self._calculate_size()

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        # Shared
        self.obj_id = util.parse_int_from_xml(root.find("id").text)
        self.obj_name = root.find("name").text

        XMLHelper().read(self, root, self.xml_structure)

    def _load_script_from_file(self, path):
        with file(path, 'rb') as script_file:
            # Skip the header info, except name offset
            script_file.seek(6 + 12)
            name_offset = script_file.read(1)
            # read event table
            event_table_size = (start + name_offset) - resource.tell()
            data = resource.self._read_raw_data(script_file, event_table_size, False)
            self.event_table = data
            # skip the object name
            script_file.seek(len(self.obj_name) + 1, os.SEEK_CUR)
            # read script data
            start_script = script_file.tell()
            start_script.seek(0, os.SEEK_END)
            end_script = script_file.tell()
            script_size = end_script - start_script
            data = resource.self._read_raw_data(script_file, script_size, False)
            self.script_data = data

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        # TODO: validate values fit into clamped?
        y_and_parent_state = (self.parent_state & 0x80) | (self.y & 0x7F)
        height_and_actor_dir = (self.height & 0xF8) | (self.actor_dir & 0x07)

        name_offset = 6 + 13 + len(self.event_table)

        # Object header
        data = struct.pack("<H5B2h2B", self.obj_id, self.unknown, self.x, y_and_parent_state, self.width,
            self.parent, self.walk_x, self.walk_y, height_and_actor_dir, name_offset)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)

        # Event table
        self._write_raw_data(outfile, self.event_table, encrypt)

        # Object name
        data = self.obj_name + "\x00"
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)

        # Script data
        self._write_raw_data(outfile, self.script_data, encrypt)

    def _calculate_size(self):
        # block header + header data + verb table + object name + null-terminator + script size
        return 6 + 13 + len(self.event_table) + len(self.obj_name) + 1 + len(self.script_data)

    def generate_xml_node(self, parent_node):
        XMLHelper().write(self, parent_node, self.xml_structure)

class BlockOIV4(BlockDefaultV4):
    """ Reads object ID but otherwise acts as generic block."""
    name = "OI"
    xml_structure = tuple()

    def _read_data(self, resource, start, decrypt):
        data = resource.read(2)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        self.obj_id = struct.unpack("<H", data)[0]
        self.data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)

    def load_from_file(self, path):
        self._load_header_from_xml(os.path.join(path, "OBHD.xml"))
        self._load_data_from_file(os.path.join(path, "OI.dmp"))
        self.size = self._calculate_size()

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        # Shared
        self.obj_id = util.parse_int_from_xml(root.find("id").text)

    def _load_data_from_file(self, path):
        with file(path, 'rb') as data_file:
            # Skip the header info
            data_file.seek(6 + 2)
            # read script data
            start_data = data_file.tell()
            start_data.seek(0, os.SEEK_END)
            end_data = data_file.tell()
            data_size = end_data - start_data
            data = resource.self._read_raw_data(data_file, data_size, False)
            self.data = data

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        # Object header
        data = struct.pack("<H", self.obj_id)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)
        # Image data
        self._write_raw_data(outfile, self.data, encrypt)

    def _calculate_size(self):
        # block header + header data + data size
        return 6 + 1 + len(self.data)

    def generate_xml_node(self, parent_node):
        XMLHelper().write(self, parent_node, self.xml_structure)

class BlockROV4(BlockRoom, BlockContainerV4): # also globally indexed
    def _init_class_data(self):
        self.name = "RO"
        self.lf_name = "LF"
        self.script_types = frozenset(["EN",
                                  "EX",
                                  "LS"])
        self.object_types = frozenset(["OI",
                                  "OC"])
        self.object_image_type = "OI"
        self.object_code_type = "OC"
        self.num_scripts_type = "NL"
        self.script_container_class = ScriptBlockContainerV4
        self.object_container_class = ObjectBlockContainerV4

class BlockSOV4(BlockContainerV4, BlockGloballyIndexedV4):
    def generate_file_name(self):
        name = (self.name
                + "_"
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3))
        return name
    
    
#--------------------
# Meta or container blocks.
class ObjectBlockContainerV4(ObjectBlockContainer):
    def _init_class_data(self):
        self.obcd_name = "OC"
        self.obim_name = "OI"
        self.obcd_class = BlockOCV4
        self.obim_class = BlockOIV4

class ScriptBlockContainerV4(ScriptBlockContainer):
    local_scripts_name = "LS"
    entry_script_name = "EN"
    exit_script_name = "EX"
    lf_name = "LF"
    num_local_name = "NL"