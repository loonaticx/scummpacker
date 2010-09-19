#! /usr/bin/python
from __future__ import with_statement
import logging
import os
import sys
import traceback
import scummpacker_util as util
import scummpacker_control as control
import dispatchers

__author__="Laurence Dougal Myers"
__date__ ="$22/12/2009 16:52:52$"

if sys.version_info[0] < 2 or (sys.version_info[0] == 2 and sys.version_info[1] < 5):
    raise util.ScummPackerException("ScummPacker requires Python 2.5 or higher.")

class ResourceHandler(object):
    """Handles saving and loading from resource files, adjusting file names,
    spanning across multiple resource files ("disks"), etc."""
    
    SINGLE_DISK, MULTI_DISK = range(2)
    RESOURCE_FILE_TEMPLATES_PER_GAME = {
        "LOOMCD" : (SINGLE_DISK, ("000", "LFL"), ("DISK01", "LEC")),
        "MI1CD" : (SINGLE_DISK, ("MONKEY", "000"), ("MONKEY", "001")),
        "MI2" : (SINGLE_DISK, ("MONKEY2", "000"), ("MONKEY2", "001")),
        "FOA" : (SINGLE_DISK, ("ATLANTIS", "000"), ("ATLANTIS", "001"))
    }    
    
    def _find_next_output_file_name(self, name):
        pass
    
    def pack(self):       
        # Get our dispatchers that know about the version-specific stuff.
        assign_dispatchers(*dispatchers.DispatcherFactory(control.global_args.scumm_version))
        # Get resource names
        try:
            spanning, (index_name, index_ext), (resource_name, resource_ext) = self.RESOURCE_FILE_TEMPLATES_PER_GAME[control.global_args.game]
        except KeyError:
            raise util.ScummPackerException("No resource file template defined for game: %s" % control.global_args.game)
        # Load from resources
        logging.normal("Loading from game resources...")
        # Don't append extra .000 or .001 if specified input file ends in .000 or .001.
        base_name = control.global_args.input_file_name
        assert os.path.isdir(base_name)
        with file(os.path.join(base_name, index_name + "." + index_ext), 'rb') as index_file:
            index_block = control.index_dispatcher.dispatch_and_load_from_resource(index_file)
        with file(os.path.join(base_name, resource_name + "." + resource_ext), 'rb') as res_file:
            resource_block = control.block_dispatcher.dispatch_and_load_from_resource(res_file)
        # Save to files
        logging.normal("Saving to files...")
        assert os.path.isdir(control.global_args.output_file_name)
        resource_block.save_to_file(control.global_args.output_file_name)
        index_block.save_to_file(control.global_args.output_file_name)
    
    def unpack(self):
        # Get our dispatchers that know about the version-specific stuff.
        assign_dispatchers(*dispatchers.DispatcherFactory(control.global_args.scumm_version))
        # Get resource names
        try:
            spanning, (index_name, index_ext), (resource_name, resource_ext) = self.RESOURCE_FILE_TEMPLATES_PER_GAME[control.global_args.game]
        except KeyError:
            raise util.ScummPackerException("No resource file template defined for game: %s" % control.global_args.game)
        # Load from files
        logging.normal("Loading from files...")
        assert os.path.isdir(control.global_args.input_file_name)
        resource_block = control.file_dispatcher.dispatch_and_load_from_file(control.global_args.input_file_name)
        index_block = control.index_dispatcher.dispatch_and_load_from_file(control.global_args.input_file_name)
        # Save to resources
        logging.normal("Saving to game resources...")        
        # Don't append extra .000 or .001 if specified input file ends in .000 or .001.
        base_name = control.global_args.output_file_name
        assert os.path.isdir(base_name)
        with file(os.path.join(base_name, resource_name + "." + resource_ext), 'wb') as res_file:
            resource_block.save_to_resource(res_file)
        with file(os.path.join(base_name, index_name + "." + index_ext), 'wb') as index_file:
            index_block.save_to_resource(index_file)

def assign_dispatchers(index_dispatcher, block_dispatcher, file_dispatcher, indexed_blocks):
    """ This is pretty grotty."""
    control.index_dispatcher = index_dispatcher
    control.block_dispatcher = block_dispatcher
    control.file_dispatcher = file_dispatcher
    control.global_index_map = control.IndexMappingContainer(*indexed_blocks)
    control.unknown_blocks_counter = control.IndexCounter(*indexed_blocks)

def main():
    try:
        logging.basicConfig(format="", level=logging.DEBUG)
        logging.NORMAL = 15
        logging.normal = lambda x: logging.log(logging.NORMAL, x)
        logging.level = logging.NORMAL
        # Delegate argument parsing to the global arguments container
        control.global_args.parse_args()
        res_handler = ResourceHandler()

        if control.global_args.unpack:
            logging.normal("Starting game resource unpacking.")
            # Check that we have an input file name
            if control.global_args.input_file_name == None:
                raise util.ScummPackerException("No input path specified")
            # Check that we have an output file name
            if control.global_args.output_file_name == None:
                raise util.ScummPackerException("No output path specified")
            # Try and create the directory - if output is an existing file this will fail
            if not os.path.isdir(control.global_args.output_file_name):
                try:
                    os.mkdir(control.global_args.output_file_name)
                except OSError, ose:
                    raise util.ScummPackerException("Could not create output directory: " +
                                            str(control.global_args.output_file_name))
            
            res_handler.pack()
            logging.normal("Finished!")
            return 0

        elif control.global_args.pack:
            logging.normal("Starting packing to game resources.")
            # Check that we have an input file name
            if control.global_args.input_file_name == None:
                raise util.ScummPackerException("No input path specified")
            # Check that we have an output file name
            if control.global_args.output_file_name == None:
                raise util.ScummPackerException("No output path specified")
            
            res_handler.unpack()
            logging.normal("Finished!")
            return 0

        else:
            logging.error("Please specify whether to pack or unpack SCUMM resources.")
            control.global_args.print_help()
            return 1
        
    except Exception, e:
        logging.error("Unhandled exception occured: " + str(e))
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

