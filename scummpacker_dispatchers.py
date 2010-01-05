#! /usr/bin/python
import logging
import os
import re
import scummpacker_blocks as blocks
import scummpacker_util as util

class AbstractBlockDispatcher(object):
    CRYPT_VALUE = None
    BLOCK_NAME_LENGTH = None
    BLOCK_MAP = {}
    DEFAULT_BLOCK = None
    REGEX_BLOCKS = []
    ROOT_BLOCK = None

    def dispatch_and_load_from_resource(self, resource, room_start=0):
        root_block = self.ROOT_BLOCK(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        root_block.load_from_resource(resource, 0)
        return root_block

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

    def dispatch_and_load_from_file(self, path):
        root_block = self.ROOT_BLOCK(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        root_block.load_from_file(path)
        return root_block

    def dispatch_next_block(self, block_name):
        if block_name in self.BLOCK_MAP:
            block_type = self.BLOCK_MAP[block_name]
        else:
            block_type = self._dispatch_regex_block(block_name)
            if block_type is None:
                if not block_name in self.IGNORED_BLOCKS:
                    logging.warning("Ignoring unknown file: " + str(block_name))
                return None
        block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        return block

class BlockDispatcherV5(AbstractBlockDispatcher):

    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        # Container blocks
        "LFLF" : blocks.BlockLFLFV5, # also indexed
        "ROOM" : blocks.BlockROOMV5, # also indexed (kind of)
        "RMIM" : blocks.BlockContainerV5,
        "SOUN" : blocks.BlockSOUNV5, # also sound (kind of)
        "OBIM" : blocks.BlockOBIMV5,
        "OBCD" : blocks.BlockOBCDV5,
        "LECF" : blocks.BlockLECFV5,

        # Sound blocks
        "SOU " : blocks.BlockSOUV5,
        "ROL " : blocks.BlockMIDISoundV5,
        "SPK " : blocks.BlockMIDISoundV5,
        "ADL " : blocks.BlockMIDISoundV5,
        "SBL " : blocks.BlockSBLV5,

        # Globally indexed blocks
        "COST" : blocks.BlockGloballyIndexedV5,
        "CHAR" : blocks.BlockGloballyIndexedV5,
        "SCRP" : blocks.BlockGloballyIndexedV5,
        "SOUN" : blocks.BlockSOUNV5,

        # Other blocks that should not used default block functionality
        "IMHD" : blocks.BlockIMHDV5,
        "LSCR" : blocks.BlockLSCRV5,
        "RMHD" : blocks.BlockRMHDV5,
        "RMIH" : blocks.BlockRMIHV5,
        "LOFF" : blocks.BlockLOFFV5

    }
    REGEX_BLOCKS = [
        (re.compile(r"IM[0-9]{2}"), blocks.BlockContainerV5)
    ]
    DEFAULT_BLOCK = blocks.BlockDefaultV5
    ROOT_BLOCK = blocks.BlockLECFV5

class FileDispatcherV5(AbstractFileDispatcher):
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        # Root
        r"LECF" : blocks.BlockLECFV5,
        # LECF
        # -LFLF
        r"ROOM" : blocks.BlockROOMV5,
        # --ROOM
        r"BOXD.dmp" : blocks.BlockDefaultV5,
        r"BOXM.dmp" : blocks.BlockDefaultV5,
        r"CLUT.dmp" : blocks.BlockDefaultV5,
        r"CYCL.dmp" : blocks.BlockDefaultV5,
        r"EPAL.dmp" : blocks.BlockDefaultV5,
        r"SCAL.dmp" : blocks.BlockDefaultV5,
        r"TRNS.dmp" : blocks.BlockDefaultV5,
        r"RMHD.xml" : blocks.BlockRMHDV5,
        r"RMIM" : blocks.BlockContainerV5,
        r"objects" : blocks.ObjectBlockContainer,
        r"scripts" : blocks.ScriptBlockContainer,
        # ---RMIM
        r"RMIH.xml" : blocks.BlockRMIHV5,
        # ---objects (incl. subdirs)
        r"VERB.dmp" : blocks.BlockDefaultV5,
        r"SMAP.dmp" : blocks.BlockDefaultV5, # also RMIM
        r"BOMP.dmp" : blocks.BlockDefaultV5, # room 99, object 1045 in MI1 CD.
        # ---scripts
        r"ENCD.dmp" : blocks.BlockDefaultV5,
        r"EXCD.dmp" : blocks.BlockDefaultV5,
        # - Sound blocks
        r"SOU" : blocks.BlockSOUV5,
        r"ROL.mid" : blocks.BlockMIDISoundV5,
        r"SPK.mid" : blocks.BlockMIDISoundV5,
        r"ADL.mid" : blocks.BlockMIDISoundV5,
        r"SBL.voc" : blocks.BlockSBLV5,

    }
    REGEX_BLOCKS = [
        # LECF
        (re.compile(r"LFLF_[0-9]{3}.*"), blocks.BlockLFLFV5),
        # -LFLF
        (re.compile(r"SOUN_[0-9]{3}(?:\.dmp)?"), blocks.BlockSOUNV5),
        (re.compile(r"CHAR_[0-9]{3}"), blocks.BlockGloballyIndexedV5),
        (re.compile(r"COST_[0-9]{3}"), blocks.BlockGloballyIndexedV5),
        (re.compile(r"SCRP_[0-9]{3}"), blocks.BlockGloballyIndexedV5),
        # --ROOM
        # ---objects
        (re.compile(r"IM[0-9a-fA-F]{2}"), blocks.BlockContainerV5), # also RMIM
        (re.compile(r"ZP[0-9a-fA-F]{2}\.dmp"), blocks.BlockDefaultV5), # also RMIM
        # --scripts
        (re.compile(r"LSCR_[0-9]{3}\.dmp"), blocks.BlockLSCRV5)
    ]
    IGNORED_BLOCKS = frozenset([
        r"ROL.mdhd",
        r"SPK.mdhd",
        r"ADL.mdhd",
        r"SBL.mdhd",
        r"order.xml"
    ])
    DEFAULT_BLOCK = blocks.BlockDefaultV5
    ROOT_BLOCK = blocks.BlockLECFV5

class IndexBlockContainerV5(AbstractBlockDispatcher):
    """Resource.000 processor; just maps blocks to Python objects (POPOs?)."""
    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 4
    BLOCK_MAP = {
        "RNAM" : blocks.BlockRNAMV5,
        "MAXS" : blocks.BlockMAXSV5,
        "DROO" : blocks.BlockDROOV5,
        "DSCR" : blocks.BlockIndexDirectoryV5,
        "DSOU" : blocks.BlockIndexDirectoryV5,
        "DCOS" : blocks.BlockIndexDirectoryV5,
        "DCHR" : blocks.BlockIndexDirectoryV5,
        "DOBJ" : blocks.BlockDOBJV5
    }
    REGEX_BLOCKS = []
    DEFAULT_BLOCK = blocks.BlockDefaultV5

    def dispatch_and_load_from_resource(self, resource, room_start=0):
        self.load_from_resource(resource, room_start)
        return self

    def load_from_resource(self, resource, room_start=0):
        self.children = []
        for i in xrange(len(self.BLOCK_MAP.keys())):
            block = self.dispatch_next_block(resource)
            block.load_from_resource(resource)
            self.children.append(block)

    def save_to_file(self, path):
        for c in self.children:
            c.save_to_file(path)

    def dispatch_and_load_from_file(self, path):
        self.load_from_file(path)
        return self

    def load_from_file(self, path):
        self.children = []

        # Crappy crappy crap
        # It's like this because blocks need to be in a specific order
        rnam_block = blocks.BlockRNAMV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        rnam_block.load_from_file(os.path.join(path, "roomnames.xml"))
        self.children.append(rnam_block)

        maxs_block = blocks.BlockMAXSV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        maxs_block.load_from_file(os.path.join(path, "maxs.xml"))
        self.children.append(maxs_block)

        d_block = blocks.BlockDROOV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        self.children.append(d_block)
        d_block = blocks.BlockIndexDirectoryV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        d_block.name = "DSCR"
        self.children.append(d_block)
        d_block = blocks.BlockIndexDirectoryV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        d_block.name = "DSOU"
        self.children.append(d_block)
        d_block = blocks.BlockIndexDirectoryV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        d_block.name = "DCOS"
        self.children.append(d_block)
        d_block = blocks.BlockIndexDirectoryV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        d_block.name = "DCHR"
        self.children.append(d_block)

        dobj_block = blocks.BlockDOBJV5(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        dobj_block.load_from_file(os.path.join(path, "dobj.xml"))
        self.children.append(dobj_block)

    def save_to_resource(self, resource, room_start=0):
        for c in self.children:
            logging.debug("Saving index: " + c.name)
            c.save_to_resource(resource, room_start)

class DispatcherFactory(object):
    # SCUMM engine version : index dispatcher (combined block & file), resource block dispatcher, resource file dispatcher
    grammars = { "5" : (IndexBlockContainerV5, BlockDispatcherV5, FileDispatcherV5) }

    def __new__(cls, scumm_version, *args, **kwds):
        assert type(scumm_version) == str
        if not scumm_version in DispatcherFactory.grammars:
            raise util.ScummPackerException("Unsupported SCUMM version: " + str(scumm_version))
        index_dispatcher, block_dispatcher, file_dispatcher = DispatcherFactory.grammars[scumm_version]
        return (index_dispatcher(), block_dispatcher(), file_dispatcher())