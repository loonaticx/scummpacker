#! /usr/bin/python
import logging
import sys
import traceback
import scummpacker_control as control
import scummpacker_res_handler as res_handler
import scummpacker_util as util


__author__="Laurence Dougal Myers"
__date__ ="$22/12/2009 16:52:52$"

if sys.version_info[0] < 2 or (sys.version_info[0] == 2 and sys.version_info[1] < 5):
    raise util.ScummPackerException("ScummPacker requires Python 2.5 or higher.")

def main():
    try:
        logging.basicConfig(format="", level=logging.DEBUG)
        logging.NORMAL = 15
        logging.normal = lambda x: logging.log(logging.NORMAL, x)
        logging.level = logging.NORMAL
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
            
            res_handler.global_res_handler.unpack()
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
            
            res_handler.global_res_handler.pack()
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

