from sys import argv
from base_component import BaseComponent
from utils import convert_fixed
from myhdl import always, block, Signal, intbv


class KernelROM(BaseComponent):
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

    :param clk: clock signal
    :type clk: std_logic
    :param q: the concatenated output values of the ROM
    :type q: std_logic_vector
    """

    def __init__(self, weights=[], **kwargs):
        super().__init__(**kwargs)
        print("%-24s%-10i%-10i%-16i%-10s%-10s" % ("KernelROM", self.layer_id,
              self.unit_id, self.channel_id, "-", "-"))

        unit_weights = convert_fixed(weights)
        self.CONTENT = tuple(unit_weights)
        return

    def get_signals(self):
        return {
            "clk": Signal(False),
            "q": Signal(intbv(0)[9*16:])
        }

    @block
    def rtl(self, clk, q):
        @always(clk)
        def logic():
            q.next[16:0] = self.CONTENT[0]
            q.next[32:16] = self.CONTENT[1]
            q.next[48:32] = self.CONTENT[2]
            q.next[64:48] = self.CONTENT[3]
            q.next[80:64] = self.CONTENT[4]
            q.next[96:80] = self.CONTENT[5]
            q.next[112:96] = self.CONTENT[6]
            q.next[128:112] = self.CONTENT[7]
            q.next[144:128] = self.CONTENT[8]
        return logic


if __name__ == '__main__':
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = KernelROM()
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
