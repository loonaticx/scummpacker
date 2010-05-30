#! /usr/bin/python
from v4_base import *

class BlockRNV4(BlockRoomNames, BlockDefaultV4):
    """ Room names """
    name = "RN"

class Block0RV4(BlockRoomIndexes, BlockDefaultV4):
    """ Directory of Rooms.

    Each game seems to have a different padding length.
    
    Doesn't seem to be used in LOOM CD.
    
    TODO: correct implementation?
    TODO: if this implementation is okay, abstract to common."""
    name = "0R"
    DEFAULT_PADDING_LENGTHS = {
        "LOOMCD" : 100
    }
    
class Block0OV4(BlockObjectIndexes, BlockDefaultV4):
    name = "0R"
    HAS_OBJECT_CLASS_DATA = False
