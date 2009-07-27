import array
import os
import scummpacker_control as control
import scummpacker_util as util


class AbstractBlock(object):
    def __init__(self, block_name_length, crypt_value):
        self.BLOCK_NAME_LENGTH = block_name_length
        self.CRYPT_VALUE = crypt_value
    
    def load_from_resource(self, resource):
        start = resource.tell()
        self._read_header(resource)
        self._read_data(resource, start)

    def _read_header(self, resource):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start):
        self.data = util.crypt(self._read_raw_data(resource), self.CRYPT_VALUE)
        
    def _read_name(self, resource):
        return resource.read(self.BLOCK_NAME_LENGTH)
    
    def _read_size(self, resource):
        return util.str_to_int(resource.read(4), util.BE)
    
    def _read_raw_data(self, resource):
        data = array.array('B')
        data.fromfile(resource, self.size)
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
                self.data[i] = util.crypt(b, self.CRYPT_VALUE)
        self.data.tofile(outfile)
        
    def generate_file_name(self):
        return self.name + ".dmp"


class BlockDefaultV5(BlockDefault):
    def _read_header(self, resource):
        # Should be reversed for old format resources
        self.name = util.crypt(self._read_name(resource), self.CRYPT_VALUE)
        self.size = util.crypt(self._read_size(resource), self.CRYPT_VALUE)

    def _write_header(self, outfile, path):
        outfile.write(util.crypt(self.name, self.CRYPT_VALUE))
        outfile.write(util.crypt_value(util.int_to_str(self.size, util.BE), self.CRYPT_VALUE))


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


class BlockLocallyIndexedV5(BlockDefaultV5):
    def __init__(self, *args):
        super(BlockLocallyIndexedV5, self).__init__(args)
        self.index = None
    
    # Crap on a crapstick
    def set_index(self, index):
        self.index = index
        
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
            self._add_child_block(block)
            
    def _add_child_block(self, block):
        self.children.append(block)
    
    def save_to_file(self, path):
        newpath = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(newpath):
            os.mkdir(newpath) # throws an exception if can't create dir
        for child in self.children:
            child.save_to_file(path)
        
    def generate_file_name(self):
        return self.name #+ "_" + str(self.index).zfill(3)


class BlockROOM(BlockIndexedV5, BlockContainerV5):
    pass


class BlockLOFF(BlockIndexedV5):
    pass
    
    
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
        #block.load_from_resource(resource)
        #block.save_to_file(path)


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
        "LOFF" : BlockLOFF
    }    


class IndexFileReader(AbstractBlockReader):
    def dispatch_next_block(self, resource, path):
        pass
    