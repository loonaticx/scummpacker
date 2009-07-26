import array
import os
import scummpacker_util as util

class AbstractBlock(Object):
    def saveToFile(self, path):
        raise NotImplementedError("This method must be overriden by a concrete class.")

class AbstractSoundBlock(AbstractBlock):
    pass

class AbstractIndexedBlock(AbstractBlock):
    pass

class AbstractContainerBlock(AbstractBlock):
    pass
    
class AbstractBlockDispatcher(Object):
    CRYPT_VALUE = None
    BLOCK_NAME_LENGTH = None
    BLOCK_MAP = None
    
    def readNextBlockFromResource(self, resource, path):
        assert type(resource) is file
        block_name = resource.read(BLOCK_NAME_LENGTH)
        if not self.CRYPT_VALUE is None:
            block_name = decrypt(block_name)
        if not block_name in self.BLOCK_MAP:
            util.error("Unrecognised block type: " + block_name + ", attempting to continue.")
            block_type = BlockUnknown
        else:
            block_type = self.BLOCK_MAP(block_name)
        resource.seek(-BLOCK_NAME_LENGTH, os.SEEK_CUR)
        block = block_type()
        block.loadFromResource(resource)
        block.saveToFile(path)

class BlockDispatcherV5(AbstractBlockDispatcher):
    CRYPT_VALUE = None
    BLOCK_NAME_LENGTH = None
    BLOCK_MAP = {
        # Container blocks
        "LFLF" : BlockLFLF,
        "ROOM" : BlockROOM,
        "RMIM" : BlockRMIM,
        #"SOUN" : BlockSOUN,
        "OBIM" : BlockOBIM,
        "OBCD" : BlockOBCD,
        #"SOU " : BlockSOU,
        "LECF" : BlockLECF,
        
        # Sound blocks
        "SOU " : BlockSOU,
        "ROL " : BlockROL,
        "SPK " : BlockSPK,
        "ADL " : BlockADL,
        "SBL " : BlockSBL,
        
        # Globally indexed blocks
        "COST" : BlockCOST,
        "CHAR" : BlockCHAR,
        "SCRP" : BlockSCRP,
        "SOUN" : BlockSOUN,
        "ROOM" : BlockROOM,
        "LOFF" : BlockLOFF
    }
    
class BlockDefault(BasicBlockDumperMixIn, AbstractBlock):
    def loadFromResource(self, resource):
        self.name = util.crypt(self.readName(resource), self.CRYPT_VALUE)
        self.size = util.crypt(self.readSize(resource), self.CRYPT_VALUE)
        self.rawdata = util.crypt(self.readRawData(resource), self.CRYPT_VALUE)
        
    def readName(self, resource):
        return resource.read(self.BLOCK_NAME_LENGTH)
    
    def readSize(self, resource):
        return util.strToInt(resource.read(4), util.BE)
    
    def readRawData(self, resource):
        data = array.array('B')
        data.fromfile(resource, self.size)
        return data

class BasicBlockDumperMixIn(Object):
    def saveToFile(self, path):
        #os.path.join(path, ) # need to somehow keep track of block IDs
        pass
        # 1) Create the file
        # 2) Write the header (name + size)
        # 3) Write the raw data
        # 4) Close the file

class IndexFileReader(AbstractBlockReader):
    def readNextBlockFromResource(self, resource):
        pass
    