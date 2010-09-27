from __future__ import with_statement
import logging
import os
import scummpacker_util as util
import scummpacker_control as control
import dispatchers

def assign_dispatchers(index_dispatcher, block_dispatcher, file_dispatcher, indexed_blocks):
    """ This is pretty grotty."""
    control.index_dispatcher = index_dispatcher
    control.block_dispatcher = block_dispatcher
    control.file_dispatcher = file_dispatcher
    control.global_index_map = control.IndexMappingContainer(*indexed_blocks)
    control.unknown_blocks_counter = control.IndexCounter(*indexed_blocks)

class ResourceHandler(object):
    """Handles saving and loading from resource files, adjusting file names,
    spanning across multiple resource files ("disks"), etc."""
    
    SINGLE_ROOM_MULTI_FILE, MULTI_ROOM_MULTI_FILE, SINGLE_FILE = range(3)
    RESOURCE_FILE_TEMPLATES_PER_GAME = {
        "MI1EGA" : (MULTI_ROOM_MULTI_FILE, ("000", "LFL"), ("DISK%NN%", "LEC")),
        "MI1VGA" : (MULTI_ROOM_MULTI_FILE, ("000", "LFL"), ("DISK%NN%", "LEC")),
        "LOOMCD" : (MULTI_ROOM_MULTI_FILE, ("000", "LFL"), ("DISK%NN%", "LEC")),
        "MI1CD" : (SINGLE_FILE, ("MONKEY", "000"), ("MONKEY", "001")),
        "MI2" : (SINGLE_FILE, ("MONKEY2", "000"), ("MONKEY2", "001")),
        "FOA" : (SINGLE_FILE, ("ATLANTIS", "000"), ("ATLANTIS", "001"))
    }
    
    def unpack(self):       
        # Get our dispatchers that know about the version-specific stuff.
        assign_dispatchers(*dispatchers.DispatcherFactory(control.global_args.scumm_version))
        # Get resource names
        try:
            spanning, (index_name, index_ext), (resource_name, resource_ext) = self.RESOURCE_FILE_TEMPLATES_PER_GAME[control.global_args.game]
        except KeyError:
            raise util.ScummPackerException("No resource file template defined for game: %s" % control.global_args.game)
        # Load from resources
        logging.normal("Loading from game resources...")
        base_path = control.global_args.input_file_name
        assert os.path.isdir(base_path)
        resources = []
        resource_counter = 1
        
        # read index
        with file(os.path.join(base_path, index_name + "." + index_ext), 'rb') as index_file:
            index_block = control.index_dispatcher.dispatch_and_load_from_resource(index_file)
            
        # read resources, which could be split across multiple disk files.
        while True:
            # Look for DISK01.LEC, DISK02.LEC etc until no more found.
            res_name = os.path.join(base_path, resource_name.replace("%NN%", str(resource_counter).zfill(2)) + "." + resource_ext)
            if not os.path.isfile(res_name):
                break
            logging.normal("Reading from %s" % res_name)
            with file(res_name, 'rb') as res_file:
                resources.append(control.block_dispatcher.dispatch_and_load_from_resource(res_file))
            resource_counter += 1
            
        # Save to files
        logging.normal("Saving to files...")        
        base_path = control.global_args.output_file_name
        assert os.path.isdir(base_path)        
        for i, resource_block in enumerate(resources):
            disk_path = os.path.join(base_path, resource_name.replace("%NN%", str(i + 1).zfill(2)))
            logging.normal("Saving to %s" % disk_path)
            if not os.path.isdir(disk_path):
                os.mkdir(disk_path)
            resource_block.save_to_file(disk_path)
        index_block.save_to_file(base_path)
    
    def pack(self):
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
        base_path = control.global_args.input_file_name
        resources = []
        resource_counter = 1
        # load folders, which represents disk spanning.
        while True:
            # Look for DISK01, DISK02 etc until no more found.
            res_name = os.path.join(base_path, resource_name.replace("%NN%", str(resource_counter).zfill(2)))
            if not os.path.isdir(res_name):
                break
            logging.normal("Reading from %s" % res_name)
            resources.append(control.file_dispatcher.dispatch_and_load_from_file(res_name))
            resource_counter += 1        
        index_block = control.index_dispatcher.dispatch_and_load_from_file(control.global_args.input_file_name)
        
        # Save to resources
        logging.normal("Saving to game resources...")        
        base_path = control.global_args.output_file_name
        assert os.path.isdir(base_path)
        for i, resource_block in enumerate(resources):
            disk_file_name = os.path.join(base_path, resource_name.replace("%NN%", str(i + 1).zfill(2)) + "." + resource_ext)
            logging.normal("Saving to %s" % disk_file_name)
            control.disk_spanning_counter = i + 1
            with file(disk_file_name, 'wb') as disk_file:
                resource_block.save_to_resource(disk_file)

        with file(os.path.join(base_path, index_name + "." + index_ext), 'wb') as index_file:
            index_block.save_to_resource(index_file)

            
global_res_handler = ResourceHandler()