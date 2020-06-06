from abc import abstractmethod


class ComponentClass():
    """
    This class serves as template to build the components in vhdl. The methods
    rtl and get_signal are obrigated to be implemented. The rtl method should
    implement a method with @block decorator describeing the desired the logic.

    The get_signals method returns the input and output signals gather in a
    dict. The convert method call get_signals and rtl methods to generate the
    vhdl files. Each class builded in ComponentClass have identifiers to layer,
    desired channel input and which unit inside the superior abstraction.
    """
    def __init__(self, layer_id=0, channel_id=0, unit_id=0):
        self.n_channels = [3, 16, 32, 64, 16, 32, 64, 16, 32, 64]
        self.n_filters = [16, 32, 64, 64, 128, 256, 512, 1024, 32, 64]
        self.n_units = [432, 4608, 18432, 73728, 294912, 1179648, 4718592,
                        262144, 1179648, 130560]
        self.layer_id = layer_id
        self.channel_id = channel_id
        self.unit_id = unit_id

    @abstractmethod
    def rtl(self):
        pass

    @abstractmethod
    def get_signals(self):
        pass

    def convert(self, name="", path=""):
        """
        This function convert the logic implemented in the rtl method in a vhdl
        file. The signal widths can be foun in the rtl method description.

        :param name: A string with the name file to vhdl file generated and the
        name to the VHDL entity.
        :type name: str
        :param path: A string with the path where the output file will be
        writed.
        :type path: str
        """
        signals = self.get_signals()
        entity = self.rtl(**signals)
        entity.convert(hdl="vhdl", name=name, path=path)

    def read_floats(self, PATH, FILE, start=0, final=0):
        """
        This function reads the file passed by the parameters and return the
        float list of values readed in the file.
        """
        weights = []
        with open("{}/{}".format(PATH, FILE), "r") as file:
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

    def convert_fixed(self, weights):
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
                num = num.replace("0", "x")
                num = num.replace("1", "0")
                num = num.replace("x", "1")
                num = int(num, 2) + 1
            else:
                num = int(num, 2)

            fixed_weights.append(
                int("{}{}".format('{0:01b}'.format(sinal),
                                  '{0:015b}'.format(int(num))), 2))
        return fixed_weights
