from multiprocessing import Pool
import yaml
import os
from myhdl import ToVHDLWarning

from conv_layer import ConvLayer
from max_pool_layer import MaxPoolLayer
from buffer_layer import BufferLayer
from utils import read_floats


class NetworkParser():
    def __init__(self, network_file=""):
        with open(network_file) as stream:
            network = yaml.load(stream, Loader=yaml.FullLoader)

        self.weight_file = network["weights"]
        self.output_path = network["output_path"]
        self.input_channels = network["channels"]
        self.layer_groups = network["layer_groups"]
        self.width = network["width"]

        # parse the file with weights
        self.weights = read_floats(file_path=self.weight_file)

        # initialize index of buckets to each conv layer
        self.weights_start_index = 0
        self.weights_end_index = 0
        pass

    def __parse_layer(self, index, layer, filters, channels):
        if (layer["type"] == "conv_layer"):
            self.__parse_conv_layer(index, layer, filters, channels)
        elif (layer["type"] == "max_pool_layer"):
            self.__parse_max_pool_layer(index, layer, filters, channels)
        elif (layer["type"] == "buffer_layer"):
            self.__parse_buffer_layer(index, layer, filters, channels)
        else:
            print("Layer type not recognized: " + layer["type"])
        pass

    def __parse_conv_layer(self, index, layer, filters, channels):
        size = layer["size"]
        binary = layer["binary"]
        bin_input = layer["bin_input"]
        bin_output = layer["bin_output"]

        # update start and end indexes of weights
        self.weights_end_index = \
            self.weights_start_index + size * size * channels * filters
        layer_weights = \
            self.weights[self.weights_start_index:self.weights_end_index]
        self.weights_start_index = self.weights_end_index + 1

        self.layers.append({
            "type": "conv_layer",
            "object": ConvLayer(
                size=size, filters=filters, channels=channels, binary=binary,
                bin_input=bin_input, bin_output=bin_output,
                weights=layer_weights, layer_id=index)
        })
        return

    def __parse_max_pool_layer(self, index, layer, filters, channels):
        binary = layer["binary"]
        self.width /= 2

        self.layers.append({
            "type": "max_pool_layer",
            "object": MaxPoolLayer(
                binary=binary, filters=filters, layer_id=index)
        })
        return

    def __parse_buffer_layer(self, index, layer, filters, channels):
        binary = layer["binary"]
        scattering = layer["scattering"]

        self.layers.append({
            "type": "buffer_layer",
            "object": BufferLayer(
                binary=binary, filters=filters, scattering=scattering,
                width=self.width, layer_id=index)
        })
        return

    def parse_network(self):
        # initalize current channe inputs with the network input
        channels = self.input_channels
        # intialize array of layers
        self.layers = []
        index = 0

        for group in self.layer_groups:
            # get the number of outputs of the current group
            filters = group["filters"]
            for layer in group["layers"]:
                self.__parse_layer(index, layer, filters, channels)
                index += 1
            # update number of inputs of the next layers
            channels = filters
        return

    def call_convertion(self, object, name, path):
        object.convert(name, path)

    def generate(self):
        with Pool(processes=(round(os.cpu_count()*3/4))) as pool:
            i = 0
            while len(self.layers) > 0:
                layer = self.layers[0]
                type = layer["type"]
                object = layer["object"]

                name = "{type}{index}".format(type=type, index=i),
                path = self.output_path

                pool.apply_async(self.call_convertion,
                                 tuple([object, str(name), str(path)]))

                i += 1
                del self.layers[0]

            pool.close()
            pool.join()


if __name__ == '__main__':
    import logging
    format = ("Layer: %(name)s\nLayer ID: %(layer_id)s\nUnit ID: %(unit_id)s\n"
              "Channel ID: %(channel_id)s\n"+80*"-")
    logging.basicConfig(format=format, level=logging.INFO)

    import warnings
    warnings.filterwarnings("ignore", message="Signal is not driven")

    net = NetworkParser("xnor_net.yaml")
    net.parse_network()
    net.generate()
