import array
# 0 = always display (errors)
# 1 = warnings, verbose
# 2 = debug
TEXT_OUTPUT_LEVEL = 1
def message(text, level=2):
    if level <= TEXT_OUTPUT_LEVEL:
        print(text)
        
def error(text):
    message(text, 0)
    
def information(text):
    message(text, 1)
    
def debug(text):
    message(text, 2)
    
    
#def write_byte(file, byte):
    #file.write()
    
def crypt(inVal, cryptVal):
    if cryptVal is None:
        return inVal
    if type(inVal) is str:
        outString = ''
        for c in inString:
            outString += c ^ cryptVal
        return outString
    elif type(inVal) is array.ArrayType:
        for i, byte in enumerate(inVal):
            inVal[i] = byte ^ cryptVal
        return inVal
    raise ScummPackerException("Could not encrypt values of type: " + str(type(inVal)))

LE = False
BE = True
def strToInt(inVal, isBE=False):
    outVal = 0
    #if type(inVal) is str:
    if isBE:
        inVal = reversed(inVal)
    for i, c in enumerate(inVal):
        outVal += ord(c) << 8*i
        #return outVal
    #elif type(inVal) is array.ArrayType:
        #if isBE:
            #inVal.reverse()
        #for i, c in enumerate(inVal):
            #outVal += c << 8*i
        #return outVal
    #raise ScummPackerException("Could not convert values of type: " + str(type(inVal)) + " to int.")


class ScummPackerException(ApplicationException):
    pass
