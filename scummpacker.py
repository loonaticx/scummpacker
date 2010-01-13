#! /usr/bin/python
from __future__ import with_statement
import logging
import os
import sys
import traceback
import scummpacker_util as util
import scummpacker_control as control
import scummpacker_blocks as blocks
import scummpacker_dispatchers as dispatchers

__author__="Laurence Dougal Myers"
__date__ ="$22/12/2009 16:52:52$"

def main():
    try:
        logging.basicConfig(format="")
        # Delegate argument parsing to the global arguments container
        control.global_args.parse_args()

        if control.global_args.unpack:
            logging.critical("Starting game resource unpacking.")
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
            index_dispatcher, block_dispatcher, file_dispatcher = dispatchers.DispatcherFactory(control.global_args.scumm_version)
            blocks.block_dispatcher = block_dispatcher # crap, how to refactor this?
            # Load from resources
            logging.critical("Loading from game resources...")
            with file(control.global_args.input_file_name + ".000", 'rb') as index_file:
                index_block = index_dispatcher.dispatch_and_load_from_resource(index_file)
            with file(control.global_args.input_file_name + ".001", 'rb') as res_file:
                resource_block = block_dispatcher.dispatch_and_load_from_resource(res_file)
            # Save to files
            logging.critical("Saving to files...")
            resource_block.save_to_file(control.global_args.output_file_name)
            index_block.save_to_file(control.global_args.output_file_name)
            logging.critical("Finished!")
            return 0

        elif control.global_args.pack:
            logging.critical("Starting packing to game resources.")
            # Check that we have an input file name
            if control.global_args.input_file_name == None:
                raise util.ScummPackerException("No input path specified")
            # Check that we have an output file name
            if control.global_args.output_file_name == None:
                raise util.ScummPackerException("No output path specified")
            # Get our dispatchers that know about the version-specific stuff.
            index_dispatcher, block_dispatcher, file_dispatcher = dispatchers.DispatcherFactory(control.global_args.scumm_version)
            control.file_dispatcher = file_dispatcher # crap
            # Load from files
            logging.critical("Loading from files...")
            resource_block = file_dispatcher.dispatch_and_load_from_file(control.global_args.input_file_name)
            index_block = index_dispatcher.dispatch_and_load_from_file(control.global_args.input_file_name)
            # Save to resources
            logging.critical("Saving to game resources...")
            with file(control.global_args.output_file_name + ".001", 'wb') as res_file:
                resource_block.save_to_resource(res_file)
            with file(control.global_args.output_file_name + ".000", 'wb') as index_file:
                index_block.save_to_resource(index_file)
            logging.critical("Finished!")
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

