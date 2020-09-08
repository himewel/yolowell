import logging

from utils import print_info
from max_pool_unit import MaxPoolUnit

from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.synthesizer.hObjList import HObjList


class MaxPoolLayer(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, width=16, filters=0, binary=False, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.width = width
        self.filters = filters
        self.binary = binary
        self.top_entity = False
        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.en_pool = Signal()
        self.input = VectSignal(4*self.width*self.filters)
        self.output = VectSignal(self.width*self.filters)._m()

        self.pool_unit = HObjList(MaxPoolUnit(
            width=self.width, binary=self.binary, layer_id=self.layer_id,
            unit_id=i, channel_id=self.channel_id, process_id=self.process_id)
            for i in range(self.filters))

        name = "MaxPoolLayerL{layer}F{filter}C{channel}P{process}".format(
            layer=self.layer_id,
            filter=self.unit_id,
            channel=self.channel_id,
            process=self.process_id)
        self._name = name
        self._hdl_module_name = name

    def _impl(self):
        for i in range(self.filters):
            pool_unit = self.pool_unit[i]
            pool_unit.clk(self.clk)
            pool_unit.rst(self.rst)
            pool_unit.en_pool(self.en_pool)
            pool_unit.input(self.input[4*self.width*(i+1):4*self.width*i])
            self.output[self.width*(i+1):self.width*i](pool_unit.output)


if __name__ == '__main__':
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if (len(argv) > 1):
        path = argv[1]

        get_std_logger()
        unit = MaxPoolLayer(width=16)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
