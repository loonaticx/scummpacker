#! /usr/bin/python
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

class BlockDefaultV5(AbstractBlock):
    def _read_header(self, resource, decrypt):
        # Should be reversed for old format resources
        self.name = self._read_name(resource, decrypt)
        self.size = self._read_size(resource, decrypt)

    def _write_header(self, outfile, encrypt):
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)
        size = util.int_to_str(self.size, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)
        size = util.int_to_str(0, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)


class BlockSoundV5(BlockDefaultV5):
    """ Sound blocks store incorrect block size (it doesn't include the SOU/ADL/SBL header size)"""
    def _read_size(self, resource, decrypt):
        size = resource.read(4)
        if decrypt:
            size = util.crypt(size, self.crypt_value)
        return util.str_to_int(size, is_BE=util.BE) + 8

    def _write_header(self, outfile, encrypt):
        name = self.name
        if len(name) == 3:
            name = name + " "
        name = util.crypt(name, self.crypt_value) if encrypt else name
        outfile.write(name)
        size = util.int_to_str(self.size - 8, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        name = self.name
        if len(name) == 3:
            name = name + " "
        name = util.crypt(name, self.crypt_value) if encrypt else name
        outfile.write(name)
        size = util.int_to_str(0, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)

    def generate_file_name(self):
        return self.name.rstrip()

class BlockGloballyIndexedV5(BlockGloballyIndexed, BlockDefaultV5):
    lf_name = "LFLF"
    room_name = "ROOM"

class BlockContainerV5(BlockContainer, BlockDefaultV5):
    block_ordering = [
        #"LECF", # don't... just don't.
        "LOFF",
        "LFLF",

        # Inside LFLF
        "ROOM",

        # Inside ROOM
        "RMHD",
        "CYCL",
        "TRNS",
        "EPAL",
        "BOXD",
        "BOXM",
        "CLUT",
        "SCAL",
        "RMIM",
         #Inside RMIM
         "RMIH",
         "IM", # IMxx
          #Inside IMxx
          "SMAP",
          "ZP", # ZPxx
        "objects",
        "OBIM",
         #Inside OBIM
         "IMHD",
         "IM",
          #Inside IMxx
          "SMAP",
          "BOMP", # appears in object 1045 in MI1CD.
          "ZP", # ZPxx
        "OBCD",
         #Inside OBCD
         "CDHD",
         "VERB",
         "OBNA",
        "scripts",
        "EXCD",
        "ENCD",
        "NLSC",
        "LSCR",

        # Inside LFLF
        "SCRP",
        "SOUN",
         # Inside SOUN
         "SOU",
         "SOU ",
         "ROL",
         "ROL ",
         "SBL",
         "SBL ",
         "ADL",
         "ADL ",
         "SPK",
         "SPK ",
        "COST",
        "CHAR"
    ]

    def _find_block_rank_lookup_name(self, block):
        rank_lookup_name = block.name
        # dumb crap here
        if rank_lookup_name[:2] == "ZP" or rank_lookup_name[:2] == "IM":
            rank_lookup_name = rank_lookup_name[:2]
        return rank_lookup_name

class BlockMIDISoundV5(BlockSoundV5):
    """ Saves the MDhd header data to a .mhd file, saves the rest of the block
    to a .mid file."""
    MDHD_SIZE = 16
    MDHD_DEFAULT_DATA = "\x4D\x44\x68\x64\x00\x00\x00\x08\x00\x00\x80\x7F\x00\x00\x00\x80"

    def load_from_file(self, path):
        self.name = os.path.splitext(os.path.split(path)[1])[0]
        mdhd_fname = os.path.splitext(path)[0] + ".mdhd"
        if os.path.isfile(mdhd_fname):
            logging.debug("Loading mdhd from file: " + mdhd_fname)
            mdhd_file = file(mdhd_fname, 'rb')
            mdhd_data = self._read_raw_data(mdhd_file, self.MDHD_SIZE, False)
            mdhd_file.close()
        else:
            mdhd_data = self._generate_mdhd_header()
        self.mdhd_header = mdhd_data
        self.size = os.path.getsize(path) # size does not include ADL/ROL block header
        midi_file = file(path, 'rb')
        self._read_data(midi_file, 0, False)
        midi_file.close()

    def save_to_file(self, path):
        # Possibly the only MDhd block that is different:
        # MI1CD\LECF\LFLF_011\SOUN_043\SOU
        # 4D44 6864 0000 0008 0000 FF7F 0000 0080
        if self.mdhd_header.tostring() != self.MDHD_DEFAULT_DATA:
            outfile = file(os.path.join(path, self.generate_file_name() + ".mdhd"), 'wb')
            self._write_mdhd_header(outfile, False)
            outfile.close()
        outfile = file(os.path.join(path, self.generate_file_name() + ".mid"), 'wb')
        self._write_data(outfile, False)
        outfile.close()

    def save_to_resource(self, resource, room_start=0):
        self._write_header(resource, True)
        self._write_mdhd_header(resource, True)
        self._write_data(resource, True)

    def _read_header(self, resource, decrypt):
        """ Also reads the MDHD header."""
        super(BlockMIDISoundV5, self)._read_header(resource, decrypt)
        self.mdhd_header = self._read_raw_data(resource, self.MDHD_SIZE, decrypt)

    def _write_header(self, outfile, encrypt):
        """ Hack to support adding of MDHD header size."""
        name = self.name
        if len(name) == 3:
            name = name + " "
        name = util.crypt(name, self.crypt_value) if encrypt else name
        outfile.write(name)
        size = self.size + self.MDHD_SIZE # size includes MDHD header, does not include ADL/ROL block header
        size = util.int_to_str(size, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)

    def _write_mdhd_header(self, outfile, encrypt):
        outfile.write(util.crypt(self.mdhd_header, (self.crypt_value if encrypt else None)))

    def _generate_mdhd_header(self):
        return array.array('B', self.MDHD_DEFAULT_DATA)

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
        au_header = BlockSBLV5.AU_HEADER + util.int_to_str(voc_size, 4, util.BE, None)
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
                  + util.int_to_str(data_offset, num_bytes=2)
                  + util.int_to_str(voc_version, num_bytes=2)
                  + util.int_to_str(voc_version_complement, num_bytes=2))
        header = (util.crypt(header, self.crypt_value) if encrypt else header)
        outfile.write(header)

    def generate_file_name(self):
        return self.name.rstrip() + ".voc"

class BlockROOMV5(BlockContainerV5): # also globally indexed
    name = "ROOM"

    def __init__(self, *args, **kwds):
        super(BlockROOMV5, self).__init__(*args, **kwds)
        self.script_types = frozenset(["ENCD",
                                       "EXCD",
                                       "LSCR"])
        self.object_types = frozenset(["OBIM",
                                       "OBCD"])

    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        object_container = ObjectBlockContainer(self.block_name_length, self.crypt_value)
        script_container = ScriptBlockContainerV5(self.block_name_length, self.crypt_value)
        while resource.tell() < end:
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource)
            if block.name in self.script_types:
                script_container.append(block)
            elif block.name == "OBIM":
                object_container.add_image_block(block)
            elif block.name == "OBCD":
                object_container.add_code_block(block)
            elif block.name == "NLSC": # ignore this since we can generate it
                del block
                continue
            else:
                self.append(block)
        self.append(object_container)
        self.append(script_container)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        logging.debug("Saving ROOM")
        #print control.global_index_map.items("ROOM")
        room_num = control.global_index_map.get_index("LFLF", room_start)
        control.global_index_map.map_index("ROOM", room_num, location)
        super(BlockROOMV5, self).save_to_resource(resource, room_start)

class BlockLOFFV5(BlockDefaultV5):
    name = "LOFF"

    def _read_data(self, resource, start, decrypt):
        num_rooms = util.str_to_int(resource.read(1),
                                    crypt_val=(self.crypt_value if decrypt else None))

        for i in xrange(num_rooms):
            room_no = util.str_to_int(resource.read(1),
                                      crypt_val=(self.crypt_value if decrypt else None))
            room_offset = util.str_to_int(resource.read(4),
                                      crypt_val=(self.crypt_value if decrypt else None))

            control.global_index_map.map_index("LFLF", room_offset - self.block_name_length - 4, room_no)
            control.global_index_map.map_index("ROOM", room_no, room_offset) # HACK

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
        room_table = sorted(control.global_index_map.items("ROOM"))
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
        for i in xrange(num_rooms):
            resource.write("\x00" * 5)
        block_end = resource.tell()
        self.size = block_end - block_start

class ScriptBlockContainerV5(ScriptBlockContainer):
    local_scripts_name = "LSCR"
    entry_script_name = "ENCD"
    exit_script_name = "EXCD"
    lf_name = "LFLF"
    num_local_name = "NLSC"

class BlockLSCRV5(BlockLocalScript, BlockDefaultV5):
    name = "LSCR"

class ObjectBlockContainer(object):
    OBJ_ID_LENGTH = 4

    """ Contains objects, which contain image and code blocks."""
    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        self.objects = {}
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
        self.name = "objects"
        self.order_map = { "OBCD" : [], "OBIM" : [] }

    def add_code_block(self, block):
        if not block.obj_id in self.objects:
            self.objects[block.obj_id] = [None, None] # pos1 = image, pos2 = code
        self.objects[block.obj_id][1] = block
        self.order_map["OBCD"].append(block.obj_id)

    def add_image_block(self, block):
        if not block.obj_id in self.objects:
            self.objects[block.obj_id] = [None, None] # pos1 = image, pos2 = code
        self.objects[block.obj_id][0] = block
        self.order_map["OBIM"].append(block.obj_id)

    def save_to_file(self, path):
        objects_path = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(objects_path):
            os.mkdir(objects_path) # throws an exception if can't create dir
        for objimage, objcode in self.objects.values():
            # New path name = Object ID + object name (removing trailing spaces)
            obj_path_name = str(objcode.obj_id).zfill(self.OBJ_ID_LENGTH) + "_" + util.discard_invalid_chars(objcode.obj_name).rstrip()
            #logging.debug("Writing object: %s" % obj_path_name)
            newpath = os.path.join(objects_path, obj_path_name)
            if not os.path.isdir(newpath):
                os.mkdir(newpath) # throws an exception if can't create dir
            objimage.save_to_file(newpath)
            objcode.save_to_file(newpath)
            self._save_header_to_xml(newpath, objimage, objcode)
        self._save_order_to_xml(objects_path)

    def save_to_resource(self, resource, room_start=0):
        object_keys = self.objects.keys()
        # Write all image blocks first
        object_keys = util.ordered_sort(object_keys, self.order_map["OBIM"])
        for obj_id in object_keys:
            #logging.debug("Writing object image: " + str(obj_id))
            self.objects[obj_id][0].save_to_resource(resource, room_start)

        # Then write all object code/names
        object_keys = util.ordered_sort(object_keys, self.order_map["OBCD"])
        for obj_id in object_keys:
            #logging.debug("Writing object code: " + str(objcode.obj_id))
            self.objects[obj_id][1].save_to_resource(resource, room_start)

    def _save_header_to_xml(self, path, objimage, objcode):
        # Save the joined header information as XML
        root = et.Element("object")

        #shared = et.SubElement(root, "shared")
        et.SubElement(root, "name").text = util.escape_invalid_chars(objcode.obj_name)
        et.SubElement(root, "id").text = util.output_int_to_xml(objcode.obj_id)

        # OBIM
        obim = et.SubElement(root, "image")
        et.SubElement(obim, "x").text = util.output_int_to_xml(objimage.imhd.x)
        et.SubElement(obim, "y").text = util.output_int_to_xml(objimage.imhd.y)
        et.SubElement(obim, "width").text = util.output_int_to_xml(objimage.imhd.width)
        et.SubElement(obim, "height").text = util.output_int_to_xml(objimage.imhd.height)
        et.SubElement(obim, "flags").text = util.output_int_to_xml(objimage.imhd.flags, util.HEX)
        et.SubElement(obim, "unknown").text = util.output_int_to_xml(objimage.imhd.unknown, util.HEX)
        et.SubElement(obim, "num_images").text = util.output_int_to_xml(objimage.imhd.num_imnn)
        et.SubElement(obim, "num_zplanes").text = util.output_int_to_xml(objimage.imhd.num_zpnn)

        # OBCD
        obcd = et.SubElement(root, "code")
        et.SubElement(obcd, "x").text = util.output_int_to_xml(objcode.cdhd.x)
        et.SubElement(obcd, "y").text = util.output_int_to_xml(objcode.cdhd.y)
        et.SubElement(obcd, "width").text = util.output_int_to_xml(objcode.cdhd.width)
        et.SubElement(obcd, "height").text = util.output_int_to_xml(objcode.cdhd.height)
        et.SubElement(obcd, "flags").text = util.output_int_to_xml(objcode.cdhd.flags, util.HEX)
        et.SubElement(obcd, "parent").text = util.output_int_to_xml(objcode.cdhd.parent)
        et.SubElement(obcd, "walk_x").text = util.output_int_to_xml(objcode.cdhd.walk_x)
        et.SubElement(obcd, "walk_y").text = util.output_int_to_xml(objcode.cdhd.walk_y)
        et.SubElement(obcd, "actor_dir").text = util.output_int_to_xml(objcode.cdhd.actor_dir)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "OBHD.xml"))

    def _save_order_to_xml(self, path):
        root = et.Element("order")

        for block_type, order_list in self.order_map.items():
            order_list_node = et.SubElement(root, "order-list")
            order_list_node.set("block-type", block_type)
            for o in order_list:
                et.SubElement(order_list_node, "order-entry").text = util.output_int_to_xml(o)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "order.xml"))

    def load_from_file(self, path):
        file_list = os.listdir(path)

        re_pattern = re.compile(r"[0-9]{" + str(self.OBJ_ID_LENGTH) + r"}_.*")
        object_dirs = [f for f in file_list if re_pattern.match(f) != None]
        self.order_map = { "OBCD" : [], "OBIM" : [] }
        for od in object_dirs:
            new_path = os.path.join(path, od)

            objimage = BlockOBIMV5(self.block_name_length, self.crypt_value)
            objimage.load_from_file(new_path)
            self.add_image_block(objimage)

            objcode = BlockOBCDV5(self.block_name_length, self.crypt_value)
            objcode.load_from_file(new_path)
            self.add_code_block(objcode)

        self._load_order_from_xml(path)

    def _load_order_from_xml(self, path):
        order_fname = os.path.join(path, "order.xml")
        if not os.path.isfile(order_fname):
            # If order.xml does not exist, use whatever order we want.
            return

        tree = et.parse(order_fname)
        root = tree.getroot()

        loaded_order_map = self.order_map
        self.order_map = { "OBCD" : [], "OBIM" : [] }

        for order_list in root.findall("order-list"):
            block_type = order_list.get("block-type")

            for o in order_list.findall("order-entry"):
                if not block_type in self.order_map:
                    self.order_map[block_type] = []
                self.order_map[block_type].append(util.parse_int_from_xml(o.text))

            # Retain order of items loaded but not present in order.xml
            if block_type in loaded_order_map:
                extra_orders = [i for i in loaded_order_map[block_type] if not i in self.order_map[block_type]]
                self.order_map[block_type].extend(extra_orders)

    def generate_file_name(self):
        return "objects"

    def __repr__(self):
        childstr = ["obj_" + str(c) for c in self.objects.keys()]
        return "[OBIM & OBCD, " + "[" + ", ".join(childstr) + "] " + "]"


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


class BlockIMHDV5(BlockDefaultV5):
    name = "IMHD"

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
        self.obj_id = int(root.find("id").text)

        # OBIM
        obim_node = root.find("image")

        self.x = util.parse_int_from_xml(obim_node.find("x").text)
        self.y = util.parse_int_from_xml(obim_node.find("y").text)
        self.width = util.parse_int_from_xml(obim_node.find("width").text)
        self.height = util.parse_int_from_xml(obim_node.find("height").text)
        self.flags = util.parse_int_from_xml(obim_node.find("flags").text) # possibly wrong
        self.unknown = util.parse_int_from_xml(obim_node.find("unknown").text)

        self.num_imnn = util.parse_int_from_xml(obim_node.find("num_images").text)
        self.num_zpnn = util.parse_int_from_xml(obim_node.find("num_zplanes").text)


    def save_to_file(self, path):
        """ Combined OBHD.xml is saved in the ObjectBlockContainer."""
        return

    def _write_data(self, outfile, encrypt):
        data = struct.pack("<3H2B4H", self.obj_id, self.num_imnn, self.num_zpnn, self.flags, self.unknown,
            self.x, self.y, self.width, self.height)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)


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
        obj_id = int(root.find("id").text)
        self.obj_id = obj_id

        # OBCD
        obcd_node = root.find("code")
        self.x = util.parse_int_from_xml(obcd_node.find("x").text)
        self.y = util.parse_int_from_xml(obcd_node.find("y").text)
        self.width = util.parse_int_from_xml(obcd_node.find("width").text)
        self.height = util.parse_int_from_xml(obcd_node.find("height").text)

        self.flags = util.parse_int_from_xml(obcd_node.find("flags").text)
        self.parent = util.parse_int_from_xml(obcd_node.find("parent").text)
        self.walk_x = util.parse_int_from_xml(obcd_node.find("walk_x").text)
        self.walk_y = util.parse_int_from_xml(obcd_node.find("walk_y").text)
        self.actor_dir = util.parse_int_from_xml(obcd_node.find("actor_dir").text)

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<H6B2hB", self.obj_id, self.x, self.y, self.width, self.height, self.flags,
            self.parent, self.walk_x, self.walk_y, self.actor_dir)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)


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

        self.width = util.parse_int_from_xml(root.find("width").text)
        self.height = util.parse_int_from_xml(root.find("height").text)
        self.num_objects = util.parse_int_from_xml(root.find("num_objects").text)

    def save_to_file(self, path):
        root = et.Element("room")

        et.SubElement(root, "width").text = util.output_int_to_xml(self.width)
        et.SubElement(root, "height").text = util.output_int_to_xml(self.height)
        et.SubElement(root, "num_objects").text = util.output_int_to_xml(self.num_objects)

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

        self.num_zbuffers = util.parse_int_from_xml(root.find("num_zbuffers").text)

    def save_to_file(self, path):
        root = et.Element("room_image")

        et.SubElement(root, "num_zbuffers").text = util.output_int_to_xml(self.num_zbuffers)

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
        cd_block_size = util.str_to_int(resource.read(4), crypt_val=(self.crypt_value if decrypt else None))
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
            self._write_header(resource, True)
            self._write_raw_data(resource, True)
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

class BlockLECFV5(BlockContainerV5):
    name = "LECF"

    def load_from_file(self, path):
        # assume input path is actually the directory containing the LECF dir
        super(BlockLECFV5, self).load_from_file(os.path.join(path, "LECF"))

    def save_to_resource(self, resource, room_start=0):
        start = resource.tell()

        # write dummy header
        self._write_dummy_header(resource, True)

        # write dummy LOFF
        loff_start = resource.tell()
        loff_block = BlockLOFFV5(self.block_name_length, self.crypt_value)
        #loff_block.name = "LOFF" # CRAAAP
        num_rooms = len(self.children)
        loff_block.write_dummy_block(resource, num_rooms)

        # process children
        for c in self.children:
            #if hasattr(c, 'index'):
            #    logging.debug("object " + str(c) + " has index " + str(c.index))
            #logging.debug("location: " + str(resource.tell()))
            c.save_to_resource(resource, room_start)

        # go back and write size of LECF block (i.e. the whole ".001" file)
        self.size = resource.tell() - start
        resource.flush()
        end = resource.tell()
        resource.seek(start, os.SEEK_SET)
        self._write_header(resource, True)

        # go back and write the LOFF block
        loff_block.save_to_resource(resource, room_start)
        resource.seek(end, os.SEEK_SET)

    def __repr__(self):
        childstr = [str(c) for c in self.children]
        return "[" + self.name + ", " + ", \n".join(childstr) + "]"

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

class BlockIndexDirectoryV5(BlockDefaultV5):
    DIR_TYPES = {
        "DROO" : "ROOM",
        "DSCR" : "SCRP",
        "DSOU" : "SOUN",
        "DCOS" : "COST",
        "DCHR" : "CHAR"
        #"DOBJ" : "OBCD"
    }
    MIN_ENTRIES = {
        "MI1CD" : {
            "DSCR" : 199,
            "DSOU" : 150,
            "DCOS" : 150,
            "DCHR" : 7
        },
        "MI2" : {
            "DSCR" : 199,
            "DSOU" : 254,
            "DCOS" : 199,
            "DCHR" : 9
        },
        "FOA" : {
            "DSCR" : 200,
            "DSOU" : 250,
            "DCOS" : 244,
            "DCHR" : 6
        }
    }

    def _read_data(self, resource, start, decrypt):
        num_items = util.str_to_int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        room_nums = []
        i = num_items
        while i > 0:
            room_no = util.str_to_int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            room_nums.append(room_no)
            i -= 1
        offsets = []
        i = num_items
        while i > 0:
            offset = util.str_to_int(resource.read(4), crypt_val=(self.crypt_value if decrypt else None))
            offsets.append(offset)
            i -= 1

        for i, key in enumerate(zip(room_nums, offsets)):
            control.global_index_map.map_index(self.DIR_TYPES[self.name], key, i)

    def save_to_file(self, path):
        """This block is generated when saving to a resource."""
        return

    def save_to_resource(self, resource, room_start=0):
        # is room_start required? nah, just there for interface compliance.
        #for i, key in enumerate()
        items = control.global_index_map.items(self.DIR_TYPES[self.name])
        item_map = {}
        if len(items) == 0:
            logging.info("No indexes found for block type \"" + self.name + "\" - are there any files of this block type?")
            num_items = self.MIN_ENTRIES[control.global_args.game][self.name]
        else:
            items.sort(cmp=lambda x, y: cmp(x[1], y[1])) # sort by resource number
            # Need to pad items out, so take last entry's number as the number of items
            num_items = items[-1][1]
            if self.name in self.MIN_ENTRIES[control.global_args.game] and \
               num_items < self.MIN_ENTRIES[control.global_args.game][self.name]:
                num_items = self.MIN_ENTRIES[control.global_args.game][self.name]
            # Create map with reversed key/value pairs
            for i, j in items:
                item_map[j] = i

        # Bleeech
        self.size = 5 * num_items + 2 + self.block_name_length + 4
        self._write_header(resource, True)

        resource.write(util.int_to_str(num_items, 2, crypt_val=self.crypt_value))
        for i in xrange(num_items):
            if not i in item_map:
                # write dummy values for unused item numbers.
                resource.write(util.int_to_str(0, 1, crypt_val=self.crypt_value))
            else:
                room_num, _ = item_map[i]
                resource.write(util.int_to_str(room_num, 1, crypt_val=self.crypt_value))
        for i in xrange(num_items):
            if not i in item_map:
                # write dummy values for unused item numbers.
                resource.write(util.int_to_str(0, 4, crypt_val=self.crypt_value))
            else:
                _, offset = item_map[i]
                resource.write(util.int_to_str(offset, 4, crypt_val=self.crypt_value))

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
            et.SubElement(obj_node, "class-data").text = util.output_int_to_xml(class_data, util.HEX)

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


def __test_unpack():
    import dispatchers
    control.global_args.set_args(unpack=True, pack=False, scumm_version="5",
        game="MI2", input_file_name="MONKEY2.000", output_file_name="D:\\TEMP")
    control.unknown_blocks_counter = control.IndexCounter(*dispatchers.INDEXED_BLOCKS_V5)
    control.global_index_map = control.IndexMappingContainer(*dispatchers.INDEXED_BLOCKS_V5)

    outpath = "D:\\TEMP"

    dirfile = file("MONKEY2.000", "rb")
    dir_block = dispatchers.IndexBlockContainerV5()
    dir_block.load_from_resource(dirfile)
    dirfile.close()

    dir_block.save_to_file(outpath)

    control.block_dispatcher = dispatchers.BlockDispatcherV5()
    resfile = file("MONKEY2.001", "rb")
    block = BlockLECFV5(4, 0x69)
    block.load_from_resource(resfile)
    resfile.close()

    block.save_to_file(outpath)

def __test_pack():
    import dispatchers
    control.global_args.set_args(unpack=False, pack=True, scumm_version="5",
        game="MI2", input_file_name="D:\\TEMP", output_file_name="D:\\TEMP\\outres.000")
    control.file_dispatcher = dispatchers.FileDispatcherV5()
    control.unknown_blocks_counter = control.IndexCounter(*dispatchers.INDEXED_BLOCKS_V5)
    control.global_index_map = control.IndexMappingContainer(*dispatchers.INDEXED_BLOCKS_V5)

    startpath = "D:\\TEMP"

    block = BlockLECFV5(4, 0x69)
    block.load_from_file(startpath)
    index_block = dispatchers.IndexBlockContainerV5()
    index_block.load_from_file(startpath)

    logging.info("read from file, now saving to resource")

    outpath_res = os.path.join(startpath, "outres.001")
    with file(outpath_res, 'wb') as outres:
        block.save_to_resource(outres)
    outpath_index = os.path.join(startpath, "outres.000")
    with file(outpath_index, 'wb') as outindres:
        index_block.save_to_resource(outindres)


def __test():
    __test_unpack()
    __test_pack()

# TODO: better integration test dispatching
test_blocks_v5 = __test

if __name__ == "__main__": __test()
