# Stores globals
import os.path
from optparse import OptionParser
import scummpacker_util as util

class IndexCounter(object):
    def __init__(self, *args):
        self.index_map = {}
        for s in args:
            self.index_map[s] = 0

    def reset_counts(self):
        for k in self.index_map:
            self.index_map[k] = 0
    
    def get_next_index(self, index_name):
        if not index_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \"" 
                                            + str(index_name) 
                                            + "\" tried to retrieve a counted index.")
        self.index_map[index_name] = self.index_map[index_name] + 1
        return self.index_map[index_name]


class IndexMappingContainer(object):
    def __init__(self, *args):
        self.index_map = {}
        for s in args:
            self.index_map[s] = {}
    
    def reset_maps(self):
        for k in self.index_map:
            self.index_map[k].clear()
            
    def map_index(self, map_name, key, index):
        self.__setitem__(map_name, key, index)
        
    def __setitem__(self, map_name, key, index):
        if not map_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \"" 
                                            + str(map_name) 
                                            + "\" tried to store a global index.")
        self.index_map[map_name][key] = index
        
    def get_index(self, map_name, key):
        return self.__getitem__(map_name, key)
    
    def __getitem__(self, map_name, key):
        if not map_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \"" 
                                            + str(map_name) 
                                            + "\" tried to retrieve a global index.")
        if not key in self.index_map[map_name]:
            raise util.ScummPackerUnrecognisedIndexException("Block \"" 
                                            + str(map_name) 
                                            + "\" tried to retrieve an unrecognised global index \""
                                            + str(key)
                                            + "\".")
        return self.index_map[map_name][key]

    def items(self, map_name):
        """Returns key/value pairs for the desired block table."""
        if not map_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \""
                                            + str(map_name)
                                            + "\" tried to retrieve a global index.")
        return self.index_map[map_name].items()
    
class GlobalArguments(object):
    RESOURCE_FILE_NAME_MAP = {
        "MI1CD" : "MONKEY",
        "MI2" : "MONKEY2",
        "FOA" : "ATLANTIS"
    }
    SCUMM_VERSION_GAME_MAP = {
        "MI1CD" : "5",
        "MI2" : "5",
        "FOA" : "5"
    }
    DEFAULT_SCUMM_VERSION_GAMES = {
        "5" : "MI2"
    }
    DEFAULT_GAME_FOR_UNKNOWN_SCUMM_VERSION = "MI2"

    def __init__(self):
        super(GlobalArguments, self).__setattr__("scumm_version", None)
        super(GlobalArguments, self).__setattr__("game", None)
        super(GlobalArguments, self).__setattr__("input_file_name", None)
        super(GlobalArguments, self).__setattr__("output_file_name", None)
        super(GlobalArguments, self).__setattr__("unpack", None)
        super(GlobalArguments, self).__setattr__("pack", None)
        self.oparser = OptionParser(usage="%prog [options]",
                               version="ScummPacker v3",
                               description="Packs and unpacks resources used by LucasArts adventure games.")
        self.oparser.add_option("-v", "--scumm-version", action="store",
                           dest="scumm_version",
                           choices=self.DEFAULT_SCUMM_VERSION_GAMES.keys(),
                           help="Specify the SCUMM version to target. " +
                           "Possible options are: " +
                           ", ".join(self.DEFAULT_SCUMM_VERSION_GAMES.keys()) + ". ")
        self.oparser.add_option("-g", "--game", action="store",
                           dest="game",
                           choices=self.SCUMM_VERSION_GAME_MAP.keys(),
                           help="Specify the game to target. " +
                           "Possible options are: " +
                           ", ".join(self.SCUMM_VERSION_GAME_MAP.keys()) + ". ")
        self.oparser.add_option("-i", "--input", action="store",
                           dest="input_file_name",
                           help="Specify an input file name. " +
                           "If not specified, ScummPacker will try to guess.")
        self.oparser.add_option("-o", "--output", action="store",
                           dest="output_file_name",
                           help="Specify an output base file name (will have .000 and .001 appended). " +
                           "If not specified, ScummPacker will generate one.")
        self.oparser.add_option("-u", "--unpack", action="store_true",
                           dest="unpack", default=False,
                           help="Unpack resources.")
        self.oparser.add_option("-p", "--pack", action="store_true",
                           dest="pack", default=False,
                           help="Pack resources.")
        self.oparser.set_defaults(scumm_version="5", game="MI2", output_file_name="outres")

    def set_scumm_version(self, scumm_version):
        super(GlobalArguments, self).__setattr__("scumm_version",
                    scumm_version)
        if self.game != None:
            if self.SCUMM_VERSION_GAME_MAP[self.game] != scumm_version:
                raise util.ScummPackerException("A conflicting SCUMM version and game ID was specified.")
        elif not scumm_version in self.DEFAULT_SCUMM_VERSION_GAMES:
            super(GlobalArguments, self).__setattr__("game",
                    self.DEFAULT_GAME_FOR_UNKNOWN_SCUMM_VERSION)
        else:
            super(GlobalArguments, self).__setattr__("game",
                    self.DEFAULT_SCUMM_VERSION_GAMES[scumm_version])

    def set_game(self, game):
        super(GlobalArguments, self).__setattr__("game",
                    game)
        if self.scumm_version != None:
            if self.SCUMM_VERSION_GAME_MAP[self.game] != self.scumm_version:
                raise util.ScummPackerException("A conflicting SCUMM version and game ID was specified.")
        elif not game in self.SCUMM_VERSION_GAME_MAP:
            raise util.ScummPackerException("Unknown or unsupported game ID: " + str(game))
        else:
            super(GlobalArguments, self).__setattr__("scumm_version",
                    self.SCUMM_VERSION_GAME_MAP[game])

    def set_input_file_name(self, input_file_name):
        if self.unpack:
            if input_file_name == None:
                if self.game == None:
                    raise util.ScummPackerException("No game specified; can't guess input file name.")
                super(GlobalArguments, self).__setattr__("input_file_name",
                        self.RESOURCE_FILE_NAME_MAP[self.game])
            elif os.path.isdir(input_file_name):
                if self.game == None:
                    raise util.ScummPackerException("No game specified; can't guess input file name.")
                super(GlobalArguments, self).__setattr__("input_file_name",
                        os.path.join(os.path.splitext(input_file_name)[0], self.RESOURCE_FILE_NAME_MAP[self.game]))
            else:
                super(GlobalArguments, self).__setattr__("input_file_name",
                        os.path.splitext(input_file_name)[0])
        elif self.pack:
            if input_file_name == None:
                raise util.ScummPackerException("No input directory specified.")
            elif not os.path.isdir(input_file_name):
                raise util.ScummPackerException("Input does not appear to be a valid directory.")
            else:
                super(GlobalArguments, self).__setattr__("input_file_name",
                        input_file_name)

    def __setattr__(self, item, value):
        if item == "game":
            self.set_game(value)
        elif item == "scumm_version":
            self.set_scumm_version(value)
        elif item == "input_file_name":
            self.set_input_file_name(value)
        else:
            super(GlobalArguments, self).__setattr__(item, value)

    def parse_args(self):
        options, _ = self.oparser.parse_args()
        # @type options Values
        self.unpack = options.unpack
        self.pack = options.pack
        self.scumm_version = options.scumm_version
        self.game = options.game
        self.input_file_name = options.input_file_name
        self.output_file_name = options.output_file_name

    def print_help(self):
        self.oparser.print_help()

global_index_map = IndexMappingContainer(
    "ROOM",
    "COST",
    "CHAR",
    "SCRP",
    "SOUN",
    "LFLF",
    "RNAM"
)

unknown_blocks_counter = IndexCounter(
    "ROOM",
    "COST",
    "CHAR",
    "SCRP",
    "SOUN",
    "LFLF"
)

global_args = GlobalArguments()

block_dispatcher = None
file_dispatcher = None