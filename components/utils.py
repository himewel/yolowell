def read_floats(file_path="", start=0, final=0):
    """
    This function reads the file passed by the parameters and return the
    float list of values readed in the file.
    """
    weights = []
    with open("{}".format(file_path), "r") as file:
        text = file.read().replace("\n", "").replace("\t", "")
        text = text.split("{")
        text = text[1].split("}")
        text = text[0].split(",")

        try:
            for i in range(start, len(text) if final == 0 else final):
                weights.append(float(text[i]))
        except Exception:
            pass

    return weights

def convert_fixed(weights=[]):
    """
    This funtion receives a list of weights and convert each one of the
    values to fixed point representation. By default, the decimal portion
    of the values are represented with 11 bits while the int portion is
    represented with 4 bits. One bit is reserved to the magnitude
    representation, totalizing 16 bits of fixed point representation.
    """
    fixed_weights = []
    for w in weights:
        sinal = 0 if w > 0 else 1
        inteiro = int(abs(w))
        decimal = abs(w - inteiro)

        while decimal*10 <= 2**11 and decimal != 0:
            decimal *= 10

        num = "{}{}".format('{0:04b}'.format(inteiro),
                            '{0:011b}'.format(int(decimal)))

        if (sinal == 1):
            num = num.replace("0", "-")
            num = num.replace("1", "0")
            num = num.replace("-", "1")
            num = int(num, 2) + 1
        else:
            num = int(num, 2)

        fixed_weights.append(
            int("{}{}".format('{0:01b}'.format(sinal),
                              '{0:015b}'.format(int(num))), 2))
    return fixed_weights
