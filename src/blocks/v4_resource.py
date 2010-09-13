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

class BlockFOV4(BlockRoomOffsets, BlockDefaultV4):
    name = "FO"
    LFLF_NAME = "LF"
    ROOM_NAME = "RO"
    OFFSET_POINTS_TO_ROOM = False

class BlockLEV4(BlockLucasartsEntertainmentContainer, BlockContainerV4):
    def _init_class_data(self):
        self.name = "LE"
        self.OFFSET_CLASS = BlockFOV4
        
class BlockLFV4(BlockLucasartsFile, BlockContainerV4, BlockGloballyIndexedV4):
    is_unknown = False
    
    def _read_data(self, resource, start, decrypt):
        """LF blocks store the room number before any child blocks.

        Also, first LF file seems to sometimes store (junk?) data after the last child block, at least
        for LOOM CD and Monkey Island 1."""
        logging.debug("Reading LF's children from container block...")
        # NOTE: although we read index in here, it gets overridden in load_from_resource.
        self.index = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
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
        self.obj_id = util.xml2int(root.find("id").text)
        self.obj_name = root.find("name").text
        self.obj_name = self.obj_name if self.obj_name != None else ""

        XMLHelper().read(self, root, self.xml_structure)

    def _load_script_from_file(self, path):
        with file(path, 'rb') as script_file:
            # Skip the header info, except name offset
            script_file.seek(6 + 12)
            name_offset = ord(script_file.read(1))
            # read event table
            event_table_size = name_offset - script_file.tell()
            data = self._read_raw_data(script_file, event_table_size, False)
            self.event_table = data
            # skip the object name
            #script_file.seek(len(self.obj_name) + 1, os.SEEK_CUR) # doesn't work because obj_name may be "None" if it's blank in the XML
            while True:
                c = script_file.read(1)
                if c == "\x00":
                    break
            # read script data
            start_script = script_file.tell()
            script_file.seek(0, os.SEEK_END)
            end_script = script_file.tell()
            script_size = end_script - start_script
            script_file.seek(start_script, os.SEEK_SET)
            data = self._read_raw_data(script_file, script_size, False)
            self.script_data = data

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        # TODO: validate values fit into clamped?
        y_and_parent_state = (self.parent_state & 0x80) | (self.y & 0x7F)
        height_and_actor_dir = (self.height & 0xF8) | (self.height & 0x07)

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
        self.obj_id = util.xml2int(root.find("id").text)

    def _load_data_from_file(self, path):
        with file(path, 'rb') as data_file:
            # Skip the header info
            data_file.seek(6 + 2)
            # read script data
            start_data = data_file.tell()
            data_file.seek(0, os.SEEK_END)
            end_data = data_file.tell()
            data_size = end_data - start_data
            data_file.seek(start_data, os.SEEK_SET)
            logging.debug("Attempting to load %s. start_data = %s. end_data = %s. data_size = %s" % (path, start_data, end_data, data_size))
            data = self._read_raw_data(data_file, data_size, False)
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
    name = "SO"

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_num = control.global_index_map.get_index("LF", room_start)
        room_offset = control.global_index_map.get_index("RO", room_num)
        control.global_index_map.map_index(self.name,
                                           (room_num, location - room_offset),
                                           self.index)
        super(BlockSOV4, self).save_to_resource(resource, room_start)
    
    def load_from_file(self, path):
        name = os.path.split(path)[1]
        self.is_cd_track = False
        self.name = name.split('_')[0]
        self.index = int(name.split('_')[1])
        self.children = []

        file_list = os.listdir(path)

        for f in file_list:
            b = control.file_dispatcher.dispatch_next_block(f)
            if b != None:
                b.load_from_file(os.path.join(path, f))
                self.append(b)    
    
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
    num_local_name = "LC" # I used to have this as NL, not sure why.
