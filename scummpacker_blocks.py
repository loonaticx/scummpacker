from __future__ import with_statement # bleh
import array
import os
import re
import struct
import sys
import xml.etree.ElementTree as et
import scummpacker_control as control
import scummpacker_util as util

if sys.version_info[0] < 2 or (sys.version_info[0] == 2 and sys.version_info[1] < 5):
    raise util.ScummPackerException("ScummPacker requires Python 2.5 or higher.")

block_order_res_v5 = [
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

block_dispatcher = None
file_dipsatcher = None

class AbstractBlock(object):
    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        super(AbstractBlock, self).__init__(*args, **kwds)
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
    
    def load_from_resource(self, resource, room_start=0):
        start = resource.tell()
        self._read_header(resource, True)
        self._read_data(resource, start, True)

    def save_to_resource(self, resource, room_start=0):
        #start = resource.tell()
        self._write_header(resource, True)
        self._write_data(resource, True)
        
    def _read_header(self, resource, decrypt):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start, decrypt):
        data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)
        self.data = data
        
    def _read_name(self, resource, decrypt):
        name = resource.read(self.block_name_length)
        if decrypt:
            name = util.crypt(name, self.crypt_value)
        return name
    
    def _read_size(self, resource, decrypt):
        size = resource.read(4)
        if decrypt:
            size = util.crypt(size, self.crypt_value)
        return util.str_to_int(size, is_BE=util.BE)
    
    def _read_raw_data(self, resource, size, decrypt):
        data = array.array('B')
        data.fromfile(resource, size)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        return data

    def load_from_file(self, path):
        block_file = file(path, 'rb')
        start = block_file.tell()
        self._read_header(block_file, False)
        self._read_data(block_file, start, False)
        block_file.close()

    def save_to_file(self, path):
        outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
        self._write_header(outfile, False)
        self._write_data(outfile, False)
        outfile.close()

    def _write_header(self, outfile, encrypt):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _write_data(self, outfile, encrypt):
        self._write_raw_data(outfile, encrypt)

    def _write_raw_data(self, outfile, encrypt):
        data = self.data
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        data.tofile(outfile)
        
    def generate_file_name(self):
        return self.name + ".dmp"
    
    def __repr__(self):
        return "[" + self.name + "]"


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

class BlockGloballyIndexedV5(BlockDefaultV5):
    def __init__(self, *args, **kwds):
        super(BlockGloballyIndexedV5, self).__init__(*args, **kwds)
        self.index = None
        self.is_unknown = False
    
    def load_from_resource(self, resource, room_start=0):
        location = resource.tell()
        super(BlockGloballyIndexedV5, self).load_from_resource(resource)
        try:
            room_num = control.global_index_map.get_index("LFLF", room_start)
            room_offset = control.global_index_map.get_index("ROOM", room_num) # HACK
            self.index = control.global_index_map.get_index(self.name, 
                                                             (room_num, location - room_offset))
        except util.ScummPackerUnrecognisedIndexException, suie:
            util.error("Block \"" 
                       + str(self.name)
                       + "\" at offset "
                       + str(location)
                       + " has no entry in the index file (.000). "
                       + "It can not be re-packed or used in the game.")
            self.is_unknown = True
            self.index = control.unknown_blocks_counter.get_next_index(self.name)

    def save_to_resource(self, resource, room_start=0):
        # Look up the start of the current ROOM block, store
        # a mapping of this block's index and room #/offset.
        # Later on, our directories will just treat global_index_map as a list of
        # tables and go through all of the values.
        location = resource.tell()
        #util.debug("Saving globally indexed block: " + self.name)
        #util.debug("LFLF: " + str(control.global_index_map.items("LFLF")))
        #util.debug("ROOM: " + str(control.global_index_map.items("ROOM")))
        room_num = control.global_index_map.get_index("LFLF", room_start)
        room_offset = control.global_index_map.get_index("ROOM", room_num)
        control.global_index_map.map_index(self.name,
                                           (room_num, location - room_offset),
                                           self.index)
        super(BlockGloballyIndexedV5, self).save_to_resource(resource, room_start)

    def load_from_file(self, path):
        """ Assumes we won't get any 'unknown' blocks, based on the regex in the file walker."""
        if os.path.isdir(path):            
            index = os.path.split(path)[1][-3:]
        else:
            fname = os.path.split(path)[1]
            index = os.path.splitext(fname)[0][-3:]
        try:
            self.index = int(index)
        except ValueError, ve:
            raise util.ScummPackerException(str(self.index) + " is an invalid index for resource " + path)
        super(BlockGloballyIndexedV5, self).load_from_file(path)

    def generate_file_name(self):
        return (self.name 
                + "_" 
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3) + ".dmp")
    
    def __repr__(self):
        return "[" + self.name + ":" + ("unk_" if self.is_unknown else "") + str(self.index).zfill(3) + "]"

    
class BlockContainerV5(BlockDefaultV5):
    def __init__(self, *args, **kwds):
        super(BlockContainerV5, self).__init__(*args, **kwds)
        self.children = []
    
    def _read_data(self, resource, start, decrypt):
        global block_dispatcher
        end = start + self.size
        while resource.tell() < end:
            block = block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource, start)
            self.append(block)
    
    def append(self, block):
        # Maintain sorted order for children
        #TODO: use bisect module for sorted insertion?
        global block_order_res_v5
        rank_lookup_name = block.name
        # dumb crap here but I'm sick of working on this crappy piece of software
        if rank_lookup_name[:2] == "ZP" or rank_lookup_name[:2] == "IM":
            rank_lookup_name = rank_lookup_name[:2]
        #util.debug("Appending block: " + str(rank_lookup_name))
        block_rank = block_order_res_v5.index(rank_lookup_name)
        for i, c in enumerate(self.children):
            c_rank_lookup_name = c.name
            if c_rank_lookup_name[:2] == "ZP" or c_rank_lookup_name[:2] == "IM":
                c_rank_lookup_name = c_rank_lookup_name[:2]
            #util.debug("Comparing block: " + str(c_rank_lookup_name))
            c_rank = block_order_res_v5.index(c_rank_lookup_name)
            if c_rank > block_rank:
                #util.debug("rank_lookup_name: " + str(rank_lookup_name) + ", c_rank: " + str(c_rank) + ", block_rank: " + str(block_rank))
                self.children.insert(i, block)
                return
        #util.debug("appending block, rank_lookup_name: " + str(rank_lookup_name) + ", block_rank: " + str(block_rank))
        self.children.append(block)
    
    def save_to_file(self, path):
        newpath = self._create_directory(path)
        self._save_children(newpath)
        
    def _create_directory(self, start_path):
        newpath = os.path.join(start_path, self.generate_file_name())
        if not os.path.isdir(newpath):
            os.mkdir(newpath) # throws an exception if can't create dir
        return newpath
    
    def _save_children(self, path):
        for child in self.children:
            child.save_to_file(path)
        
    def load_from_file(self, path):
        #global file_dispatcher #TODO?
        self.name = os.path.split(path)[1]
        self.children = []
        
        file_list = os.listdir(path)
        
        file_dispatcher = FileDispatcherV5()
        for f in file_list:
            b = file_dispatcher.dispatch_next_block(f)
            if b != None:
                b.load_from_file(os.path.join(path, f))
                self.append(b)

    def save_to_resource(self, resource, room_start=0):
        start = resource.tell()

        # write dummy header
        self._write_dummy_header(resource, True)
        # process children
        for c in self.children:
            c.save_to_resource(resource, room_start)
        
        # go back and write size of block
        end = resource.tell()
        self.size = end - start
        resource.flush()
        resource.seek(start, os.SEEK_SET)
        self._write_header(resource, True)
        resource.seek(end, os.SEEK_SET)

    def sort_children(self):
        """Ensures that children are stored & processed in the correct order."""
        global block_order_res_v5
        cmp_method = lambda x,y: cmp(block_order_res_v5.index(x.name),
                                     block_order_res_v5.index(y.name))
        self.children.sort(cmp=cmp_method)
        return

    def generate_file_name(self):
        return self.name
    
    def __repr__(self):
        childstr = [str(c) for c in self.children]
        return "[" + self.name + ", " + ", ".join(childstr) + "]"

class BlockMIDISoundV5(BlockSoundV5):
    """ Saves the MDhd header data to a .mhd file, saves the rest of the block 
    to a .mid file."""
    MDHD_SIZE = 16
    MDHD_DEFAULT_DATA = "\x4D\x44\x68\x64\x00\x00\x00\x08\x00\x00\x80\x7F\x00\x00\x00\x80"
    
    def load_from_file(self, path):
        self.name = os.path.splitext(os.path.split(path)[1])[0]
        try:
            mdhd_file = file(os.path.splitext(path)[0] + ".mdhd", 'rb')
            mdhd_data = self._read_raw_data(mdhd_file, self.MDHD_SIZE, False)
            mdhd_file.close()
        except Exception, e:
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
        if self.mdhd_header != self.MDHD_DEFAULT_DATA:
            outfile = file(os.path.join(path, self.generate_file_name() + ".mhd"), 'wb')
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
        global block_dispatcher
        end = start + self.size
        object_container = ObjectBlockContainer(self.block_name_length, self.crypt_value)
        script_container = ScriptBlockContainer(self.block_name_length, self.crypt_value)
        while resource.tell() < end:
            block = block_dispatcher.dispatch_next_block(resource)
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
        #util.debug("Saving ROOM")
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

class ScriptBlockContainer(object):
    script_types = frozenset(["ENCD", "EXCD", "LSCR"])

    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        self.local_scripts = []
        self.encd_script = None
        self.excd_script = None
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
        self.name = "scripts"
    
    def append(self, block):
        # Would be nice to compare them using self.script_types or similar...
        if block.name == "LSCR":
            self.local_scripts.append(block)
        elif block.name == "ENCD":
            self.encd_script = block
        elif block.name == "EXCD":
            self.excd_script = block
        else:
            raise util.ScummPackerException("Unrecognised script type: " + str(block.name))
    
    def save_to_file(self, path):
        newpath = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(newpath):
            os.mkdir(newpath) # throws an exception if can't create dir
        if self.encd_script:
            self.encd_script.save_to_file(newpath)
        if self.excd_script:
            self.excd_script.save_to_file(newpath)
        for s in self.local_scripts:
            s.save_to_file(newpath)

    def save_to_resource(self, resource, room_start=0):
        # Determine the number of local scripts (LSCR)
        num_local_scripts = len(self.local_scripts)
        # Write ENCD, EXCD blocks (seperate from LSCRs)
        if not self.encd_script or not self.excd_script:
            room_num = control.global_index_map.get_index("LFLF", room_start)
            raise util.ScummPackerException(
                "Room #" + str(room_num) + " appears to be missing either a room entry or exit script.")
        self.excd_script.save_to_resource(resource, room_start)
        self.encd_script.save_to_resource(resource, room_start)
        # Generate and write NLSC block (could be prettier, should have its own class)
        resource.write(util.crypt("NLSC", self.crypt_value))
        resource.write(util.int_to_str(10, 4, util.BE, self.crypt_value)) # size of this block is always 10
        resource.write(util.int_to_str(num_local_scripts, 2, util.LE, self.crypt_value))
        # Write all LSCRs sorted by script number
        self.local_scripts.sort(cmp=lambda x,y: cmp(x.script_id, y.script_id))
        for s in self.local_scripts:
            s.save_to_resource(resource, room_start)

    def load_from_file(self, path):
        file_list = os.listdir(path)
        
        file_dispatcher = FileDispatcherV5()
        for f in file_list:
            b = file_dispatcher.dispatch_next_block(f)
            if b != None: #and self.script_types: #TODO: only load recognised scripts
                b.load_from_file(os.path.join(path, f))
                self.append(b)
            
    def generate_file_name(self):
        return "scripts"
    
    def __repr__(self):
        childstr = [str(self.encd_script), str(self.excd_script)]
        childstr.extend([str(c) for c in self.local_scripts])
        return "[Scripts, " + ", ".join(childstr) + "]"

class BlockLSCRV5(BlockDefaultV5):
    name = "LSCR"

    def _read_data(self, resource, start, decrypt):
        script_id = resource.read(1)
        if decrypt:
            script_id = util.crypt(script_id, self.crypt_value)
        self.script_id = util.str_to_int(script_id)
        self.data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)
        
    def _write_data(self, outfile, encrypt):
        script_num = util.int_to_str(self.script_id, num_bytes=1)
        if encrypt:
            script_num = util.crypt(script_num, self.crypt_value)
        outfile.write(script_num)
        self._write_raw_data(outfile, encrypt)
        
    def generate_file_name(self):
        return self.name + "_" + str(self.script_id).zfill(3) + ".dmp"
        

class ObjectBlockContainer(object):
    OBJ_ID_LENGTH = 4

    """ Contains objects, which contain image and code blocks."""
    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        self.objects = {}
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
        self.name = "objects"
        self.obim_order = None # hacks to preserve order of object blocks
        self.obcd_order = None
    
    def add_code_block(self, block):
        if not block.obj_id in self.objects:
            self.objects[block.obj_id] = [None, None] # pos1 = image, pos2 = code
        self.objects[block.obj_id][1] = block

    def add_image_block(self, block):
        if not block.obj_id in self.objects:
            self.objects[block.obj_id] = [None, None] # pos1 = image, pos2 = code
        self.objects[block.obj_id][0] = block
        
    def save_to_file(self, path):
        objects_path = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(objects_path):
            os.mkdir(objects_path) # throws an exception if can't create dir
        for objimage, objcode in self.objects.values():
            newpath = os.path.join(objects_path, str(objcode.obj_id).zfill(self.OBJ_ID_LENGTH) + "_" + util.discard_invalid_chars(objcode.obj_name))
            if not os.path.isdir(newpath):
                os.mkdir(newpath) # throws an exception if can't create dir
            objimage.save_to_file(newpath)
            objcode.save_to_file(newpath)
            self._save_header_to_xml(newpath, objimage, objcode)

    def save_to_resource_old(self, resource, room_start=0):
        object_entries = self.objects.items()
        # NOTE: although we sort by object ID, original resources don't seem
        # to be fussy. See: MI1 CD, room 2, object 36 - the sequence for
        # images is object 31, 32, 33... but the sequence for codes
        # is object 31, 36, 32...!
        #util.ordered_sort(object_entries, self.obim_order)
        object_entries.sort() # sort by object id
        # TODO: keep track of where objects are written in the resource
        # Write all image blocks first
        for obj_id, (objimage, objcode) in object_entries:
            #util.debug("Writing object image: " + str(obj_id))
            objimage.save_to_resource(resource, room_start)
        # Then write all object code/names
        for obj_id, (objimage, objcode) in object_entries:
            #util.debug("Writing object code: " + str(objcode.obj_id))
            objcode.save_to_resource(resource, room_start)

    def save_to_resource(self, resource, room_start=0):
        # TODO: keep track of where objects are written in the resource
        object_keys = self.objects.keys()
        
        # Write all image blocks first
        util.ordered_sort(object_keys, self.obim_order)
        for obj_id in object_keys:
            #util.debug("Writing object image: " + str(obj_id))
            self.objects[obj_id][0].save_to_resource(resource, room_start)

        # Then write all object code/names
        util.ordered_sort(object_keys, self.obcd_order)
        for obj_id in object_keys:
            #util.debug("Writing object code: " + str(objcode.obj_id))
            self.objects[obj_id][1].save_to_resource(resource, room_start)

    def _save_header_to_xml(self, path, objimage, objcode):
        # Save the joined header information as XML
        root = et.Element("object")
    
        #shared = et.SubElement(root, "shared")
        et.SubElement(root, "name").text = util.escape_invalid_chars(objcode.obj_name)
        et.SubElement(root, "id").text = str(objcode.obj_id)
        
        # OBIM
        obim = et.SubElement(root, "image")
        et.SubElement(obim, "x").text = str(objimage.imhd.x)
        et.SubElement(obim, "y").text = str(objimage.imhd.y)
        et.SubElement(obim, "width").text = str(objimage.imhd.width)
        et.SubElement(obim, "height").text = str(objimage.imhd.height)
        et.SubElement(obim, "flags").text = str(objimage.imhd.flags)
        et.SubElement(obim, "unknown").text = str(objimage.imhd.unknown)
        et.SubElement(obim, "num_images").text = str(objimage.imhd.num_imnn)
        et.SubElement(obim, "num_zplanes").text = str(objimage.imhd.num_zpnn)
        # Don't bother outputting OBIM flags and "unknown" (probably parent),
        #  they are always 0.
        #et.SubElement(obim, "flags").text = str(objimage.imhd.flags)
        #et.SubElement(obim, "unknown").text = str(objimage.imhd.unknown)
        
        # OBCD
        obcd = et.SubElement(root, "code")
        et.SubElement(obcd, "x").text = str(objcode.cdhd.x)
        et.SubElement(obcd, "y").text = str(objcode.cdhd.y)
        et.SubElement(obcd, "width").text = str(objcode.cdhd.width)
        et.SubElement(obcd, "height").text = str(objcode.cdhd.height)
        et.SubElement(obcd, "flags").text = str(objcode.cdhd.flags)
        et.SubElement(obcd, "parent").text = str(objcode.cdhd.parent)
        et.SubElement(obcd, "walk_x").text = str(objcode.cdhd.walk_x)
        et.SubElement(obcd, "walk_y").text = str(objcode.cdhd.walk_y)
        et.SubElement(obcd, "actor_dir").text = str(objcode.cdhd.actor_dir)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "OBHD.xml"))

    def _save_order_to_xml(self, path):
        root = et.Element("order")

        obim_order = et.SubElement(root, "object-image")
        et.SubElement()

        obcd_order = et.SubElement(root, "object-code")

    
    def load_from_file(self, path):
        file_list = os.listdir(path)
        
        re_pattern = re.compile(r"[0-9]{" + str(self.OBJ_ID_LENGTH) + r"}_.*")
        object_dirs = [f for f in file_list if re_pattern.match(f) != None]
        for od in object_dirs:
            new_path = os.path.join(path, od)
            
            objimage = BlockOBIMV5(self.block_name_length, self.crypt_value)
            objimage.load_from_file(new_path)
            self.add_image_block(objimage)
            
            objcode = BlockOBCDV5(self.block_name_length, self.crypt_value)
            objcode.load_from_file(new_path)
            self.add_code_block(objcode)
            
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

        self.x = int(obim_node.find("x").text)
        self.y = int(obim_node.find("y").text)
        self.width = int(obim_node.find("width").text)
        self.height = int(obim_node.find("height").text)
        self.flags = int(obim_node.find("flags").text) # possibly wrong
        self.unknown = int(obim_node.find("unknown").text)

        self.num_imnn = int(obim_node.find("num_images").text)
        self.num_zpnn = int(obim_node.find("num_zplanes").text)

        
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
        #tree = et.parse(os.path.join(path, "header.xml"))
        tree = et.parse(path)
        root = tree.getroot()
        
        # Shared
        obj_id = int(root.find("id").text)
        self.obj_id = obj_id
        
        # OBCD
        obcd_node = root.find("code")
        self.x = int(obcd_node.find("x").text)
        self.y = int(obcd_node.find("y").text)
        self.width = int(obcd_node.find("width").text)
        self.height = int(obcd_node.find("height").text)

        self.flags = int(obcd_node.find("flags").text)
        self.parent = int(obcd_node.find("parent").text)
        self.walk_x = int(obcd_node.find("walk_x").text)
        self.walk_y = int(obcd_node.find("walk_y").text)
        self.actor_dir = int(obcd_node.find("actor_dir").text)

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
        
        self.width = int(root.find("width").text)
        self.height = int(root.find("height").text)
        self.num_objects = int(root.find("num_objects").text)
        
    def save_to_file(self, path):
        root = et.Element("room")
        
        et.SubElement(root, "width").text = str(self.width)
        et.SubElement(root, "height").text = str(self.height)
        et.SubElement(root, "num_objects").text = str(self.num_objects)
        
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
        
        self.num_zbuffers = int(root.find("num_zbuffers").text)
        
    def save_to_file(self, path):
        root = et.Element("room_image")
        
        et.SubElement(root, "num_zbuffers").text = str(self.num_zbuffers)
        
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
        global block_dispatcher
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
                block = block_dispatcher.dispatch_next_block(resource)
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
        if self.is_cd_track:
            self._write_header(resource, True)
            self._write_raw_data(resource, True)
        else:
            super(BlockSOUNV5, self).save_to_resource(resource, room_start)

    def load_from_file(self, path):
        #global file_dispatcher
        name = os.path.split(path)[1]
        if os.path.splitext(name)[1] == '':
            self.is_cd_track = False
            self.name = name.split('_')[0]
            self.index = int(name.split('_')[1])
            self.children = []
            
            file_list = os.listdir(path)
            
            file_dispatcher = FileDispatcherV5()
            for f in file_list:
                b = file_dispatcher.dispatch_next_block(f)
                if b != None:
                    b.load_from_file(os.path.join(path, f))
                    self.append(b)
        else:
            self.is_cd_track = True
            self.name = name.split('_')[0]
            self.index = os.path.splitext(name.split('_')[1])[0]
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
     
        
class BlockLFLFV5(BlockContainerV5, BlockGloballyIndexedV5):
    name = "LFLF"

    def load_from_resource(self, resource, room_start=0):
        location = resource.tell()
        #super(BlockGloballyIndexedV5, self).load_from_resource(resource, location)
        self._read_header(resource, True)
        self._read_data(resource, location, True)
        try:
            self.index = control.global_index_map.get_index(self.name, location)
        except util.ScummPackerUnrecognisedIndexException, suie:
            util.error("Block \"" 
                       + str(self.name)
                       + "\" at offset "
                       + str(location)
                       + " has no entry in the index file (.000). "
                       + "It can not be re-packed or used in the game without manually assigning an index.")
            self.is_unknown = True
            self.index = control.unknown_blocks_counter.get_next_index(self.name)    

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_start = location
        control.global_index_map.map_index(self.name, location, self.index)
        super(BlockLFLFV5, self).save_to_resource(resource, room_start)

    def save_to_file(self, path):
        util.information("Saving block " 
                         + self.name 
                         + ":" 
                         + ("unk_" if self.is_unknown else "")
                         + str(self.index).zfill(3))
        super(BlockLFLFV5, self).save_to_file(path)
    
    def load_from_file(self, path):
        #global file_dispatcher
        name = os.path.split(path)[1]
        self.name = name.split('_')[0]
        self.index = int(name.split('_')[1])
        self.children = []
        
        file_list = os.listdir(path)
        
        file_dispatcher = FileDispatcherV5()
        for f in file_list:
            b = file_dispatcher.dispatch_next_block(f)
            if b != None:
                b.load_from_file(os.path.join(path, f))
                self.append(b)

    
    def generate_file_name(self):
        return (self.name 
                + "_" 
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3))
    
    def __repr__(self):
        childstr = [str(c) for c in self.children]
        return ("[" 
                + self.name 
                + ":" 
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3) 
                + ", "
                + ", ".join(childstr)
                + "]")
    
    
class BlockLECFV5(BlockContainerV5):
    name = "LECF"

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
            #    util.debug("object " + str(c) + " has index " + str(c.index))
            #util.debug("location: " + str(resource.tell()))
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

class AbstractBlockDispatcher(object):
    CRYPT_VALUE = None
    BLOCK_NAME_LENGTH = None
    BLOCK_MAP = {}
    DEFAULT_BLOCK = None
    REGEX_BLOCKS = []
    
    def dispatch_next_block(self, resource):
        assert type(resource) is file
        block_name = resource.read(self.BLOCK_NAME_LENGTH)
        if not self.CRYPT_VALUE is None:
            block_name = util.crypt(block_name, self.CRYPT_VALUE)
        if block_name in self.BLOCK_MAP:
            block_type = self.BLOCK_MAP[block_name]            
        else:
            block_type = self._dispatch_regex_block(block_name)
            if block_type is None:
                block_type = self.DEFAULT_BLOCK
        block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        resource.seek(-self.BLOCK_NAME_LENGTH, os.SEEK_CUR)
        return block
    
    def _dispatch_regex_block(self, block_name):
        for re_pattern, block_type in self.REGEX_BLOCKS:
            if re_pattern.match(block_name) != None:
                return block_type
        return None

class AbstractFileDispatcher(AbstractBlockDispatcher):
    IGNORED_BLOCKS = frozenset([])
    
    def dispatch_next_block(self, block_name):
        if block_name in self.BLOCK_MAP:
            block_type = self.BLOCK_MAP[block_name]            
        else:
            block_type = self._dispatch_regex_block(block_name)
            if block_type is None:
                if not block_name in self.IGNORED_BLOCKS:
                    util.information("Ignoring unknown file: " + str(block_name))
                return None
        block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        return block

class BlockDispatcherV5(AbstractBlockDispatcher):
    
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        # Container blocks
        "LFLF" : BlockLFLFV5, # also indexed
        "ROOM" : BlockROOMV5, # also indexed (kind of)
        "RMIM" : BlockContainerV5,
        "SOUN" : BlockSOUNV5, # also sound (kind of)
        "OBIM" : BlockOBIMV5,
        "OBCD" : BlockOBCDV5,
        "LECF" : BlockLECFV5,
        
        # Sound blocks
        "SOU " : BlockSOUV5,
        "ROL " : BlockMIDISoundV5,
        "SPK " : BlockMIDISoundV5,
        "ADL " : BlockMIDISoundV5,
        "SBL " : BlockSBLV5,
        
        # Globally indexed blocks
        "COST" : BlockGloballyIndexedV5,
        "CHAR" : BlockGloballyIndexedV5,
        "SCRP" : BlockGloballyIndexedV5,
        "SOUN" : BlockSOUNV5,
        
        # Other blocks that should not used default block functionality
        "IMHD" : BlockIMHDV5,
        "LSCR" : BlockLSCRV5,
        "RMHD" : BlockRMHDV5,
        "RMIH" : BlockRMIHV5,
        "LOFF" : BlockLOFFV5
        
    }
    REGEX_BLOCKS = [
        (re.compile(r"IM[0-9]{2}"), BlockContainerV5)
    ]
    DEFAULT_BLOCK = BlockDefaultV5

class FileDispatcherV5(AbstractFileDispatcher):
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        # Root
        r"LECF" : BlockLECFV5,
        # LECF
        # -LFLF
        r"ROOM" : BlockROOMV5,
        # --ROOM
        r"BOXD.dmp" : BlockDefaultV5,
        r"BOXM.dmp" : BlockDefaultV5,
        r"CLUT.dmp" : BlockDefaultV5,
        r"CYCL.dmp" : BlockDefaultV5,
        r"EPAL.dmp" : BlockDefaultV5,
        r"SCAL.dmp" : BlockDefaultV5,
        r"TRNS.dmp" : BlockDefaultV5,
        r"RMHD.xml" : BlockRMHDV5,
        r"RMIM" : BlockContainerV5,
        r"objects" : ObjectBlockContainer,
        r"scripts" : ScriptBlockContainer,
        # ---RMIM
        r"RMIH.xml" : BlockRMIHV5,
        # ---objects (incl. subdirs)
        r"VERB.dmp" : BlockDefaultV5,
        r"SMAP.dmp" : BlockDefaultV5, # also RMIM
        r"BOMP.dmp" : BlockDefaultV5, # room 99, object 1045 in MI1 CD.
        # ---scripts
        r"ENCD.dmp" : BlockDefaultV5,
        r"EXCD.dmp" : BlockDefaultV5,
        # - Sound blocks
        r"SOU" : BlockSOUV5,
        r"ROL.mid" : BlockMIDISoundV5,
        r"SPK.mid" : BlockMIDISoundV5,
        r"ADL.mid" : BlockMIDISoundV5,
        r"SBL.voc" : BlockSBLV5,
        
    }
    REGEX_BLOCKS = [
        # LECF
        (re.compile(r"LFLF_[0-9]{3}.*"), BlockLFLFV5),
        # -LFLF
        (re.compile(r"SOUN_[0-9]{3}(?:\.dmp)?"), BlockSOUNV5),
        (re.compile(r"CHAR_[0-9]{3}"), BlockGloballyIndexedV5),
        (re.compile(r"COST_[0-9]{3}"), BlockGloballyIndexedV5),
        (re.compile(r"SCRP_[0-9]{3}"), BlockGloballyIndexedV5),
        # --ROOM
        # ---objects
        (re.compile(r"IM[0-9a-fA-F]{2}"), BlockContainerV5), # also RMIM
        (re.compile(r"ZP[0-9a-fA-F]{2}\.dmp"), BlockDefaultV5), # also RMIM
        # --scripts
        (re.compile(r"LSCR_[0-9]{3}\.dmp"), BlockLSCRV5)
    ]
    IGNORED_BLOCKS = frozenset([
        r"ROL.mhd",
        r"SPK.mhd",
        r"ADL.mhd",
        r"SBL.mhd"
    ])
    DEFAULT_BLOCK = BlockDefaultV5

class IndexFileDispatcherV5(AbstractFileDispatcher):
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        #r"maxs\.xml" : BlockMAXSV5,
        #r"roomnames\.xml" : BlockRNAMV5,
        #r"DOBJ\.dmp" : BlockDOBJV5,
        #r"DROO\.dmp" : BlockDefaultV5
    }
    REGEX_BLOCKS = [
    ]
    DEFAULT_BLOCK = BlockDefaultV5

class BlockRNAMV5(BlockDefaultV5):
    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        self.room_names = []
        while resource.tell() < end:
            room_no = util.str_to_int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            if room_no == 0: # end of list marked by 0x00
                break
            room_name = resource.read(9)
            if decrypt:
                room_name = util.crypt(room_name, self.crypt_value)
            room_name = util.crypt(room_name, 0xFF).rstrip("\x00")
            self.room_names.append((room_no, room_name))
            control.global_index_map.map_index(self.name, room_no, room_name)
            
    def save_to_file(self, path):
        root = et.Element("room_names")
        
        for room_no, room_name in self.room_names:
            room = et.SubElement(root, "room")
            et.SubElement(room, "id").text = str(room_no)
            et.SubElement(room, "name").text = util.escape_invalid_chars(room_name)
        
        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "roomnames.xml"))
        

class BlockMAXSV5(BlockDefaultV5):
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
        
        et.SubElement(root, "variables").text = str(self.num_vars)
        et.SubElement(root, "unknown_1").text = str(self.unknown_1)
        et.SubElement(root, "bit_variables").text = str(self.bit_vars)
        et.SubElement(root, "local_objects").text = str(self.local_objects)
        et.SubElement(root, "unknown_2").text = str(self.unknown_2)
        et.SubElement(root, "character_sets").text = str(self.char_sets)
        et.SubElement(root, "unknown_3").text = str(self.unknown_3)
        et.SubElement(root, "unknown_4").text = str(self.unknown_4)
        et.SubElement(root, "inventory_objects").text = str(self.inventory_objects)
        
        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "maxs.xml"))
      
class BlockIndexDirectoryV5(BlockDefaultV5):
    DIR_TYPES = {
        "DROO" : "ROOM",
        "DSCR" : "SCRP",
        "DSOU" : "SOUN",
        "DCOS" : "COST",
        "DCHR" : "CHAR"
        #"DOBJ" : "OBCD"
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
        pass
            
class BlockDOBJV5(BlockDefaultV5):
    def _read_data(self, resource, start, decrypt):
        num_items = util.str_to_int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        self.objects = []
        i = num_items
        while i > 0:
            owner_and_state = util.str_to_int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            owner = (owner_and_state & 0xF0) >> 4
            state = owner_and_state & 0x0F
            self.objects.append((owner, state))
            i -= 1
            
    def load_from_file(self, path):
        tree = et.parse(path)
        
        self.objects = []
        for obj_node in tree.getiterator("object-entry"):
            obj_id = int(obj_node.find("id").text)
            assert obj_id == len(self.objects), "Entries in object ID must be in sorted order with no gaps in ID numbering."
            owner = int(obj_node.find("owner").text)
            state = int(obj_node.find("state").text)
            self.objects.append((owner, state))

    def save_to_file(self, path):
        root = et.Element("object-directory")

        for i in xrange(len(self.objects)):
            owner, state = self.objects[i]
            obj_node = et.SubElement(root, "object-entry")
            et.SubElement(obj_node, "id").text = str(i)
            et.SubElement(obj_node, "owner").text = str(owner)
            et.SubElement(obj_node, "state").text = str(state)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "dobj.xml"))

    def save_to_resource(self, resource, room_start=0):
        pass

class BlockDROOV5(BlockDefaultV5):
    """Directory of offsets to ROOM blocks."""
    def save_to_file(self, path):
        """This block is generated when saving to a resource."""
        return

    def save_to_resource(self, resource, room_start=0):
        pass

class IndexBlockContainerV5(AbstractBlockDispatcher):
    """Resource.000 processor; just maps blocks to Python objects (POPOs?)."""
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        "RNAM" : BlockRNAMV5,
        "MAXS" : BlockMAXSV5,
        "DROO" : BlockDROOV5,
        "DSCR" : BlockIndexDirectoryV5,
        "DSOU" : BlockIndexDirectoryV5,
        "DCOS" : BlockIndexDirectoryV5,
        "DCHR" : BlockIndexDirectoryV5,
        "DOBJ" : BlockDOBJV5
    }
    REGEX_BLOCKS = []
    DEFAULT_BLOCK = BlockDefaultV5
    
    def load_from_resource(self, resource, room_start=0):
        self.children = []
        for i in xrange(8):
            block = self.dispatch_next_block(resource)
            block.load_from_resource(resource)
            self.children.append(block)
            
    def save_to_file(self, path):
        for c in self.children:
            c.save_to_file(path)
        
    
def __test_unpack():
    global block_dispatcher
    
    #outpath = os.getcwd()
    outpath = "D:\\TEMP"
    
    dirfile = file("MONKEY.000", "rb")
    dir_block = IndexBlockContainerV5()
    dir_block.load_from_resource(dirfile)
    dirfile.close()
    
    dir_block.save_to_file(outpath)
    
    block_dispatcher = BlockDispatcherV5()
    resfile = file("MONKEY.001", "rb")
    block = BlockLECFV5(4, 0x69)
    block.load_from_resource(resfile)
    #print block
    resfile.close()
    
    block.save_to_file(outpath)

def __test_unpack_from_file():
    global file_dispatcher

    #outpath = os.getcwd()
    outpath = "D:\\TEMP"

    inpath = os.path.join(outpath, "LECF")
    block = BlockLECFV5(4, 0x69)
    block.load_from_file(inpath)

    #print block
    util.information("read from file, now saving to file")

    outpath = os.path.join(outpath, "outtest")
    if not os.path.isdir(outpath):
        os.mkdir(outpath)
    block.save_to_file(outpath)

def __test_pack():
    global file_dispatcher

    #outpath = os.getcwd()
    outpath = "D:\\TEMP"
    
    inpath = os.path.join(outpath, "LECF")
    block = BlockLECFV5(4, 0x69)
    block.load_from_file(inpath)
    
    #print block
    util.information("read from file, now saving to resource")
    
    #outpath = os.path.join(outpath, "outtest")
    #os.mkdir(outpath)
    
    #block.save_to_file(outpath)

    outpath = os.path.join(outpath, "outres.001")
    with file(outpath, 'wb') as outres:
        block.save_to_resource(outres)

def __test():
    #__test_unpack()
    #__test_unpack_from_file()
    __test_pack()
    
if __name__ == "__main__": __test()
