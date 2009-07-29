import array
import os
import struct
import scummpacker_control as control
import scummpacker_util as util


class AbstractBlock(object):
    def __init__(self, block_name_length, crypt_value):
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
    
    def load_from_resource(self, resource):
        start = resource.tell()
        self._read_header(resource)
        self._read_data(resource, start)

    def _read_header(self, resource):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start):
        self.data = util.crypt(self._read_raw_data(resource, self.size - self.block_name_length - 4), self.crypt_value)
        
    def _read_name(self, resource):
        return resource.read(self.block_name_length)
    
    def _read_size(self, resource):
        return util.str_to_int(resource.read(4), util.BE)
    
    def _read_raw_data(self, resource, size):
        data = array.array('B')
        data.fromfile(resource, size)
        return data

    def save_to_file(self, path):
        outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
        self._write_header(outfile, path)
        self._write_data(outfile, path)
        outfile.close()

    def _write_header(self, outfile, path):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _write_data(self, outfile, path):
        self._write_raw_data(self, outfile, path)

    def _write_raw_data(self, outfile, path, encrypt):
        if encrypt:
            for i, b in enumerate(self.data):
                self.data[i] = util.crypt(b, self.crypt_value)
        self.data.tofile(outfile)
        
    def generate_file_name(self):
        return self.name + ".dmp"


class BlockDefaultV5(AbstractBlock):
    def _read_header(self, resource):
        # Should be reversed for old format resources
        self.name = util.crypt(self._read_name(resource), self.crypt_value)
        self.size = util.crypt(self._read_size(resource), self.crypt_value)

    def _write_header(self, outfile, path):
        outfile.write(util.crypt(self.name, self.crypt_value))
        outfile.write(util.crypt_value(util.int_to_str(self.size, util.BE), self.crypt_value))


class BlockSoundV5(BlockDefaultV5):
    pass


class BlockGloballyIndexedV5(BlockDefaultV5):
    def __init__(self, *args):
        super(BlockGloballyIndexedV5, self).__init__(args)
        self.index = None
    
    def load_from_resource(self, resource):
        location = resource.tell()
        super(BlockIndexedV5, self).load_from_resource(resource)
        self.index = control.global_index_map.get_index(self.name, location)
        
    def generate_file_name(self):
        return self.name + "_" + str(self.index).zfill(3) + ".dmp"

    
class BlockContainerV5(BlockDefaultV5):
    def __init__(self, *args):
        super(BlockContainerV5, self).__init__(args)
        self.children = []
    
    def _read_data(self, resource, start):
        end = start + self.size
        while resource.tell() < end:
            block = BlockDispatcherV5.dispatch_next_block(resource)
            block.loadFromResource(resource)
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


class BlockROOM(BlockContainerV5): # also globally indexed
    def __init__(self, *args):
        super(BlockContainerV5, self).__init__(args)
        self.index = None
        self.script_types = frozenset(["ENCD", 
                                       "EXCD",
                                       "LSCR"])
        self.object_types = frozenset(["OBIM",
                                       "OBCD"])
        
    def _read_data(self, resource, start):
        self.index = control.global_index_map.get_index(self.name, start)
        end = start + self.size
        object_container = ObjectBlockContainer()
        script_container = ScriptBlockContainer()
        while resource.tell() < end:
            block = BlockDispatcherV5.dispatch_next_block(resource)
            block.loadFromResource(resource)
            if block.name in self.script_types:
                script_container.append(block)
            elif block.name == "OBIM":
                object_container.set_image_block(block)
            elif block.name == "OBCD":
                object_container.set_code_block(block)
            elif block.name == "NLSC": # ignore this since we can generate it
                del block
                continue
            else:
                self.append(block)
        self.append(object_container)
        self.append(script_container)

    
class BlockLFLF(BlockContainerV5):
    #self.room_name
    def generate_file_name(self):
        return self.name + "_" + str(self.index).zfill(3) + "_" + self.room_name
    
    
class BlockLOFF(BlockGloballyIndexedV5):
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


class BlockLSCRV5(BlockDefaultV5):
    def _read_data(self, resource, start):
        

class ObjectBlockContainer(object):
    def __init__(self):
        self.objects = {}
    
    def set_code_block(self, block):
        if not block.obj_id in self.objects:
            self.objects[block.obj_id] = [None, None] # pos1 = image, pos2 = code
        self.objects[block.obj_id][1] = block

    def set_image_block(self, block):
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
    
    
class BlockOBIM(BlockContainerV5):
    def _read_data(self, resource, start):
        end = start + self.size
        block = BlockIMHDV5(self.block_name_length, self.crypt_value)
        block.loadFromResource(resource)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.imhd = block
        i = block.num_inn
        while i > 0:
            block = BlockContainerV5(self.block_name_length, self.crypt_value)
            block.load_from_resource(resource)
            self.append(block)
            i -= 1
    
    def generate_file_name(self):
        return self.obj_id

    
class BlockIMHDV5(BlockDefaultV5):
    def _read_data(self, resource, start):
        """
        obj id       : 16le
        num imnn     : 16le
        num zpnn     : 16le (per IMnn block)
        unknown      : 16
         ^ (ScummVM object.h seems to think the first byte is flags)
        x            : 16le
        y            : 16le
        width        : 16le
        height       : 16le
        num hotspots : 16le (usually one for each IMnn, but their is one even
                       if no IMnn is present)
        hotspots
          x          : 16le signed
          y          : 16le signed
        """

        values = struct.unpack("<3H2B5H", util.crypt(resource.read(18), self.crypt_value))
        
        # Unpack the values 
        self.obj_id, self.num_imnn, self.num_zpnn, self.flags, self.unknown, \
            self.x, self.y, self.width, self.height, self.num_hotspots = values
        
        # Read the hotspots
##        i = self.num_hotspots
##        self.hotspots = []
##        while i > 0:
##            hotspot_pos = struct.unpack("<2h", util.crypt(resource.read(4), self.crypt_value))
##            self.hotspots.append(hotspot_pos)
##            i -= 1

    
class AbstractBlockDispatcher(object):
    CRYPT_VALUE = None
    BLOCK_NAME_LENGTH = None
    BLOCK_MAP = None
    
    def dispatch_next_block(self, resource, path):
        assert type(resource) is file
        block_name = resource.read(self.BLOCK_NAME_LENGTH)
        if not self.CRYPT_VALUE is None:
            block_name = decrypt(block_name)
        if not block_name in self.BLOCK_MAP:
            block_type = BlockDefaultV5
        else:
            block_type = self.BLOCK_MAP(block_name)
        block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        resource.seek(-self.BLOCK_NAME_LENGTH, os.SEEK_CUR)
        return block

    
class BlockDispatcherV5(AbstractBlockDispatcher):
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        # Container blocks
        "LFLF" : BlockLFLF,
        "ROOM" : BlockROOM, # also indexed
        "RMIM" : BlockRMIM,
        "SOUN" : BlockSOUN, # also sound, kind of
        "OBIM" : BlockOBIM,
        "OBCD" : BlockOBCD,
        "LECF" : BlockLECF,
        
        # Sound blocks
        "SOU " : BlockSOU, # also container, except for MI1CD
        "ROL " : BlockSoundV5,
        "SPK " : BlockSoundV5,
        "ADL " : BlockSoundV5,
        "SBL " : BlockSoundV5,
        
        # Globally indexed blocks
        "COST" : BlockIndexed,
        "CHAR" : BlockIndexed,
        "SCRP" : BlockIndexed,
        "SOUN" : BlockIndexed,
        
        # Other special blocks
        "IMHD" : BlockIMHDV5,
        "LSCR" : BlockLSCRV5,
        "LOFF" : BlockLOFF
        
    }


class IndexFileReader(AbstractBlockReader):
    def dispatch_next_block(self, resource, path):
        pass
    