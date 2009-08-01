import array
import os
import re
import struct
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
    
    def load_from_resource(self, resource):
        start = resource.tell()
        self._read_header(resource, True)
        self._read_data(resource, start, True)

    def _read_header(self, resource):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start, decrypt):
        data = self._read_raw_data(resource, self.size - (resource.tell() - start))
        if decrypt:
            data = util.crypt(data, self.crypt_value)
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
    
    def _read_raw_data(self, resource, size):
        data = array.array('B')
        data.fromfile(resource, size)
        return data

    def save_to_file(self, path):
        outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
        self._write_header(outfile, path, False)
        self._write_data(outfile, path, False)
        outfile.close()

    def _write_header(self, outfile, path, encrypt):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _write_data(self, outfile, path, encrypt):
        self._write_raw_data(outfile, path, encrypt)

    def _write_raw_data(self, outfile, path, encrypt):
        if encrypt:
            for i, b in enumerate(self.data):
                self.data[i] = util.crypt(b, self.crypt_value)
        self.data.tofile(outfile)
        
    def generate_file_name(self):
        return self.name + ".dmp"
    
    def __repr__(self):
        return "[" + self.name + "]"


class BlockDefaultV5(AbstractBlock):
    def _read_header(self, resource, decrypt):
        # Should be reversed for old format resources
        self.name = self._read_name(resource, decrypt)
        self.size = self._read_size(resource, decrypt)

    def _write_header(self, outfile, path, encrypt):
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
    
    def _write_header(self, outfile, path, encrypt):
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)
        size = util.int_to_str(self.size - 8, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)
    
    def generate_file_name(self):
        return self.name.rstrip() + ".dmp"

class BlockGloballyIndexedV5(BlockDefaultV5):
    def __init__(self, *args, **kwds):
        super(BlockGloballyIndexedV5, self).__init__(*args, **kwds)
        self.index = None
        self.is_unknown = False
    
    def load_from_resource(self, resource):
        location = resource.tell()
        super(BlockGloballyIndexedV5, self).load_from_resource(resource)
        try:
            self.index = control.global_index_map.get_index(self.name, location)
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
            block.load_from_resource(resource)
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

class BlockSOUV5(BlockContainerV5, BlockSoundV5):
    def generate_file_name(self):
        return self.name.rstrip()

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
            control.global_index_map.map_index("ROOM", room_offset, room_no)

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
        data = self._read_raw_data(resource, self.size - (resource.tell() - start))
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        self.data = data
        
    def _write_data(self, outfile, path, encrypt):
        script_num = util.int_to_str(self.script_id, numBytes=1)
        if encrypt:
            script_num = util.crypt(script_num, self.crypt_value)
        outfile.write(script_num)
        self._write_raw_data(outfile, path, encrypt)
        
    def generate_file_name(self):
        return self.name + "_" + str(self.script_id).zfill(3) + ".dmp"
        

class ObjectBlockContainer(object):
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
        newpath = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(newpath):
            os.mkdir(newpath) # throws an exception if can't create dir
        for objimage, objcode in self.objects.values():
            objimage.save_to_file(newpath)
            objcode.save_to_file(newpath)
        
    def generate_file_name(self):
        return "objects"
    
    def __repr__(self):
        childstr = ["obj_" + str(c) for c in self.objects.keys()]
        return "[OBIM & OBCD, " + "[" + ", ".join(childstr) + "] " + "]"
    
    
class BlockOBIMV5(BlockContainerV5):
    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        block = BlockIMHDV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.imhd = block
        i = block.num_imnn
        while i > 0:
            block = BlockContainerV5(self.block_name_length, self.crypt_value)
            block.load_from_resource(resource)
            self.append(block)
            i -= 1
    
    def generate_file_name(self):
        return str(self.obj_id)
    
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
        
        not sure about the following:
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
        
        block = BlockDefaultV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obna = block
        
        self.obj_name = self.obna.data[:-1].tostring() # cheat
    
    def generate_file_name(self):
        return str(self.obj_id)
    
    
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
            self.parent, self.walk_x, self.walk_y, self._actor_dir = values
        del values
        
        
class BlockSOUNV5(BlockContainerV5, BlockGloballyIndexedV5):
    def _read_data(self, resource, start, decrypt):
        global block_dispatcher
        if self.size == 32:
            self.data = self._read_raw_data(resource, self.size - (resource.tell() - start))
        else:
            end = start + self.size
            while resource.tell() < end:
                block = block_dispatcher.dispatch_next_block(resource)
                block.load_from_resource(resource)
                self.append(block)
                
    def save_to_file(self, path):
        if self.size == 32:
            outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
            self._write_header(outfile, path, False)
            self._write_raw_data(outfile, path, False)
            outfile.close()
        else:
            newpath = self._create_directory(path)
            self._save_children(newpath)
                
    def generate_file_name(self):
        name = (self.name 
                + "_" 
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3))
        if self.size == 32:
            return name + ".dmp"
        else:
            return name
     
        
class BlockLFLFV5(BlockContainerV5, BlockGloballyIndexedV5):
    #self.room_name
##    def generate_file_name(self):
##        return self.name + "_" + str(self.index).zfill(3) + "_" + self.room_name
    
##    def load_from_resource(self, resource):
##        location = resource.tell()
##        super(BlockGloballyIndexedV5, self).load_from_resource(resource)
##        self.is_unknown = self.children[0].is_unknown
##        self.index = self.children[0].index
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
    BLOCK_MAP = None
    DEFAULT_BLOCK = None
    
    def dispatch_next_block(self, resource):
        assert type(resource) is file
        block_name = resource.read(self.BLOCK_NAME_LENGTH)
        if not self.CRYPT_VALUE is None:
            block_name = util.crypt(block_name, self.CRYPT_VALUE)
        if block_name in self.BLOCK_MAP:
            block_type = self.BLOCK_MAP[block_name]            
        elif self._is_quirky_block(block_name):
            block_type = self._dispatch_quirky_block(block_name)
        else:
            block_type = self.DEFAULT_BLOCK
        block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        resource.seek(-self.BLOCK_NAME_LENGTH, os.SEEK_CUR)
        return block

    def _is_quirky_block(self, block_name):
        return False
    
    def _dispatch_quirky_block(self, block_name):
        raise NotImplementedError("This method must be overriden by a concrete class if required.")
    
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
        "ROL " : BlockSoundV5,
        "SPK " : BlockSoundV5,
        "ADL " : BlockSoundV5,
        "SBL " : BlockSoundV5,
        
        # Globally indexed blocks
        "COST" : BlockGloballyIndexedV5,
        "CHAR" : BlockGloballyIndexedV5,
        "SCRP" : BlockGloballyIndexedV5,
        "SOUN" : BlockSOUNV5,
        
        # Other special blocks
        "IMHD" : BlockIMHDV5,
        "LSCR" : BlockLSCRV5,
        "LOFF" : BlockLOFFV5
        
    }
    DEFAULT_BLOCK = BlockDefaultV5
    
    def _is_quirky_block(self, block_name):
        re_pattern = re.compile("IM[0-9]{2}")
        if re_pattern.match(block_name) != None:
            return True
        return False
    
    def _dispatch_quirky_block(self, block_name):
        re_pattern = re.compile("IM[0-9]{2}")
        if re_pattern.match(block_name) != None:
            return BlockContainerV5
        raise util.ScummPackerException("Tried to dispatch apparently known quirky block \"" 
                                        + block_name 
                                        + "\", but I don't know what to do with it!")

#class IndexFileReader(AbstractBlockReader):
#    def dispatch_next_block(self, resource, path):
#        pass
    
    
def __test():
    global block_dispatcher
    block_dispatcher = BlockDispatcherV5()
    resfile = file("MONKEY.001", "rb")
    block = BlockLECFV5(4, 0x69)
    block.load_from_resource(resfile)
    print block
    resfile.close()
    
    block.save_to_file(os.getcwd())
    
if __name__ == "__main__": __test()
