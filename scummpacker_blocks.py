import array
import os
import re
import struct
import xml.etree.ElementTree as et
import scummpacker_control as control
import scummpacker_util as util

block_order_index_v5 = [
    
]
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
      "SMAP"
      "ZP" # ZPxx
    "OBIM",
     #Inside OBIM
     "IMHD",
     "IM",
      #Inside IMxx
      "SMAP"
      "ZP" # ZPxx
    "OBCD",
     #Inside OBCD
     "CDHD",
     "VERB",
     "OBNA",
    "EXCD",
    "ENCD",
    "NLSC",
    "LSCR",
    
    # Inside LFLF
    "SCRP",
    "SOUN",
    "COST",
    "CHAR"
]

block_dispatcher = None

class AbstractBlock(object):
    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        super(AbstractBlock, self).__init__(*args, **kwds)
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
    
    def load_from_resource(self, resource, room_start=0):
        start = resource.tell()
        self._read_header(resource, True)
        self._read_data(resource, start, True)

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
        self._read_header(block_file, True)
        self._read_data(block_file, start, True)
        block_file.close()

    def save_to_file(self, path):
        outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
        self._write_header(outfile, False)
        self._write_data(outfile, False)
        outfile.close()

    def _write_header(self, outfile, encrypt):
        # Different in old format resources
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


class BlockSoundV5(BlockDefaultV5):
    """ Sound blocks store incorrect block size (it doesn't include the SOU/ADL/SBL header size)"""
    def _read_size(self, resource, decrypt):
        size = resource.read(4)
        if decrypt:
            size = util.crypt(size, self.crypt_value)
        return util.str_to_int(size, is_BE=util.BE) + 8
    
    def _write_header(self, outfile, encrypt):
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)
        size = util.int_to_str(self.size - 8, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
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
        
    def generate_file_name(self):
        return self.name
    
    def __repr__(self):
        childstr = [str(c) for c in self.children]
        return "[" + self.name + ", " + ", ".join(childstr) + "]"

class BlockMIDISoundV5(BlockSoundV5):
    """ Saves the MDhd header data to a .mhd file, saves the rest of the block 
    to a .mid file."""
    MDHD_SIZE = 16
    
    #def load_from_file(self, path):
    #    mdhd_file = file(self.name + "")
    
    def save_to_file(self, path):
        # Possibly the only MDhd block that is different:
        # MI1CD\LECF\LFLF_011\SOUN_043\SOU
        # 4D44 6864 0000 0008 0000 FF7F 0000 0080
        outfile = file(os.path.join(path, self.generate_file_name() + ".mhd"), 'wb')
        self._write_mdhd_header(outfile, False)
        outfile.close()
        outfile = file(os.path.join(path, self.generate_file_name() + ".mid"), 'wb')
        self._write_data(outfile, False)
        outfile.close()
    
    def _read_header(self, resource, decrypt):
        super(BlockMIDISoundV5, self)._read_header(resource, decrypt)
        self.mdhd_header = self._read_raw_data(resource, self.MDHD_SIZE, decrypt)
    
    def _write_mdhd_header(self, outfile, encrypt):
        outfile.write(util.crypt(self.mdhd_header, (self.crypt_value if encrypt else None)))

class BlockSOUV5(BlockSoundV5, BlockContainerV5):
    pass

class BlockSBLV5(BlockSoundV5):
    AU_HEADER = "AUhd\x00\x00\x00\x03\x00\x00\x80AUdt"
    
    def _read_data(self, resource, start, decrypt):
        # SBL blocks have AUhd and AUdt headers instead of
        #  "Creative Voice File".
        # Skip AUhd/AUdt and just read the rest of the raw data,
        #  we can regenerate the header later.
        resource.seek(19, os.SEEK_CUR)
        super(BlockSBLV5, self)._read_data(resource, start, decrypt)

    def load_from_file(self, path):
        # TODO: open file etc
        voc_file = file(os.path.join(path, "SBL.voc"), 'rb')
        self.size = len(voc_file) - 0x1A + 27 # ignore VOC header, add SBL block header (could just +1)
        voc_file.seek(0x1A, os.SEEK_CUR)
        self._read_raw_data(voc_file, 0, False)
        voc_file.close()
        
    def save_to_file(self, path):
        outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
        self._write_VOC_header(outfile, False)
        self._write_data(outfile, False)
        outfile.close()

    def save_to_resource(self, resource):
        self._write_header(resource, True)
        self._write_AUhd_header(resource, True)
        self._write_data(resource, True)
        
    def _write_AUhd_header(self, outfile, encrypt):
        voc_size = self.size - 27 # ignore all header info for size
        au_header = AU_HEADER + util.str_to_int(voc_size, is_BE=True)
        au_header = (util.crypt(au_header if encrypt else au_header))
        outfile.write(au_header)
        
    def _write_VOC_header(self, outfile, encrypt):
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
        object_container = ObjectBlockContainer()
        script_container = ScriptBlockContainer()
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
    
class BlockLOFFV5(BlockDefaultV5):
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
        pass

class ScriptBlockContainer(object):
    def __init__(self):
        self.scripts = []
    
    def append(self, block):
        self.scripts.append(block)
    
    def save_to_file(self, path):
        newpath = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(newpath):
            os.mkdir(newpath) # throws an exception if can't create dir
        for s in self.scripts:
            s.save_to_file(newpath)
        
    def generate_file_name(self):
        return "scripts"
    
    def __repr__(self):
        childstr = [str(c) for c in self.scripts]
        return "[Scripts, " + ", ".join(childstr) + "]"


class BlockLSCRV5(BlockDefaultV5):
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
    """ Contains objects, which contain image and code blocks."""
    def __init__(self):
        self.objects = {}
    
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
            newpath = os.path.join(objects_path, str(objcode.obj_id) + "_" + util.discard_invalid_chars(objcode.obj_name))
            if not os.path.isdir(newpath):
                os.mkdir(newpath) # throws an exception if can't create dir
            objimage.save_to_file(newpath)
            objcode.save_to_file(newpath)
            self._save_header_to_xml(newpath, objimage, objcode)

    def _save_header_to_xml(self, path, objimage, objcode):
        # Save the joined header information as XML
        root = et.Element("object")
    
        #shared = et.SubElement(root, "shared")
        et.SubElement(root, "name").text = util.escape_invalid_chars(objcode.obj_name)
        et.SubElement(root, "id").text = str(objcode.obj_id)
        et.SubElement(root, "x").text = str(objcode.cdhd.x)
        et.SubElement(root, "y").text = str(objcode.cdhd.y)
        et.SubElement(root, "width").text = str(objcode.cdhd.width)
        et.SubElement(root, "height").text = str(objcode.cdhd.height)
        
        # OBIM
        obim = et.SubElement(root, "image")
        et.SubElement(obim, "num_images").text = str(objimage.imhd.num_imnn)
        et.SubElement(obim, "num_zplanes").text = str(objimage.imhd.num_zpnn)
        # Don't bother outputting OBIM flags and "unknown" (probably parent),
        #  they are always 0.
        #et.SubElement(obim, "flags").text = str(objimage.imhd.flags)
        #et.SubElement(obim, "unknown").text = str(objimage.imhd.unknown)
        
        # OBCD
        obcd = et.SubElement(root, "code")
        et.SubElement(obcd, "flags").text = str(objcode.cdhd.flags)
        et.SubElement(obcd, "parent").text = str(objcode.cdhd.parent)
        et.SubElement(obcd, "walk_x").text = str(objcode.cdhd.walk_x)
        et.SubElement(obcd, "walk_y").text = str(objcode.cdhd.walk_y)
        et.SubElement(obcd, "actor_dir").text = str(objcode.cdhd.actor_dir)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "header.xml"))

    
    def load_from_file(self, path):
        file_list = os.listdir(path)
        
        re_pattern = re.compile(r"[0-9]{3}_.*")
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
        block.load_from_file(path)
        self.obj_id = block.obj_id
        self.imhd = block
        
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
        num hotspots : 16le (usually one for each IMnn, but their is one even
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
        tree = et.parse(os.path.join(path, "header.xml"))
        root = tree.getroot()
        
        # Shared
        self.obj_id = int(root.find("id").text)
        self.x = int(root.find("x").text)
        self.y = int(root.find("y").text)
        self.width = int(root.find("width").text)
        self.height = int(root.find("height").text)

        # OBIM
        obim_node = root.find("image")
        self.num_imnn = int(obim_node.find("num_images").text)
        self.num_zpnn = int(obim_node.find("num_zplanes").text)
        
        # OBCD
        obcd_node = root.find("code")
        self.flags = int(obcd_node.find("flags").text) # possibly wrong
        self.unknown = int(obcd_node.find("parent").text) # almost certainly wrong
        
    def save_to_file(self, path):
        """ Combined header.xml is saved in the ObjectBlockContainer."""
        pass

    
class BlockOBCDV5(BlockContainerV5):
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
        
        self.obj_name = self.obna.data[:-1].tostring() # cheat

    def load_from_file(self, path):
        block = BlockCDHDV5(self.block_name_length, self.crypt_value)
        block.load_from_file(path)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.cdhd = block
        
        block = BlockDefaultV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "VERB.dmp")) # hmm
        self.verb = block
        
        block = BlockOBNAV5(self.block_name_length, self.crypt_value)
        block.load_from_file(path)
        self.obna = block
        
        self.obj_name = self.obna.data[:-1].tostring() # cheat
        
    def save_to_file(self, path):
        self.verb.save_to_file(path)
        
    def generate_file_name(self):
        return str(self.obj_id) + "_" + self.obj_name
    
class BlockOBNAV5(BlockDefaultV5):
    def _read_data(self, resource, start, decrypt):
        data = resource.read(self.size - (resource.tell() - start))
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        self.obj_name = data[:-1]
        
    def load_from_file(self, path):
        self.name = "OBNA"
        self._load_header_from_xml(path)
        self.size = len(self.obj_name) + 8
    
    def _load_header_from_xml(self, path):
        tree = et.parse(os.path.join(path, "header.xml"))
        root = tree.getroot()
        
        # Shared
        self.obj_name = util.unescape_invalid_chars(root.find("name").text)
        
    #def save_to_resource(self, path):
    #    write object name + "\x00"
    
class BlockCDHDV5(BlockDefaultV5):
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
        tree = et.parse(os.path.join(path, "header.xml"))
        root = tree.getroot()
        
        # Shared
        obj_id = int(root.find("id").text)
        self.obj_id = obj_id
        self.x = int(root.find("x").text)
        self.y = int(root.find("y").text)
        self.width = int(root.find("width").text)
        self.height = int(root.find("height").text)
        
        # OBCD
        obcd_node = root.find("code")
        self.flags = int(obcd_node.find("flags").text)
        self.parent = int(obcd_node.find("parent").text)
        self.walk_x = int(obcd_node.find("walk_x").text)
        self.walk_y = int(obcd_node.find("walk_y").text)
        self.actor_dir = int(obcd_node.find("actor_dir").text)
        
class BlockRMHDV5(BlockDefaultV5):
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
        
    def save_to_file(self, path):
        root = et.Element("room")
        
        et.SubElement(root, "width").text = str(self.width)
        et.SubElement(root, "height").text = str(self.height)
        et.SubElement(root, "num_objects").text = str(self.num_objects)
        
        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "header.xml"))

class BlockRMIHV5(BlockDefaultV5):
    def _read_data(self, resource, start, decrypt):
        """
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
        
    def save_to_file(self, path):
        root = et.Element("room_image")
        
        et.SubElement(root, "num_zbuffers").text = str(self.num_zbuffers)
        
        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "header.xml"))
        
        
class BlockSOUNV5(BlockContainerV5, BlockGloballyIndexedV5):
    """ SOUN blocks in V5 may contain CD track data. Unfortunately, these CD
    blocks have no nice header value to look for. Instead, we have to check
    the file size somehow."""
    
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
    
    def save_to_file(self, path):
        util.information("Saving block " 
                         + self.name 
                         + ":" 
                         + ("unk_" if self.is_unknown else "")
                         + str(self.index).zfill(3))
        super(BlockLFLFV5, self).save_to_file(path)
    
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

class FileDispatcherV5(AbstractBlockDispatcher):
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
        #r"header\.xml" : BlockRMHDV5, # this could be any header
        r"RMIM" : BlockContainerV5,
        r"objects" : ObjectBlockContainer,
        r"scripts" : ScriptBlockContainer
        # ---objects (incl. subdirs)
        r"VERB.dmp" : BlockDefaultV5,
        r"SMAP.dmp" : BlockDefaultV5, # also RMIM
        # ---scripts
        r"ENCD.dmp" : BlockDefaultV5,
        r"EXCD.dmp" : BlockDefaultV5,
    }
    REGEX_BLOCKS = [
        # LECF
        (re.compile(r"LFLF_[0-9]{3}.*"), BlockLFLFV5),
        # -LFLF
        (re.compile(r"SOUN_[0-9]{3}(?:\.dmp)?"), BlockSOUNV5),
        (re.compile(r"CHAR_[0-9]{3}"), BlockGloballyIndexedV5),
        (re.compile(r"COST_[0-9]{3}"), BlockGloballyIndexedV5),
        (re.compile(r"SCRP_[0-9]{3}"), BlockDefaultV5)
        # --ROOM
        # ---objects
        (re.compile(r"IM[0-9a-fA-F]{2}"), BlockContainerV5), # also RMIM
        (re.compile(r"ZP[0-9a-fA-F]{3}\.dmp"), BlockDefaultV5), # also RMIM
        # --scripts
        (re.compile(r"LSCR_[0-9]{3}\.dmp"), blocks.BlockLSCRV5)
    ]
    DEFAULT_BLOCK = BlockDefaultV5

class IndexFileDispatcherV5(AbstractBlockDispatcher):
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        r"maxs\.xml" : blocks.BlockMAXSV5,
        r"roomnames\.xml" : blocks.BlockRNAMV5,
        r"DOBJ\.dmp" : blocks.BlockDOBJV5,
        r"DROO\.dmp" : blocks.BlockDefaultV5
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
        pass
            
class BlockDOBJV5(BlockDefaultV5):
    pass

class IndexBlockContainerV5(AbstractBlockDispatcher):
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        "RNAM" : BlockRNAMV5,
        "MAXS" : BlockMAXSV5,
        "DROO" : BlockDefaultV5,
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
        
    
def __test():
    global block_dispatcher
    
    outpath = os.getcwd()
    
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
    
if __name__ == "__main__": __test()
