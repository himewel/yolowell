from sys import argv
from ComponentClass import ComponentClass
from myhdl import always, block, Signal, intbv


class BnROM(ComponentClass):
    """
    This class implements some functions to read the weights file and generate
    a ROM with the values identifyied by the layer_id, channel_id and unit_id.
    The clock signal serves only to give a signal to the sensitive list of the
    process, registers should not be generated.

    Both path to weights and data arrays about the weight organizations should
    be informed or implemented. The data to tiny_yolov3 first layer weights is
    informed in the __init__ method. To generate the kernel ROMs, this class
    provides some methods to read the weights, convert them to binary values
    and convert them to fixed point representation. By default, each ROM has
    only nine values to feed the convolutional units.
    """

    def __init__(self, mean_file="yolov3_tiny/yolov3_tiny_mean.h",
                 scale_file="yolov3_tiny/yolov3_tiny_scale.h",
                 variance_file="yolov3_tiny/yolov3_tiny_variance.h",
                 bias_file="yolov3_tiny/yolov3_tiny_biases.h",
                 path="/home/welberthime/Documentos/nios-darknet/include",
                 **kwargs):
        super().__init__(**kwargs)
        print(8*" "+"- Creating BnROM layer={} unit={} channel={}...".format(
            self.layer_id, self.unit_id, self.channel_id))
        # mean = self.read_floats(path, mean_file)
        # variance = self.read_floats(path, variance_file)
        # scale = self.read_floats(path, scale_file)
        # bias = self.read_floats(path, bias_file)

        self.bn_content = Signal(intbv(3)[16:])
        self.ssi_content = Signal(intbv(3)[16:])
        return

    def get_signals(self):
        """
        :param clk: clock signal
        :type clk: std_logic
        :param q: the concatenated output values of the ROM
        :type q: std_logic_vector
        """
        return {
            "clk": Signal(False),
            "q_bn": Signal(intbv(0)[16:]),
            "q_ssi": Signal(intbv(0)[16:])
        }

    @block
    def rtl(self, clk, q_bn, q_ssi):
        @always(clk)
        def logic():
            q_bn.next = self.bn_content
            q_ssi.next = self.ssi_content
        return logic


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = BnROM()
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
