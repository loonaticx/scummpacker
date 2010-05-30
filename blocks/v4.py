#! /usr/bin/python
import logging
import scummpacker_control as control
from common import *
from v4_resource import *
from v4_index import *

def __test_unpack():
    import dispatchers
    control.global_args.set_args(unpack=True, pack=False, scumm_version="4",
        game="LOOMCD", input_file_name="DISK01.LEC", output_file_name="D:\\TEMP")
    outpath = "D:\\TEMP"

#    dirfile = file("000.LFL", "rb")
#    dir_block = dispatchers.IndexBlockContainerV5()
#    dir_block.load_from_resource(dirfile)
#    dirfile.close()
#
#    dir_block.save_to_file(outpath)
    print dispatchers.INDEXED_BLOCKS_V4
    control.unknown_blocks_counter = control.IndexCounter(*dispatchers.INDEXED_BLOCKS_V4)
    control.global_index_map = control.IndexMappingContainer(*dispatchers.INDEXED_BLOCKS_V4)

    logging.debug("Reading from indexes...")
    dirfile = file("000.LFL", "rb")
    dir_block = dispatchers.IndexBlockContainerV4()
    dir_block.load_from_resource(dirfile)
    dirfile.close()

    dir_block.save_to_file(outpath)
    
    
    logging.debug("Reading from resources...")
    control.block_dispatcher = dispatchers.BlockDispatcherV4()
    resfile = file("DISK01.LEC", "rb")
    block = BlockContainerV4(2, 0x69)
    block.load_from_resource(resfile)
    resfile.close()

    logging.debug("Saving to files...")
    block.save_to_file(outpath)

def __test():
    __test_unpack()
    #__test_unpack_from_file()
    #__test_pack()

# TODO: better integration test dispatching
test_blocks_v4 = __test

if __name__ == "__main__": __test()
