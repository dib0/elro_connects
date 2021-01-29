def get_string_from_ascii(input):
    """
    This function is reversed engineered and translated to python
    based on the CoderUtils class in the ELRO Android app

    :param input: A hex string
    :return: A string
    """
    try:
        if len(input) != 32:
            return ''

        byt = bytearray.fromhex(input)
        name = "".join(map(chr, byt))
        name = name.replace("@", "").replace("$", "")
    except:
        return ''

    return name
