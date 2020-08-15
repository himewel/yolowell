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

def convert_fixed(weights=[], integer_portion=4, decimal_portion=11):
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

        while decimal*(decimal_portion-1) <= 2**decimal_portion and decimal != 0:
            decimal *= 10

        integer_mask = '{0:0' + str(integer_portion) +'b}'
        decimal_mask = '{0:0' + str(decimal_portion) +'b}'
        num = "{}{}".format(integer_mask.format(inteiro),
                            decimal_mask.format(int(decimal)))

        if (sinal == 1):
            num = num.replace("0", "-")
            num = num.replace("1", "0")
            num = num.replace("-", "1")
            num = int(num, 2) + 1
        else:
            num = int(num, 2)

        fixed_weight_mask = \
            '{0:0' + str(integer_portion + decimal_portion) + 'b}'
        fixed_weights.append(
            int("{}{}".format('{0:01b}'.format(sinal),
                              fixed_weight_mask.format(int(num))), 2))
    return fixed_weights
