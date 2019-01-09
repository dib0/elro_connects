# This calss is reversed engineered and translated to python
# based on the CoderUtils class in the ELRO Android app

class coder_utils:

    def getStringFromAscii(input):
        try:
            if len(input) != 32:
                return ''
            
            name = bytearray.fromhex(input).decode('gbk')
        except:
            return ''
