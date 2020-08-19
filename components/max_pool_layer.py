from sys import argv
import logging
from base_component import BaseComponent
from max_pool_unit import MaxPoolUnit
from bin_max_pool_unit import BinMaxPoolUnit
from myhdl import always_comb, block, Signal, intbv, ResetSignal


class MaxPoolLayer(BaseComponent):
    """
    This class gather some MaxPoolUnits with different channel input and
    outputs. Both inputs are concatenated in one signal to the layer. The same
    to the outputs.

    :param filters: number of filters inputs to this layer
    :type filters: int
    """
    logger = logging.getLogger(__name__)

    def __init__(self, filters=0, binary=False, **kwargs):
        super().__init__(**kwargs)

        self.filters = filters
        self.PORT_WIDTH = 1 if binary else 16

        if (binary):
            self.max_pool_units = \
                [BinMaxPoolUnit(channel_id=i) for i in range(self.filters)]
        else:
            self.max_pool_units = \
                [MaxPoolUnit(channel_id=i) for i in range(self.filters)]
        return

    @block
    def rtl(self, clk, reset, input, output, en_pool):
        """
        This function implements the combinational and sequential blocks of
        this block.

        :param clk: clock signal
        :type clk: Signal()
        :param reset: reset signal
        :type reset: Signal()
        :param en_pool: enable signal
        :type en_pool: Signal()
        :param input: vector with the all channel inputs to the layer \
        concatenated, each channel input gather four input values \
        concatenated to form a input channel, each value should be an signed \
        value with 16 bits width
        :type input: Signal(intbv()[])
        :param output: the concatenated output values of the comparations
        :type output: Signal(intbv()[])

        :return: logic of this block
        :rtype: @block method
        """
        wire_channel_inputs = [Signal(intbv(0)[4*self.PORT_WIDTH:])
                               for _ in range(self.filters)]
        wire_channel_outputs = [Signal(intbv(0)[self.PORT_WIDTH:])
                                for _ in range(self.filters)]
        max_pool_units = [self.max_pool_units[i].rtl(
            clk=clk, reset=reset, input=wire_channel_inputs[i],
            en_pool=en_pool, output=wire_channel_outputs[i]
        ) for i in range(self.filters)]

        @always_comb
        def comb_wire_inputs():
            for i in range(self.filters):
                wire_channel_inputs[i].next = \
                    input[4*self.PORT_WIDTH*(i+1):4*self.PORT_WIDTH*i]

        @always_comb
        def comb_wire_outputs():
            aux = intbv(0)[self.filters*self.PORT_WIDTH:]
            for i in range(self.filters):
                aux[(i+1)*self.PORT_WIDTH:i*self.PORT_WIDTH] = \
                    wire_channel_outputs[i]
            output.next = aux

        return (max_pool_units, comb_wire_outputs, comb_wire_inputs)

    def get_signals(self):
        """
        This function returns the signals necessairly to instantiate the rtl
        block and convert the python method to a vhdl file.

        :return: a dict specifying the input and outputs signals of the block.
        :rtype: dict of myhdl.Signal

        **Python definition of inputs and ouputs:**

        .. code-block:: python

            def get_signals(self):
                return {
                    "clk": Signal(False),
                    "reset": ResetSignal(0, active=1, isasync=1),
                    "input": Signal(intbv(0)[4*self.filters*self.PORT_WIDTH:]),
                    "output": Signal(intbv(0)[self.filters*self.PORT_WIDTH:]),
                    "en_pool": Signal(False),
                }

        **VHDL component generated:**

        .. code-block:: vhdl

            component MaxPoolLayer
                port (
                    clk     : in  std_logic;
                    reset   : in  std_logic;
                    input   : in  unsigned(1023 downto 0);
                    output  : out unsigned(255 downto 0);
                    en_pool : in  std_logic
                );
            end component MaxPoolLayer;

        """
        return {
            "clk": Signal(False),
            "reset": ResetSignal(0, active=1, isasync=1),
            "input": Signal(intbv(0)[4*self.filters*self.PORT_WIDTH:]),
            "output": Signal(intbv(0)[self.filters*self.PORT_WIDTH:]),
            "en_pool": Signal(False),
        }


if (__name__ == '__main__'):
    if (len(argv) > 2):
        name = argv[1]
        path = argv[2]

        unit = MaxPoolLayer(filters=16, binary=True)
        unit.convert(name, path)
    else:
        print("file.py <entityname> <outputfile>")
