#! /usr/bin/python
import scummpacker_util as util
import blocks
from v4 import *
from v5 import *

class DispatcherFactory(object):
    # SCUMM engine version : index dispatcher (combined block & file), resource block dispatcher, resource file dispatcher
    grammars = {
        "4" : (None, BlockDispatcherV4, None),
        "5" : (IndexBlockContainerV5, BlockDispatcherV5, FileDispatcherV5)
    }

    def __new__(cls, scumm_version, *args, **kwds):
        assert type(scumm_version) == str
        if not scumm_version in DispatcherFactory.grammars:
            raise util.ScummPackerException("Unsupported SCUMM version: " + str(scumm_version))
        index_dispatcher, block_dispatcher, file_dispatcher = DispatcherFactory.grammars[scumm_version]
        return (index_dispatcher(), block_dispatcher(), file_dispatcher())