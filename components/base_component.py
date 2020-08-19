from abc import abstractmethod


class BaseComponent():
    """
    This class serves as template to build the components in vhdl. The methods
    rtl and get_signal are obrigated to be implemented. The rtl method should
    implement a method with @block decorator describeing the desired the logic.

    The get_signals method returns the input and output signals gather in a
    dict. The convert method call get_signals and rtl methods to generate the
    vhdl files. Each class builded in BaseComponent have identifiers to layer,
    desired channel input and which unit inside the superior abstraction.

    :param layer_id: layer index
    :type layer_id: int
    :param unit_id: index of the unit inside a layer
    :type unit_id: int
    :param channel_id: index of the channel input inside a unit
    :type channel_id: int
    """

    def __init__(self, layer_id=0, channel_id=0, unit_id=0, convert=""):
        self.n_channels = [3, 16, 32, 64, 16, 32, 64, 16, 32, 64]
        self.n_filters = [16, 32, 64, 64, 128, 256, 512, 1024, 32, 64]
        self.n_units = [432, 4608, 18432, 73728, 294912, 1179648, 4718592,
                        262144, 1179648, 130560]
        self.layer_id = layer_id
        self.channel_id = channel_id
        self.unit_id = unit_id

        self.logger.info("", extra={
            'layer_id': self.layer_id,
            'channel_id': self.channel_id,
            'unit_id': self.unit_id
        })

        if (convert != ""):
            self.convert(convert)

    @abstractmethod
    def rtl(self):
        pass

    @abstractmethod
    def get_signals(self):
        pass

    @abstractmethod
    def fix_syntax(self, name="", path=""):
        pass

    def convert(self, name="", path=""):
        """
        This function convert the logic implemented in the rtl method in a vhdl
        file. The signal widths can be foun in the rtl method description.

        :param name: A string with the name file to vhdl file generated and \
        the name to the VHDL entity.
        :type name: str
        :param path: A string with the path where the output file will be \
        writed.
        :type path: str
        """
        signals = self.get_signals()
        entity = self.rtl(**signals)
        print("Converting vhd file... ", end="")
        entity.convert(hdl="vhdl", name=name, path=path)
        self.fix_syntax(name=name, path=path)
        print("Ok!")
