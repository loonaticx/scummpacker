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
        # Delegate argument parsing to the global arguments container
        control.global_args.parse_args()

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
            # Get our dispatchers that know about the version-specific stuff.
            assign_dispatchers(*dispatchers.DispatcherFactory(control.global_args.scumm_version))
            # Load from resources
            logging.normal("Loading from game resources...")
            with file(control.global_args.input_file_name + ".000", 'rb') as index_file:
                index_block = control.index_dispatcher.dispatch_and_load_from_resource(index_file)
            with file(control.global_args.input_file_name + ".001", 'rb') as res_file:
                resource_block = control.block_dispatcher.dispatch_and_load_from_resource(res_file)
            # Save to files
            logging.normal("Saving to files...")
            resource_block.save_to_file(control.global_args.output_file_name)
            index_block.save_to_file(control.global_args.output_file_name)
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
            # Get our dispatchers that know about the version-specific stuff.
            assign_dispatchers(*dispatchers.DispatcherFactory(control.global_args.scumm_version))
            # Load from files
            logging.normal("Loading from files...")
            resource_block = control.file_dispatcher.dispatch_and_load_from_file(control.global_args.input_file_name)
            index_block = control.index_dispatcher.dispatch_and_load_from_file(control.global_args.input_file_name)
            # Save to resources
            logging.normal("Saving to game resources...")
            with file(control.global_args.output_file_name + ".001", 'wb') as res_file:
                resource_block.save_to_resource(res_file)
            with file(control.global_args.output_file_name + ".000", 'wb') as index_file:
                index_block.save_to_resource(index_file)
            logging.normal("Finished!")
            return 0

        else:
            logging.error("Please specify whether to pack or unpack SCUMM resources.")
            control.global_args.print_help()
            return 1
        
    except Exception, e:
        logging.error("Unhandled exception occured: " + str(e))
        logging.debug(traceback.print_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())

