import logging

from utils import print_info

from hwt.code import If
from hwt.hdl.types.bits import Bits
from hwt.interfaces.std import Signal, VectSignal
from hwt.synthesizer.unit import Unit
from hwt.serializer.mode import serializeParamsUniq


@serializeParamsUniq
class ScatterUnit(Unit):
    """
    .. hwt-schematic::
    """

    def __init__(self, binary=True, mem_size=256, counter_size=8, width=16,
                 size=3, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.binary = binary
        self.counter_size = counter_size
        self.top_entity = False

        self.data_width = 1 if binary else width
        self.addr_width = mem_size
        self.counter_width = counter_size
        self.size = size
        self.n_outputs = size * size

        print_info(self, **kwargs)
        super().__init__()

    def _declr(self):
        self.clk = Signal()
        self.rst = Signal()
        self.input = VectSignal(self.data_width)
        self.input_counter = VectSignal(self.counter_width)
        self.output_counter = VectSignal(self.counter_width)
        self.en_zero = Signal()
        self.mode = VectSignal(self.size+1)
        self.en_read = Signal()
        self.en_write = Signal()
        self.output = VectSignal(self.n_outputs*self.data_width)._m()

        name = f"ScatterUnitL{self.layer_id}"
        self._name = name
        self._hdl_module_name = name

    def _impl(self):
        data_signal = Bits(bit_length=self.data_width, force_vector=True)
        counter_signal = Bits(bit_length=self.counter_width, force_vector=True)

        output_list = [self._sig(name=f"output_list_{i}", dtype=data_signal)
                       for i in range(self.n_outputs)]

        buffer_addr = []
        line_buffer = []
        for i in range(self.size + 1):
            buffer_addr.append(self._sig(
                name=f"buffer_addr_{i}", dtype=counter_signal))
            line_buffer.append(self._sig(
                name=f"ram_{i}", dtype=data_signal[self.addr_width]))

        If(
            self.clk._onRisingEdge(),
            self.__counter_assignment(buffer_addr),
            If(
                self.en_write,
                self.__input_selection(buffer_addr, line_buffer)
            )
        )

        If(
            self.rst,
            *(output_list[i](0) for i in range(self.n_outputs))
        ).Elif(
            self.clk._onRisingEdge(),
            If(
                self.en_read,
                self.__output_selection(buffer_addr, line_buffer, output_list)
            ),
        )

        for i in range(self.n_outputs):
            self.output[(i+1)*self.data_width:
                        i*self.data_width](output_list[i])

    def __counter_assignment(self, buffer_addr):
        condition = If(
            self.mode[0],
            *self.__input_tuple_assignment(0, buffer_addr)
        )
        for i in range(1, self.size+1):
            condition = condition.Elif(
                self.mode[i],
                *self.__input_tuple_assignment(i, buffer_addr)
            )
        return condition

    def __input_tuple_assignment(self, index, buffer_addr):
        list_assignment = []
        for i in range(self.size+1):
            counter = self.input_counter if i == index else self.output_counter
            list_assignment.append(buffer_addr[i](counter))
        return (list_assignment)

    def __input_selection(self, buffer_addr, line_buffer):
        condition = If(
            self.mode[0],
            line_buffer[0][buffer_addr[0]](self.input)
        )
        for i in range(1, self.size+1):
            condition = condition.Elif(
                self.mode[i],
                line_buffer[i][buffer_addr[i]](self.input)
            )
        return condition

    def __output_tuple_assignment(self, buffer_addr, line_buffer, output_list):
        indexes = list(range(self.size+1))
        indexes.remove(0)
        condition = If(
            self.mode[0],
            *([output_list[i](line_buffer[indexes[i]][buffer_addr[indexes[i]]])
              for i in range(self.size)])
        )
        for i in range(1, self.size+1):
            indexes = list(range(self.size+1))
            indexes.remove(i)
            condition = condition.Elif(
                self.mode[i],
                *([output_list[i](
                  line_buffer[indexes[i]][buffer_addr[indexes[i]]])
                  for i in range(self.size)])
            )
        return condition

    def __output_selection(self, buffer_addr, line_buffer, output_list):
        return If(
            self.en_zero,
            *([output_list[i](0) for i in range(self.size)])
        ).Else(
            self.__output_tuple_assignment(
                buffer_addr, line_buffer, output_list),
            *([output_list[i](output_list[i-self.size])
              for i in range(self.size, self.n_outputs)])
        )


if __name__ == '__main__':
    from sys import argv
    from utils import to_vhdl, get_std_logger

    if (len(argv) > 1):
        path = argv[1]

        get_std_logger()
        unit = ScatterUnit()
        to_vhdl(unit, path)
    else:
        print("file.py <outputpath>")
