import logging
from math import ceil, log

from utils import print_info
from scatter_unit import ScatterUnit

from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.synthesizer.hObjList import HObjList
from hwt.interfaces.utils import propagateClkRst, addClkRst


class BufferLayer(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, scattering=3, binary=False, width=416, filters=16,
                 **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.scattering = scattering
        self.n_outputs = scattering * scattering
        self.mode_width = scattering + 1
        self.width = 1 if binary else width
        self.filters = filters
        self.binary = binary

        self.mem_size = int(2 ** ceil(log(width, 2)))
        self.counter_size = int(log(self.mem_size, 2)) + 1

        self.top_entity = False
        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        addClkRst(self)
        self.input = VectSignal(self.data_width*self.filters)
        self.input_counter = VectSignal(self.counter_width)
        self.output_counter = VectSignal(self.counter_width)
        self.en_zero = Signal()
        self.mode = VectSignal(self.size+1)
        self.en_read = Signal()
        self.en_write = Signal()
        self.output = \
            VectSignal(self.n_outputs*self.data_width*self.filters)._m()

        self.scatter_units = HObjList(ScatterUnit(
            layer_id=self.layer_id, unit_id=i, mem_size=self.mem_size,
            counter_size=self.counter_size, binary=self.binary,
            size=self.scattering, log_level=self.log_level+1)
            for i in range(self.filters))

        name = f"BufferLayerL{self.layer_id}"
        self._name = name
        self._hdl_module_name = name

    def _impl(self):
        propagateClkRst(self)
        for i in range(self.filters):
            scatter_unit = self.scatter_units[i]
            scatter_unit.input_counter(self.input_counter)
            scatter_unit.output_counter(self.output_counter)
            scatter_unit.en_zero(self.en_zero)
            scatter_unit.mode(self.mode)
            scatter_unit.en_read(self.en_read)
            scatter_unit.en_write(self.en_write)
            scatter_unit.input(self.input[self.width*(i+1):self.width*i])
            self.output[self.width*(i+1):self.width*i](scatter_unit.output)


if __name__ == '__main__':
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if (len(argv) > 1):
        path = argv[1]

        get_std_logger()
        unit = BufferLayer(width=16)
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
