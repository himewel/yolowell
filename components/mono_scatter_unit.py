from sys import argv
import logging
from math import ceil, log
from base_component import BaseComponent
from myhdl import (always_comb, always_seq, always, block, Signal, intbv,
                   ResetSignal)


class MonoScatterUnit(BaseComponent):
    """
    This block implements a unit to fill the inputs of a ConvUnit block. Nine
    outputs are provided for this cause. Four line buffers are implemented
    receiveing the outputs from the predecessor layer with four modes to read
    and write. The read and write mode define which line buffer will be used to
    write the outputs of the last layer. The three line buffers remaining are
    used to fill the registers outputs.

    :param input_size: size of the line_buffers of this unit.
    :type input_size: int
    """
    logger = logging.getLogger(__name__)

    def __init__(self, binary=False, mem_size=0, counter_size=0,
                 **kwargs):
        super().__init__(**kwargs)

        self.INPUT_WIDTH = 1 if binary else 16

        self.mem_size = mem_size
        self.counter_size = counter_size
        self.size = 1
        self.n_outputs = 1
        return

    @block
    def rtl(self, clk, reset, input_counter, input, output_counter, output,
            en_zero, mode, en_read, en_write):
        """
        This function implements the combinational and sequential blocks of
        this block.

        :param clk: clock signal
        :type clk: std_logic
        :param reset: reset signal
        :type reset: std_logic
        :param en_zero: enable signal
        :type en_zero: std_logic
        :param en_read: enable signal
        :type en_read: std_logic
        :param input: vector with the input value with 16 bits width
        :type input: std_logic_vector
        :param output: the nine output values of the concatenated
        :type output: std_logic_vector
        :return: the logic implemented in this block
        :rtype: a method with @block decorator
        """
        wire_outputs = [Signal(intbv(0)[self.INPUT_WIDTH:])
                        for _ in range(self.n_outputs)]

        line_buffer0 = [Signal(intbv(0)[self.INPUT_WIDTH:])
                        for _ in range(self.mem_size)]
        line_buffer1 = [Signal(intbv(0)[self.INPUT_WIDTH:])
                        for _ in range(self.mem_size)]

        buffer_addr0 = Signal(intbv(0)[self.counter_size:])
        buffer_addr1 = Signal(intbv(0)[self.counter_size:])

        @always(clk.posedge)
        def comb_wire_buffer_addr():
            if (mode[0] == 1):
                buffer_addr0.next = input_counter
                buffer_addr1.next = output_counter
            else:
                buffer_addr0.next = output_counter
                buffer_addr1.next = input_counter

        @always_comb
        def comb_wire_channel_outputs():
            aux = intbv(0)[self.n_outputs*self.INPUT_WIDTH:]
            for i in range(self.n_outputs):
                aux[(i+1)*self.INPUT_WIDTH:i*self.INPUT_WIDTH] = \
                    wire_outputs[i]
            output.next = aux

        @always_seq(clk.posedge, reset=reset)
        def shift_outputs():
            if (en_read == 1):
                if (en_zero == 1):
                    for i in range(self.size):
                        wire_outputs[i].next = 0
                else:
                    if (mode[0] == 1):
                        wire_outputs[0].next = line_buffer0[buffer_addr0]
                    else:
                        wire_outputs[0].next = line_buffer1[buffer_addr1]

                for i in range(self.size, self.n_outputs):
                    wire_outputs[i].next = wire_outputs[i-self.size]

        @always(clk.posedge)
        def write_line_buffer():
            if (en_write == 1):
                if (mode[0] == 1):
                    line_buffer0[buffer_addr0].next = input
                else:
                    line_buffer1[buffer_addr1].next = input

        return (write_line_buffer, shift_outputs, comb_wire_channel_outputs,
                comb_wire_buffer_addr)

    def get_signals(self):
        """
        This function returns the signals necessairly to instantiate the rtl
        block and convert the python method to a vhdl file.

        :return: a dict specifying the input and output signals of the block.
        :rtype: dict of myhdl.Signal

        **Python definition of inputs and ouputs:**

        .. code-block:: python

            def get_signals(self):
                return {
                    "clk": Signal(False),
                    "reset": ResetSignal(0, active=1, isasync=1),
                    "input": Signal(intbv(0)[16:]),
                    "input_counter": Signal(intbv(0)[self.counter_size:]),
                    "output": Signal(intbv(0)[self.n_outputs*16:]),
                    "output_counter": Signal(intbv(0)
                                             [self.size*self.counter_size:]),
                    "en_zero": Signal(False),
                    "mode": Signal(intbv(0)[self.size+1:]),
                    "en_read": Signal(False),
                    "en_write": Signal(False)
                }

        **VHDL component generated:**

        .. code-block:: vhdl

            component DualScatterUnit is
                port (
                    clk            : in  std_logic;
                    reset          : in  std_logic;
                    en_zero        : in  std_logic;
                    en_read        : in  std_logic;
                    en_write       : in  std_logic;
                    mode           : in  unsigned(3 downto 0);
                    input_counter  : in  unsigned(8 downto 0);
                    input          : in  unsigned(15 downto 0);
                    output_counter : in  unsigned(26 downto 0);
                    output         : out unsigned(143 downto 0)
                );
            end component TriScatterUnit;

        """
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "input": Signal(intbv(0)[self.INPUT_WIDTH:]),
            "input_counter": Signal(intbv(0)[self.counter_size:]),
            "output": Signal(intbv(0)[self.n_outputs*self.INPUT_WIDTH:]),
            "output_counter": Signal(intbv(0)[self.counter_size:]),
            "en_zero": Signal(False),
            "mode": Signal(intbv(0)[self.size+1:]),
            "en_read": Signal(False),
            "en_write": Signal(False)
        }


if (__name__ == '__main__'):
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        mem_size = int(2 ** ceil(log(416, 2)))
        counter_size = int(log(mem_size, 2)) + 1
        unit = MonoScatterUnit(mem_size=mem_size, counter_size=counter_size,
                               binary=True)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
