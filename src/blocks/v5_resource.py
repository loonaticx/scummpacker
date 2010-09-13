# TODO: sort out imports
from __future__ import with_statement
import array
import logging
import os
import re
import struct
import xml.etree.ElementTree as et
import scummpacker_control as control
import scummpacker_util as util
from common import *
from v5_base import *

class BlockSOUV5(BlockSoundV5, BlockContainerV5):
    name = "SOU"

class BlockSBLV5(BlockSoundV5):
    name = "SBL"
    AU_HEADER = "AUhd\x00\x00\x00\x03\x00\x00\x80AUdt"

    def _read_data(self, resource, start, decrypt):
        # SBL blocks have AUhd and AUdt headers instead of
        #  "Creative Voice File".
        # Skip AUhd/AUdt and just read the rest of the raw data,
        #  we can regenerate the header later.
        resource.seek(19, os.SEEK_CUR)
        super(BlockSBLV5, self)._read_data(resource, start, decrypt)

    def load_from_file(self, path):
        self.name = os.path.splitext(os.path.split(path)[1])[0]
        self.size = os.path.getsize(path) - 0x1A + 27 # ignore VOC header, add SBL block header (could just +1)
        voc_file = file(path, 'rb')
        voc_file.seek(0x1A, os.SEEK_CUR)
        self.data = self._read_raw_data(voc_file, self.size - 27, False)
        voc_file.close()

    def save_to_file(self, path):
        outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
        self._write_voc_header(outfile, False)
        self._write_data(outfile, False)
        outfile.close()

    def save_to_resource(self, resource, room_start=0):
        self._write_header(resource, True)
        self._write_auhd_header(resource, True)
        self._write_data(resource, True)

    def _write_auhd_header(self, outfile, encrypt):
        voc_size = self.size - 27 # ignore all header info for size
        au_header = BlockSBLV5.AU_HEADER + util.int2str(voc_size, 4, util.BE, None)
        au_header = (util.crypt(au_header, self.crypt_value if encrypt else None))
        outfile.write(au_header)

    def _write_voc_header(self, outfile, encrypt):
        """
        SBL block strips the "Creative Voice File" header information, so we
        have to restore it. Thankfully there's not much there except for the
        start of the data and the version of the VOC format.
        00h     14h     Contains the string "Creative Voice File" plus an EOF byte.
        14h     2       The file offset to the sample data. This value usually is
                        001Ah.
        16h     2       Version number. The major version is in the high byte, the
                        minor version in the low byte.
        18h     2       Validity check. This word contains the complement (NOT
                        operation) value of offset 16h added to 1234h.
        1Ah     ...     Start of the sample data.
        """
        header_name = "Creative Voice File\x1A"
        data_offset = 0x1A
        voc_version = 0x010A
        voc_version_complement = (0x1234 + ~voc_version) & 0xFFFF
        header = (header_name
                  + util.int2str(data_offset, num_bytes=2)
                  + util.int2str(voc_version, num_bytes=2)
                  + util.int2str(voc_version_complement, num_bytes=2))
        header = (util.crypt(header, self.crypt_value) if encrypt else header)
        outfile.write(header)

    def generate_file_name(self):
        return self.name.rstrip() + ".voc"

class BlockROOMV5(BlockRoom, BlockContainerV5): # also globally indexed
    def _init_class_data(self):
        self.name = "ROOM"
        self.lf_name = "LFLF"
        self.script_types = frozenset(["ENCD",
                                  "EXCD",
                                  "LSCR"])
        self.object_types = frozenset(["OBIM",
                                  "OBCD"])
        self.object_image_type = "OBIM"
        self.object_code_type = "OBCD"
        self.num_scripts_type = "NLSC"
        self.script_container_class = ScriptBlockContainerV5
        self.object_container_class = ObjectBlockContainerV5

class BlockLOFFV5(BlockRoomOffsets, BlockDefaultV5):
    name = "LOFF"
    LFLF_NAME = "LFLF"
    ROOM_NAME = "ROOM"
    OFFSET_POINTS_TO_ROOM = True

class BlockLSCRV5(BlockLocalScript, BlockDefaultV5):
    name = "LSCR"

class BlockOBIMV5(BlockContainerV5):
    name = "OBIM"

    def _read_data(self, resource, start, decrypt):
        end = start + self.size

        # Load the header
        block = BlockIMHDV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.imhd = block

        # Load the image data
        i = block.num_imnn
        while i > 0:
            block = BlockContainerV5(self.block_name_length, self.crypt_value)
            block.load_from_resource(resource)
            self.append(block)
            i -= 1

    def load_from_file(self, path):
        # Load the header
        block = BlockIMHDV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "OBHD.xml"))
        self.append(block)
        self.obj_id = block.obj_id
        self.imhd = block
        self.name = "OBIM"

        # Load the image data
        file_list = os.listdir(path)
        re_pattern = re.compile(r"IM[0-9a-fA-F]{2}")
        imnn_dirs = [f for f in file_list if re_pattern.match(f) != None]
        if len(imnn_dirs) != block.num_imnn:
            raise util.ScummPackerException("Number of images in the header ("
            + str(block.num_imnn)
            + ") does not match the number of image directories ("
            + str(len(imnn_dirs))
            + ")")

        for d in imnn_dirs:
            new_path = os.path.join(path, d)
            block = BlockContainerV5(self.block_name_length, self.crypt_value)
            block.load_from_file(new_path)
            self.append(block)

    def generate_file_name(self):
        return ""

    def generate_xml_node(self, parent_node):
        """ Adds a new XML node to the given parent node."""
        self.imhd.generate_xml_node(parent_node)


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
        # Dump image stuff using XML structure
        XMLHelper().read(self, root, self.xml_structure)

    def save_to_file(self, path):
        """ Combined OBHD.xml is saved in the ObjectBlockContainer."""
        return

    def _write_data(self, outfile, encrypt):
        data = struct.pack("<3H2B4H", self.obj_id, self.num_imnn, self.num_zpnn, self.flags, self.unknown,
            self.x, self.y, self.width, self.height)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)

    def generate_xml_node(self, parent_node):
        """ Adds a new XML node to the given parent node."""
        XMLHelper().write(self, parent_node, self.xml_structure)

class BlockOBCDV5(BlockContainerV5):
    name = "OBCD"

    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        block = BlockCDHDV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.cdhd = block

        block = BlockDefaultV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.verb = block

        block = BlockOBNAV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obna = block

        self.obj_name = self.obna.obj_name # cheat

    def load_from_file(self, path):
        self.name = "OBCD"
        block = BlockCDHDV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "OBHD.xml"))
        self.obj_id = block.obj_id # maybe should handle header info better
        self.cdhd = block

        block = BlockDefaultV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "VERB.dmp")) # hmm
        self.verb = block

        block = BlockOBNAV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "OBHD.xml"))
        self.obna = block

        self.obj_name = self.obna.obj_name # cheat

    def save_to_file(self, path):
        self.verb.save_to_file(path)

    def save_to_resource(self, resource, room_start=0):
        start = resource.tell()
        self._write_dummy_header(resource, True)
        self.cdhd.save_to_resource(resource, room_start)
        self.verb.save_to_resource(resource, room_start)
        self.obna.save_to_resource(resource, room_start)
        end = resource.tell()
        self.size = end - start
        resource.flush()
        resource.seek(start, os.SEEK_SET)
        self._write_header(resource, True)
        resource.flush()
        resource.seek(end, os.SEEK_SET)

    def generate_file_name(self):
        return str(self.obj_id) + "_" + self.obj_name

    def generate_xml_node(self, parent_node):
        self.cdhd.generate_xml_node(parent_node)

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

    def _read_data(self, resource, start, decrypt):
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

        XMLHelper().read(self, root, self.xml_structure)

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<H6B2hB", self.obj_id, self.x, self.y, self.width, self.height, self.flags,
            self.parent, self.walk_x, self.walk_y, self.actor_dir)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)

    def generate_xml_node(self, parent_node):
        XMLHelper().write(self, parent_node, self.xml_structure)


class BlockRMHDV5(BlockDefaultV5):
    name = "RMHD"

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
        #tree = et.parse(os.path.join(path, "header.xml"))
        tree = et.parse(path)
        root = tree.getroot()

        self.width = util.xml2int(root.find("width").text)
        self.height = util.xml2int(root.find("height").text)
        self.num_objects = util.xml2int(root.find("num_objects").text)

    def save_to_file(self, path):
        root = et.Element("room")

        et.SubElement(root, "width").text = util.int2xml(self.width)
        et.SubElement(root, "height").text = util.int2xml(self.height)
        et.SubElement(root, "num_objects").text = util.int2xml(self.num_objects)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "RMHD.xml"))

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<3H", self.width, self.height, self.num_objects)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)


class BlockRMIHV5(BlockDefaultV5):
    name = "RMIH"

    def _read_data(self, resource, start, decrypt):
        """
        Assumes it's reading from a resource.
        num_zbuffers 16le
        """
        data = resource.read(2)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<H", data)
        del data

        # Unpack the values
        self.num_zbuffers = values[0]
        del values

    def load_from_file(self, path):
        self.name = "RMIH"
        self.size = 2 + 8
        self._load_header_from_xml(path)

    def _load_header_from_xml(self, path):
        #tree = et.parse(os.path.join(path, "header.xml"))
        tree = et.parse(path)
        root = tree.getroot()

        self.num_zbuffers = util.xml2int(root.find("num_zbuffers").text)

    def save_to_file(self, path):
        root = et.Element("room_image")

        et.SubElement(root, "num_zbuffers").text = util.int2xml(self.num_zbuffers)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "RMIH.xml"))

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<H", self.num_zbuffers)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)


class BlockSOUNV5(BlockContainerV5, BlockGloballyIndexedV5):
    """ SOUN blocks in V5 may contain CD track data. Unfortunately, these CD
    blocks have no nice header value to look for. Instead, we have to check
    the file size somehow."""

    # Potential task: do some crazy class mutation if this is a CD track.

    name = "SOUN"

    def __init__(self, *args, **kwds):
        super(BlockSOUNV5, self).__init__(*args, **kwds)
        self.is_cd_track = False

    def _read_data(self, resource, start, decrypt):
        # Not a great way of checking this, since we will try to interpret legit
        # block names as a number.
        # cd_block_size should always be 24 if it's CD track block.
        cd_block_size = util.str2int(resource.read(4), crypt_val=(self.crypt_value if decrypt else None))
        resource.seek(-4, os.SEEK_CUR) # rewind
        if cd_block_size == self.size - 8: # could just check if size == 32, but that might impact legit small blocks
            self.data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)
            self.is_cd_track = True
        else:
            end = start + self.size
            while resource.tell() < end:
                block = control.block_dispatcher.dispatch_next_block(resource)
                block.load_from_resource(resource)
                self.append(block)

    def save_to_file(self, path):
        if self.is_cd_track:
            outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
            self._write_header(outfile, False)
            self._write_raw_data(outfile, False)
            outfile.close()
        else:
            newpath = self._create_directory(path)
            self._save_children(newpath)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_num = control.global_index_map.get_index("LFLF", room_start)
        room_offset = control.global_index_map.get_index("ROOM", room_num)
        control.global_index_map.map_index(self.name,
                                           (room_num, location - room_offset),
                                           self.index)
        if self.is_cd_track:
            self._write_header(resource, self.data, True)
            self._write_raw_data(resource, self.data, True)
        else:
            super(BlockSOUNV5, self).save_to_resource(resource, room_start)

    def load_from_file(self, path):
        name = os.path.split(path)[1]
        if os.path.splitext(name)[1] == '':
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
        else:
            self.is_cd_track = True
            self.name = name.split('_')[0]
            self.index = int(os.path.splitext(name.split('_')[1])[0])
            self.children = []
            soun_file = file(path, 'rb')
            self._read_header(soun_file, False)
            self._read_data(soun_file, 0, False)
            soun_file.close()

    def generate_file_name(self):
        name = (self.name
                + "_"
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3))
        if self.is_cd_track:
            return name + ".dmp"
        else:
            return name


class BlockLFLFV5(BlockLucasartsFile, BlockContainerV5, BlockGloballyIndexedV5):
    name = "LFLF"

class BlockLECFV5(BlockLucasartsEntertainmentContainer, BlockContainerV5):
    def _init_class_data(self):
        self.name = "LECF"
        self.OFFSET_CLASS = BlockLOFFV5
    
# Meta containers
class ObjectBlockContainerV5(ObjectBlockContainer):
    def _init_class_data(self):
        self.obcd_name = "OBCD"
        self.obim_name = "OBIM"
        self.obcd_class = BlockOBCDV5
        self.obim_class = BlockOBIMV5
        
class ScriptBlockContainerV5(ScriptBlockContainer):
    local_scripts_name = "LSCR"
    entry_script_name = "ENCD"
    exit_script_name = "EXCD"
    lf_name = "LFLF"
    num_local_name = "NLSC"
