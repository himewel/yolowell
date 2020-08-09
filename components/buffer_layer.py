from sys import argv
from math import ceil, log
from base_component import BaseComponent
from tri_scatter_unit import TriScatterUnit
from myhdl import always_comb, always_seq, block, Signal, intbv, ResetSignal


class BufferLayer(BaseComponent):
    def __init__(self, scattering=3, binary=False, width=416, filters=16,
                 **kwargs):
        super().__init__(**kwargs)
        print("%-24s%-10i%-10i%-16i%-10i%-10s" % ("BufferLayer",
              self.layer_id, self.unit_id, self.channel_id, filters, "-"))

        self.filters = filters

        # set input and output width
        self.PORT_WIDTH = 1 if binary else 16
        self.mode_width = scattering + 1
        self.size = scattering * scattering

        mem_size = int(2 ** ceil(log(width, 2)))
        self.counter_size = int(log(mem_size, 2)) + 1

        if (scattering == 3):
            self.scattering_units = [TriScatterUnit(
                layer_id=self.layer_id, channel_id=i, mem_size=mem_size,
                counter_size=self.counter_size, binary=binary)
                for i in range(self.filters)]
        # elif (scattering == 2):
        #     self.scatter_units = [DualScatterUnit(
        #         layer_id=self.layer_id, unit_id=i, width=width,
        #         binary=binary) for i in range(self.filters)]
        # elif (scattering == 1):
        #     self.scatter_units = [MonoScatterUnit(
        #         layer_id=self.layer_id, unit_id=i, width=width,
        #         binary=binary) for i in range(self.filters)]
        return

    @block
    def rtl(self, clk, reset, input, output, en_zero, mode, en_read, en_write,
            en_read_counter, en_write_counter):
        wire_input_channels = [Signal(intbv(0)[self.PORT_WIDTH:])
                               for _ in range(self.filters)]
        wire_output_channels = [Signal(intbv(0)[self.PORT_WIDTH*self.size:])
                                for _ in range(self.filters)]

        input_counter = Signal(intbv(0)[self.counter_size:])
        output_counter = Signal(intbv(0)[self.counter_size:])

        scattering_units = [self.scattering_units[i].rtl(
            clk=clk, reset=reset, input=wire_input_channels[i],
            output=wire_output_channels[i], input_counter=input_counter,
            output_counter=output_counter, en_zero=en_zero, mode=mode,
            en_read=en_read, en_write=en_write) for i in range(self.filters)]

        @always_comb
        def combinational_input_wires():
            for i in range(self.filters):
                wire_input_channels[i].next = \
                    input[(i+1)*self.PORT_WIDTH:i*self.PORT_WIDTH]

        @always_comb
        def combinational_output_wires():
            aux = intbv(0)[self.filters*self.size*self.PORT_WIDTH:]
            for i in range(self.filters):
                aux[(i+1)*self.PORT_WIDTH*self.size:
                    i*self.PORT_WIDTH*self.size] = wire_output_channels[i]
            output.next = aux

        @always_seq(clk.posedge, reset=reset)
        def process():
            if (en_read_counter == 1):
                output_counter.next = output_counter + 1
            if (en_write_counter == 1):
                input_counter.next = input_counter + 1

        return (scattering_units, combinational_input_wires,
                combinational_output_wires, process)

    def get_signals(self):
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "input": Signal(intbv(0)[self.filters*self.PORT_WIDTH:]),
            "output": \
                Signal(intbv(0)[self.size*self.filters*self.PORT_WIDTH:]),
            "mode": Signal(intbv(0)[self.mode_width:]),
            "en_zero": Signal(False),
            "en_read": Signal(False),
            "en_write": Signal(False),
            "en_read_counter": Signal(False),
            "en_write_counter": Signal(False)
        }


if (__name__ == '__main__'):
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = BufferLayer(scattering=3, binary=True, width=416, filters=16)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
