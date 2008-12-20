##################################################################
####
#### SCUMM Packer
#### Laurence Dougal Myers
#### Begun 19 September 2004
####
#### Performs mostly-dumb extraction or semi-intelligent compaction of
#### LucasArts games' resource files.
####
#### Extraction stores ID based on offset tables in RESOURCE.000
#### Compaction merges dumped files, generating headers and file sizes
#### automatically, and generates offset tables for RESROUCE.000
####
#### Currently only works for Monkey Island 2.
####
##################################################################
#### TODO:
#### Make try/catches around all file operations and make them better
####
#### Generate NLSC chunks (they only contain how many local scripts there are)
####
#### Modify chunks that store how many items they hold (needed for
#### RMIM\RMIH (z-buffers), OBIM\IMHD (images and z-buffers per image),
#### RMHD (number of objects, height/width?)
####
#### Have an option for merged dumping - eg dump images as a single file
#### rather than RMIM\IMG01 etc
####
#### Relax file name restrictions by using regular expressions
####
##################################################################
import os
import sys
import array
import re
from optparse import OptionParser

# Globals
# Most of them probably shouldn't be globals, but I'm lazy

# This needs to be changeable
dirfilename = "MONKEY.000"
resfilename = "MONKEY.001"

resourcenames = {"MI1" : ("MONKEY.000", "MONKEY.001"),
                 "MI2" : ("MONKEY2.000", "MONKEY2.001"),
                 "FOA" : ("ATLANTIS.000", "ATLANTIS.001")}

global basepath
basepath = ""

# Directories of offsets for character sets, scripts, costumes, sounds, rooms
#  and room names
dchr = {}
dscr = {}
dcos = {}
dsou = {}
droo = {}
rnam = {}

# Dummy variable to be replaced by option parser
options = None

# This needs to be changeable when support for more games is implemented
decryptvalue = 0x69
encryptvalue = 0x69

# These should get re-assigned depending on game
containertypes = ["LFLF", "ROOM", "RMIM", "SOUN",
                  "OBIM", "OBCD", "SOU ", "LECF"]
soundtypes = ["SOU ", "ROL ", "SPK ", "ADL ", "SBL "]
specialtypes = {"COST":dcos, "CHAR":dchr, "SCRP":dscr,
                "SOUN":dsou, "ROOM":droo, "LOFF":droo}
dirspecialtypes = {"DCOS":dcos, "DCHR":dchr, "DSCR":dscr,
                "DSOU":dsou}

# Debugging/verbose messages
def message(stringin):
    """ Print a message only if verbose mode is set."""
    if options.verbose:
        print stringin

# Function not implemented - files are encrypted by decrypting unencrypted files
##def encryptFile(file):
##  pass

# Decrypt also doubles as encrypt, I'm just too lazy to name it properly
def decrypt(input):
    """ Perform an XOR with a decrypt value on an array."""
    if isinstance(input, array.array):
        # Should also check if it's an array of the same typecode
        for i, byte in enumerate(input):
            input[i] = byte ^ decryptvalue 
    return input

def getByte(file, encrypted=1):
    """ Retrieve a single byte from a given file and decrypt it."""
    temparray = array.array('B')
    temparray.fromfile(file, 1)
    if encrypted:
        return decrypt(temparray)
    return temparray

def getWord(file, encrypted=1):
    """ Retrieve two bytes from a given file and decrypt them."""
    temparray = array.array('B')
    temparray.fromfile(file, 2)
    if encrypted:
        return decrypt(temparray)
    return temparray

# Is LE right? I get confused between endians.
def getWordLE(file, encrypted=1):
    """ Retrieve two bytes from a given file, decrypt them, and return an 
    array reversed.
    """
    
    temp = getWord(file, encrypted)
    temp.reverse()
    return temp

def getDWord(file, encrypted=1):
    """ Retrieve four bytes from a given file and decrypt them."""
    temparray = array.array('B')
    temparray.fromfile(file, 4)
    if encrypted:
        return decrypt(temparray)
    return temparray

def getDWordLE(file, encrypted=1):
    """ Retrieve four bytes from a given file and decrypt them, and return an 
    array in reverse order.
    """
    temp = getDWord(file, encrypted)
    temp.reverse()
    return temp

def getQWord(file, encrypted=1):
    """ Retrieve eight bytes from a given file and decrypt them.
    
    Not actually used in the program, but could be used to get the header
    (rather than calling getDWord twice).
    """
    temparray = array.array('B')
    temparray.fromfile(file, 8)
    if encrypted:
        return decrypt(temparray)
    return temparray

def getChunk(file, size, encrypted=1):
    """ Retrieve any number of bytes from a gven file and decrypt them."""
    temparray = array.array('B')
    temparray.fromfile(file, size)
    if encrypted:
        return decrypt(temparray)
    return temparray

def arrayToInt(input):
    """ Convert an array of bytes (assumed to be in BE format) into a
    single value.

    Can probably be abused quite badly as there's no check on the length,
    so it may end up returning a really rather large number.
    """
    ##if isinstance(input, array.array):
    output = 0
    input.reverse()
    for i, c in enumerate(input):
        output += c << 8*i
    return output

def intToBytes(input, length=4, LE=0):
    """ Convert an integer into its machine code equivalent."""
    ##if isinstance(input, int):
    output = array.array('B')
    # Not sure what determines whether it gets an L or not
    while hex(input) != '0x0' and hex(input) != '0x0L':
        output.append(input & 0xFF)
        input = input >> 8
    # Pad output as necessary (also accounts for "0" input)
    while len(output) < length:
        output.append(0)
    if not LE:
        output.reverse()
    ##print output
    return output

def strToArray(input):
    """ Convert a string into its machine code equivalent."""
    ##if isinstance(input, str): 
    output = array.array('B')
    output.fromstring(input)
    return output

def extract(resfile, parentcounter, parentoffset, parentnode):
    """ Recursively trawl through a file, creating directories for
    container blocks and dumping all other blocks into files.
    """
    
    header = getDWord(resfile).tostring()
    # Check if it's a container block
    if header in containertypes or (header[:2] == "IM" and header != "IMHD"):
        # Create the directory representing the block
        message(header + " container block found, creating dir.")
        # Check for a "special" block (has a value stored in the
        # directory tables in the RESOURCE.000 file)
        if header == "SOUN":
            offkey = (parentnode, int(resfile.tell()-4-parentoffset-8))
            if offkey in dsou:
                newpathname = str(parentcounter).zfill(3) + "_" + header + \
                                             "_" + str(dsou[offkey]).zfill(3)
            else:
                print "WARNING! Could not find " + str(offkey) + " in " + header + \
                      " directory lookup!"
                print "The block will be dumped but will not be useable in-game."
                newpathname = str(parentcounter).zfill(3) + "_" + header
                
            # New workaround for Monkey Island 1, there seems to be sound SOUN
            #  blocks that are 32 bytes long, with no sub-data, so they're not
            #  containers. So, we'll just dump those blocks.
            #  (Unfortunately I've just duplicated the dumping code from below,
            #   perhaps it should be moved to a function.)
            blocksize = arrayToInt(getDWord(resfile))
            if blocksize == 32:
                startofblock = resfile.tell()-8
                try:
                    datafile = file(newpathname + ".dmp", 'w+b')
                # What is this exception actually checking for?
                except OSError:
                    print "ERROR: file " + newpathname + \
                          ".dmp could not be opened for writing."
                    resfile.close()
                    os.chdir(basepath)
                    sys.exit(1)
                except IOError, (errno, strerror):
                    print "I/O error(%s): %s" % (errno, strerror)
                    resfile.close()
                    os.chdir(basepath)
                    sys.exit(1)
                # Dump the data to the file
                resfile.seek(-8, 1) # dump the header as well
                # Can't just copy straight from resfile, needs decrypting.
                # However, we can just dump from an array to a file.
                getChunk(resfile, blocksize).tofile(datafile)
                datafile.close()
                return
            else:
                resfile.seek(-4, 1)
                
        elif header == "LFLF":
            if droo.has_key(parentcounter):
                newpathname = str(droo[parentcounter][0]).zfill(3) + "_" + header
            # This is a new room... not really supported
            else:
                print("WARNING: Found a new room, but this is not yet " +
                        "supported by ScummPacker. You will have problems.")
                newpathname = str(parentcounter).zfill(3) + "_" + header
                
        else:
            newpathname = str(parentcounter).zfill(3) + "_" + header
            
        # Create a container block as a directory in the file system
        try:
            os.mkdir(newpathname)
        except OSError:
            # Not sure whether to allow using existing folders or not
            message("WARNING: Could not create folder: " + newpathname + "")
            ##resfile.close()
            ##os.chdir(basepath)
            ##sys.exit("ERROR: Could not create folder " \
            ##    + os.path.join(os.getcwd(), newpathname) + \
            ##    " - make sure that it does not already exist.")
        os.chdir(os.path.join(os.getcwd(), newpathname))
        blocksize = arrayToInt(getDWord(resfile))
        # Work around eccentricities of SOU block (or my bad coding)
        if header == "SOU ":
            blocksize += 8
        message("Size of block is: " + str(blocksize))
        startblockpos = resfile.tell()-8    #subtract 8 for header
        count = 0
        if header == "LFLF":
            if droo.has_key(parentcounter):
                message("Starting LFLF block number " + str(parentcounter) +
                        ", room #" + str(droo[parentcounter][0]) +
                        ", \"" + rnam[droo[parentcounter][0]] + "\"")
            else:
                message("Starting LFLF block number " + str(parentcounter))
        # While we're still in the container block
        while resfile.tell() < startblockpos + blocksize:
            if droo.has_key(parentcounter):
                extract(resfile, count, startblockpos, droo[parentcounter][0])
            else:
                extract(resfile, count, startblockpos, parentcounter)
            count += 1
        # Move back to root container block when done
        os.chdir(os.path.dirname(os.getcwd()))
        if header == "LFLF":
            if droo.has_key(parentcounter):
                print("Finished LFLF block number " + str(parentcounter) +
                        ", room #" + str(droo[parentcounter][0]) +
                        ", \"" + rnam[droo[parentcounter][0]] + "\"")
            else:
                print "Finished LFLF block number " + str(parentcounter)

    # Non-container block
    else:
        message(header + " chunk found, dumping to file.")            
        blocksize = arrayToInt(getDWord(resfile))
        startofblock = resfile.tell()-8
        # Work around discrepencies of sound blocks
        if header in soundtypes:
            blocksize += 8
            header = header.strip() # Make sure there's no spaces in filenames
        # Check for "special" block (contained outside of ROOM and has
        # offsets in a directory table in RESOURCE.000)
        elif header in specialtypes:
            
            if header == "LOFF":
                trackRoomOffsets(resfile)
                
            else:
                # Check if roomid and offset is in directory, then assign
                # an ID to the filename
                # HACK: Have to subtract 8 for some header
                offkey = (parentnode, int(startofblock-parentoffset-8))
                message("Special block found, checking for " + str(offkey))
                directory = specialtypes[header]
    
                if offkey in directory:
                    header = header + "_" + str(directory[offkey]).zfill(3)
                # Warn if the object has no pointer in the directory table thing
                else:
                    # Check for duplicates in the original Monkey Island 2 files
                    # (The duplicates are the "monkey wrench" animation and
                    # Guybrush drinking, talking, and passing out. They're in
                    # rooms 36 and 37 respectively.)
                    global options
                    if options.game == "MI2" and \
                            (header == "COST" and 
                                (offkey == (36, 29664) or
                                 offkey == (37, 27220))
                            ):
                        message("Found known duplicate image - don't panic.")
                    else:
                        print "WARNING! Could not find " + str(offkey) + " in " + \
                              header + " directory lookup!"
                        print "Block will be dumped, but ID will not be recorded " + \
                        "and it will not be useable in-game."
                        
        message("Chunk size is: " + str(blocksize))
        
        # Create file for dumping
        try:
            datafile = file(str(parentcounter).zfill(3) + "_" + header + \
                                                ".dmp", 'w+b')
        # What is this exception actually checking for?
        except OSError:
            print "ERROR: file " + str(parentcounter).zfill(3) + header + \
                  ".dmp could not be opened for writing."
            resfile.close()
            os.chdir(basepath)
            sys.exit(1)
        except IOError, (errno, strerror):
            print "I/O error(%s): %s" % (errno, strerror)
            resfile.close()
            os.chdir(basepath)
            sys.exit(1)
        # Dump the data to the file
        resfile.seek(-8, 1) # dump the header as well
        # Can't just copy straight from resfile, needs decrypting.
        # However, we can just dump from an array to a file.
        getChunk(resfile, blocksize).tofile(datafile)
        datafile.close()

# Can't be bothered making this nice
def extractMonster(monsterfile):
    try:
        os.mkdir("Monster")
    except OSError, (errno, strerror):
        if errno == 17:
            print "Warning: Monster directory already exists"
        else:
            # pass it on to unhandled situation, hurrah!
            raise OSError, (errno, strerror)
    os.chdir(os.path.join(os.getcwd(), "Monster"))
    counter = 0
    while 1:
        try:
            header = getDWord(monsterfile, 0).tostring()
        except EOFError:
            print "Reached end of MONSTER.SOU file."
            monsterfile.close()
            break
        if header == "SOU ":
            os.mkdir("SOU")
            os.chdir(os.path.join(os.getcwd(), "SOU"))
            monsterfile.seek(4,1) # skip block size
            continue
        elif header == "VCTL":
            blocksize = arrayToInt(getDWord(monsterfile, 0))
            monsterfile.seek(-8,1)
            vtcldump = file(str(counter).zfill(4) + '_VCTL', 'wb')
            getChunk(monsterfile, blocksize, 0).tofile(vtcldump)
            vtcldump.close()
        elif header == "Crea":
            monsterfile.seek(23,1) # size starts at 1B = 27, -4 for header
            tempSize = getWord(monsterfile, 0) + getByte(monsterfile, 0)
            tempSize.reverse()
            vocsize = arrayToInt(tempSize) # size is 3 bytes
            vocsize += 31 # size doesn't include 0x1F for VOC file header
            monsterfile.seek(-30,1)
            vocdump = file(str(counter).zfill(4) + '_VOC.voc', 'wb')
            getChunk(monsterfile, vocsize, 0).tofile(vocdump)
            vocdump.close()
        counter += 1
    return

def compactMonster():
    os.chdir(os.path.join(os.getcwd(), 'Monster'))
    newMonster = file('Newmon.sou', 'wb')
    newMonster.write('SOU ')
    newMonster.write(chr(0)*4) # dummy block size
    os.chdir(os.path.join(os.getcwd(), 'SOU'))

    mainlist = os.listdir(os.getcwd())
    ##print mainlist
    filelist = [files for files in mainlist if 
                os.path.isfile(os.path.join(os.getcwd(), files))]
    ##print filelist
    
    for dumpblock in filelist:
        blockfile = file(dumpblock, 'rb')
        ##print dumpblock
        getChunk(blockfile, os.stat(os.path.join(os.getcwd(), dumpblock)).st_size, 0).tofile(newMonster)
        blockfile.close()
    newMonster.close()

def compact():
    currpath = os.getcwd()
    mainlist = os.listdir(currpath)
    # Ignore everythign that doesn't start with "123_" naming convention
    repattern = re.compile("[0-9]{3}_")
    mainlist = [files for files in mainlist if 
                re.match(repattern, files[0:4]) != None]
    mainlist.sort()
    
    message(currpath)
    dirlist = [dir for dir in mainlist if
                os.path.isdir(os.path.join(currpath, dir))]

    # Trawl through subdirectories to create mergefiles to be
    # added to this dir's mergefile.
    for dir in dirlist:
        os.chdir(os.path.join(currpath, dir))
        compact()

    # Ignore files in base dir.
    # Need to change this when compacting directories file (resource.000)
    if currpath == basepath:
        return
    
    # Have to regen list to get .tmp files
    mainlist = os.listdir(currpath)
    mainlist = [files for files in mainlist if 
                re.match(repattern, files[0:4]) != None]
    mainlist.sort()
    filelist = [files for files in mainlist if
                os.path.isfile(os.path.join(currpath, files))]

    currdir = os.path.basename(currpath)
    header = currdir[4:8]
    message("Header = " + header)
    # Create temporary file in parent dir
    os.chdir(os.path.dirname(currpath))
    try:
        if currdir == "000_LECF":
            mergefile = file("Resource.001",'wb')
        else:
            mergefile = file(currdir + ".tmp",'wb')
    except OSError:
        print "ERROR: file "+currdir+".tmp could not be opened for writing."
        os.chdir(basepath)
        sys.exit(1)
    except IOError, (errno, strerror):
        print "I/O error(%s): %s" % (errno, strerror)
        os.chdir(basepath)
        sys.exit(1)
    # Move back for adding files in current block
    os.chdir(currpath)

    # Write a dummy header (will be replaced later)
    mergefile.write('00000000')
    
    # Track room offsets
    if header == 'LECF':
        print "Generating room offset table..."
        if '000_LOFF.dmp' in filelist:
            ##os.rename('000_LOFF.dmp', 'old000_LOFF.bak')
            filelist.remove('000_LOFF.dmp')
        numRooms = len(filelist)
        addHeader(mergefile, "LOFF", 8 + 1 + numRooms*5, seek=0)
        decrypt(intToBytes(numRooms, 1)).tofile(mergefile) # store num rooms
        startOffsetsChunk = mergefile.tell()
        mergefile.write('0'*(numRooms*5)) # reserve room for offsets file
        # don't forget to add offsets table size!
        blocksize = addFiles(mergefile, filelist, currpath) + (8 + 1 + numRooms*5)
        for room in droo.keys():
            # set position to wherever we need to be
            mergefile.seek(startOffsetsChunk + 5*(room-1), 0)
            # Store room num + room offset (encrypted)
            decrypt(intToBytes(room, 1) +
             intToBytes(droo[room], length=4, LE=1)).tofile(mergefile)
    else:
        blocksize = addFiles(mergefile, filelist, currpath)

    # Add how much space the header takes up - eg container block's size
    # is the total size of all contained blocks, plus 8 bytes for the
    # container block's header.
    if header != "SOU":
        blocksize += 8
    else:
        header += " " # SOU needs to be padded to four bytes
    message(header + " container block size in header will be: " + \
                        str(blocksize))
    
    addHeader(mergefile, header, blocksize)

    if header == "LFLF":
        print "Finished packing room " + currdir[0:3]
    # Return final container so we can rename it or something
    elif header == "LECF":
        print "Finished packing LECF"


# TODO: modify files that contain number of other files in them
# eg image headers, NLSCs etc
def addFiles(mergefile, filelist, currpath):
    blocksize = 0

    for f in filelist:
        if options.modify:
            filemode = 'r+b'
        else:
            filemode = 'rb'
        tmpfile = file(f, filemode) # maybe should 'try' this
        tmptype = getDWord(tmpfile, 0).tostring()
        tmpsize = arrayToInt(getDWord(tmpfile, 0))
        fsize = os.stat(os.path.join(currpath, f)).st_size
        fhead = f[4:8]
        intendedsize = fsize

        # Compensate for three-letter block-type filenames (phew!)
        if fhead[-1] == ".":
            fhead = fhead[:-1] + " "
            intendedsize -= 8 # assume all three letter things are sound
            # files, and hence need header size removed

        # Keep track of offsets for required files.
        # Room tracking is dumb, maybe it should add number during extraction?
        # It currently tracks LFLFs rather than ROOMs.
        if fhead == "LFLF":
            roomnum = f[:3] # only 3 chars, ignore '_'
            # Don't subtract 8 as we're tracking ROOMs (first items in
            # LFLF blocks), not LFLFs
            # But why does it need 8 added? hurm...
            # Must be some header I haven't factored into my calculations...
            droo[int(roomnum)] = mergefile.tell() + 8
        # ROOM is a special type but we're tracking LFLFs instead because
        # I'm a big fat dummyhead
        elif fhead in specialtypes and fhead != "ROOM":
            dirdict = specialtypes[fhead]
            if f[9:12] != 'dmp':
                objid = int(f[9:12])
                # Roomnum is determined by the containing LFLF path
                # eg ...\000_LECF\001_LFLF\002_SOUN_170.tmp
                # roomnum will be 001
                roomnum = int(os.path.basename(os.getcwd())[:3])
                dirdict[objid] = (roomnum, mergefile.tell() - 8)
            else:
                print "WARNING: "+ os.path.join(os.getcwd(),f)
                print "  File has no ID - offset will not be generated."
                print "  This file may not be used in-game!"

        # Overwrite header if necessary (and it's not a mergefile)
        # Not a good idea to modify files not created by the compaction process
        if options.modify and f[-4:] != '.tmp' and \
           (tmptype != fhead or intendedsize != tmpsize):
                print "Modifying block " + fhead + ", " + str(intendedsize) + \
                    " (current header is " + tmptype + ", " + str(tmpsize) + ")"
                tmpfile.seek(0,0)
                addHeader(tmpfile, fhead, intendedsize, encrypted=0)
        # Ignore header in file, generate our own.
        addHeader(mergefile, fhead, intendedsize, seek=0)        
        
        # Don't encrypt it if it's an already encryted mergefile
        # NOTE: encryption should only take place when reading
        # an entire .dmp file and when writing a CONTAINER BLOCK's header
        # (that is, a .tmp file -- overwriting .dmp file headers should
        # NOT BE ENCRYPTED)
        if tmpfile.name[-4:] == '.tmp':
            getChunk(tmpfile, fsize-8, encrypted=0).tofile(mergefile)
        else:
            getChunk(tmpfile, fsize-8).tofile(mergefile)
        tmpfile.close()
        # Delete temp files (merged directories)
        if f[-4:] == '.tmp' and f != '000_LECF.tmp':
            os.remove(os.path.join(currpath, f))
        blocksize += fsize

    return blocksize


def addHeader(mergefile, blocktype, blocksize, encrypted=1, seek=1):
    """ Write 8-byte header (encrypted OR unencrypted) to block file."""
    if seek:
        mergefile.seek(0,0)
    # See what I did here? That's right. I know Python.
    # (*cough*)
    crypt = encrypted and decrypt or (lambda x: x)
    crypt(strToArray(blocktype) + intToBytes(blocksize)).tofile(mergefile)


def trackOffsets(dirfile, dumpall=0):
    """ Trawl through a file of directory tables, storing room + offset keys and
    ID values in dictionaries for appropriate block types, and dumping all
    other block types.

    Basically, the ID is the position in the dir file, and we identify
    it when extracting by comparing it to the room and offset in that room.
    """
    
    while 1:
        try:
            header = getDWord(dirfile).tostring()
        except EOFError:
            print "Reached end of directories file."
            dirfile.close()
            break
        
        blocksize = arrayToInt(getDWord(dirfile))
        
        # Check for something that we know what to do with
        if dumpall != 1 and (header == "DSCR" or header == "DCHR" or 
                            header == "DCOS" or header == "DSOU" or
                            header == "RNAM"):
            message(header + " chunk found, processing.")
            if header == "DSCR":
                directory = dscr
            elif header == "DCHR":
                directory = dchr
            elif header == "DCOS":
                directory = dcos
            elif header == "DSOU":
                directory = dsou
            elif header == "RNAM":
                # This isn't very useful. I wanted to get the real room numbers
                #  from RNAM, but they're not in sequential order here, so
                #  we do that with LOFF.
                #directory = rnam
                start = dirfile.tell()
                roomOrder = 1
                roomNo = arrayToInt(getByte(dirfile))
                while roomNo != 0:
                    # Room Name is a 9-byte string, XORed with 0xFF (and 0x69)
                    # (8-bytes plus 0 termination)
                    roomName = getChunk(dirfile, 9)
                    for i, byte in enumerate(roomName):
                        roomName[i] = byte ^ 0xFF
                    roomName = roomName.tostring().strip('\x00')
                    
                    rnam[roomNo] = roomName
                        
                    roomNo = arrayToInt(getByte(dirfile))
                    roomOrder += 1
                    
                # Dump this anyway
                dirfile.seek(start, 0)
                message(header + " chunk found, dumping.")
                dirfile.seek(-8, 1)
                dmpfile = file(header + ".dmp", 'w+b')
                getChunk(dirfile, blocksize).tofile(dmpfile)
                dmpfile.close()
                continue
            numitems = arrayToInt(getWordLE(dirfile))
            message(str(numitems) + " items found.")
            roomlist = []
            for room in xrange(numitems):
                roomlist.append(arrayToInt(getByte(dirfile)))
            # Store a tuple of room ID and offset within the room as keys.
            # Items are numbered sequentially.
            for i in xrange(numitems):
                directory[(roomlist[i], arrayToInt(getDWordLE(dirfile)))] = i+1
            
        else: # Dump other blocks - will be used as dummy blocks when packing
            message(header + " chunk found, dumping.")
            dirfile.seek(-8, 1)
            dmpfile = file(header + ".dmp", 'w+b')
            getChunk(dirfile, blocksize).tofile(dmpfile)
            dmpfile.close()
            continue

def trackRoomOffsets(dirfile):
    """ Tracks room offsets from a LOFF block."""
    
    print "Reading room numbers & offsets from LOFF block..."
    start = dirfile.tell()
    numRooms = arrayToInt(getByte(dirfile))
    
    for i in xrange(1, numRooms + 1):
        roomNo = arrayToInt(getByte(dirfile))
        roomOffset = arrayToInt(getDWordLE(dirfile)) # not actually used
        
        droo[i] = (roomNo, roomOffset)
        
    dirfile.seek(start, 0)

# Maybe the room offsets should also be handled here
def createOffsets(blocktype):
    """ Create a file consisting of room numbers and offsets.

    Format of offset tables is expected to be:
      (qword)header,
      (word)number_of_items,
      number_of_items*(byte)room_id,
      number_of_items*(dword)offset_in_room
    """

    offdir = dirspecialtypes[blocktype]
    tablefile = file(blocktype + ".gen", 'wb')
    idsetc = offdir.keys()
    idsetc.sort()
    ##numEntries = len(offdir)
    numEntries = idsetc[-1]  # Not just len() as there could be blank entries

    # Pad the file out if it's below a certain size (hopefully fixes
    # problems when using the original interpreter)
    # Blank spaces in SCRP offset table must have some unknown meaning?
    # Or there's a minsize in MAXS? Who knows...
    if blocktype == "DSCR" and numEntries < 199:
        numEntries = 199

    addHeader(tablefile, blocktype, 8 + 2 + numEntries + numEntries*4, 0)
    intToBytes(numEntries, 2, 1).tofile(tablefile)
    startOfBlock = tablefile.tell() # unnecessary, should always be 10
    # Reserve room for offsets files
    tmpfiller = array.array('B')
    tmpfiller.append(0)
    (tmpfiller * (numEntries + numEntries*4)).tofile(tablefile)
    
    for id in offdir.keys():
        # Write room number
        tablefile.seek(startOfBlock + id-1, 0)
        intToBytes(offdir[id][0], 1).tofile(tablefile)
        # Write offset within room
        tablefile.seek(startOfBlock + numEntries + (id-1)*4, 0)
        intToBytes(offdir[id][1], 4, 1).tofile(tablefile)
    tablefile.close()


def checkArguments(args):
    if len(args) > 0:
        # Absolute or relative path
        if os.path.isdir(args[0]):
            os.chdir(args[0])
        elif os.path.isdir(os.path.join(os.getcwd(),args[0])):
            os.chdir(os.path.join(os.getcwd(),args[0]))
        else:
            print "Invalid path specified."
            sys.exit(2)
    return os.getcwd()

# Pretty poor structure here
def main(argv):

    parser = OptionParser(usage="%prog [options] arg1",
                      version="SCUMM Packer v0.2")
    parser.add_option("-e", "--extract", action="store_true",
                      dest="extract", default=False,
                      help="Dump files from two resource files.")
    parser.add_option("-p", "--pack", action="store_true",
                      dest="pack", default=False,
                      help="Pack previously extracted files into "
                      "two new resource files.")    
    parser.add_option("-g", "--game", action="store",
                      dest="game", default="MI2",
                      choices=resourcenames.keys(),
                      help="The game to pack/unpack. MI1/MI2/FOA "
                      "[default: MI2]")
    parser.add_option("-s", "--sounds", action="store_true",
                      dest="sounds", default=False,
                      help="Extract or merge a MONSTER.SOU file.")
    parser.add_option("-o", "--offsets", action="store_true",
                      dest="compoffs", default=False,
                      help="[Expert] Dump or merge only offset files. "
                      "No offset tables are generated.")
    parser.add_option("-m", "--modify", action="store_true",
                      dest="modify", default=False,
                      help="[Expert] Modify dumped files and fix any invalid headers.")
    parser.add_option("-n", "--nogen", action="store_true",
                      dest="nogen", default=False,
                      help="[Expert] Don't generate offset tables. "
                      "Specify this when you want to pack a block other than "
                      "LECF.")
    parser.add_option("-d", "--usedmp", action="store_true",
                      dest="usedmp", default=False,
                      help="[Expert] Use previously dumped offset tables.")
    parser.add_option("-v", "--verbose", action="store_true",
                      dest="verbose", default=False,
                      help="Display extended messages. "
                      "Currently very large and messy output - "
                      "it's a good idea to redirect output to "
                      "a log file if you enable this.")

    global options
    options, args = parser.parse_args()

    global basepath
    basepath = checkArguments(args)

    global resfilename
    global dirfilename

    # Extraction
    if options.extract == 1:
        try:
            resfile = None
            dirfile = None
            monster = None

            if options.sounds == 1:
                monster = file("monster.sou",'rb')
                extractMonster(monster)
                monster.close()
                os.chdir(basepath)
                print "Done!"
                return 0
            
            dirfilename, resfilename = resourcenames[options.game]
            
            # Open the file
            try:
                resfile = file(resfilename,'rb')
            except IOError:
                print "ERROR: file " + resfilename + " could not be opened."
                return 1
            # Open the directories file
            try:
                dirfile = file(dirfilename,'rb')
            except IOError:
                print "ERROR: file " + dirfilename + " could not be opened."
                return 1


            # Get info for objects with offsets in dir file (Resource.000)
            print "Generating script IDs from directories file..."
            trackOffsets(dirfile, options.compoffs)

            if options.compoffs == 0:
                # Extract files from Resource.001
                print "Expectorating from " + resfilename + "..."
                extract(resfile, 0, 0, 0)
            
            print "Extraction complete!"
        finally:
            if resfile:
                resfile.close()
            if dirfile:
                dirfile.close()
                
    # Packing
    elif options.pack == 1:
        if options.sounds == 1:
                compactMonster()
                os.chdir(basepath)
                print "Done!"
                return 0
        
        if options.compoffs == 0:
            print "Packing main resources..."
            compact()

            if options.nogen == 0:
                print "Generating offset tables..."
                os.chdir(basepath)
                try:
                    createOffsets("DSCR")
                    createOffsets("DCHR")
                    createOffsets("DCOS")
                    createOffsets("DSOU")
                except IndexError:
                    print "ERROR: No offsets generated!"
                    os.chdir(basepath)
                    return
        
        
        # List is in the specific order to be merged
        if options.usedmp == 1:
            filelist = ['RNAM.dmp', 'MAXS.dmp', 'DROO.dmp', 'DSCR.dmp',
                    'DSOU.dmp', 'DCOS.dmp', 'DCHR.dmp', 'DOBJ.dmp']
        # If not using dumped offset tables and we're not generating them,
        # we can skip trying to merge them.
        # Useful for merging blocks rather than entire LECF
        elif options.nogen == 1:             
            print "Packing complete!"
            os.chdir(basepath)
            return
        else:
            filelist = ['RNAM.dmp', 'MAXS.dmp', 'DROO.dmp', 'DSCR.gen',
                    'DSOU.gen', 'DCOS.gen', 'DCHR.gen', 'DOBJ.dmp']
        print "Merging offset tables into Resource.000..."
        indexfile = file('Resource.000', 'wb')
        for tablefile in filelist:
            tf = file(tablefile, 'rb')
            message("Adding " + tablefile + "...")
            getChunk(tf, os.stat(
                os.path.join(os.getcwd(), tablefile)
                ).st_size).tofile(indexfile)
            tf.close()
        indexfile.close()

        print "Packing complete!"
    else:
        print "Please choose either -e or -p to extract or pack."
        parser.print_help()
        
    os.chdir(basepath)

if __name__ == "__main__": main(sys.argv[1:])

