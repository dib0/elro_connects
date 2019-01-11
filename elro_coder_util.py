# This class is reversed engineered and translated to python
# based on the CoderUtils class in the ELRO Android app

class coder_utils:

    def getStringFromAscii(input):
        try:
            if len(input) != 32:
                return ''
            
            byt = bytearray.fromhex(input)
            name = "".join(map(chr, byt))
            name = name.replace("@", "").replace("$", "")
        except:
            return ''
        
        return name
