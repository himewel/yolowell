from conv_layer import ConvLayer
from max_pool_layer import MaxPoolLayer
from utils import read_floats
import yaml


class NetworkParser():
    def __init__(self, network_file=""):
        with open(network_file) as stream:
            network = yaml.load(stream, Loader=yaml.FullLoader)

        self.weight_file = network["weights"]
        self.output_path = network["output_path"]
        self.input_channels = network["channels"]
        self.layer_groups = network["layer_groups"]

        # parse the file with weights
        self.weights = read_floats(file_path=self.weight_file)

        # initialize index of buckets to each conv layer
        self.weights_start_index = 0
        self.weights_end_index = 0
        pass

    def __parse_layer(self, layer, filters, channels):
        if (layer["type"] == "conv_layer"):
            self.__parse_conv_layer(layer, filters, channels)
        elif (layer["type"] == "max_pool_layer"):
            self.__parse_max_pool_layer(layer, filters, channels)
        else:
            print("Layer type not recognized: " + layer["type"])
        pass

    def __parse_conv_layer(self, layer, filters, channels):
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
                size=size, filters=filters, channels=channels,
                binary=binary, bin_input=bin_input,
                bin_output=bin_output, weights=layer_weights)
        })
        return

    def __parse_max_pool_layer(self, layer, filters, channels):
        binary = layer["binary"]

        self.layers.append({
            "type": "max_pool_layer",
            "object": MaxPoolLayer(
                binary=binary, filters=filters)
        })
        return

    def parse_network(self):
        # initalize current channe inputs with the network input
        channels = self.input_channels
        # intialize array of layers
        self.layers = []

        for group in self.layer_groups:
            # get the number of outputs of the current group
            filters = group["filters"]
            for layer in group["layers"]:
                self.__parse_layer(layer, filters, channels)
            # update number of inputs of the next layers
            channels = filters
        return

    def generate(self):
        for i in range(len(self.layers)):
            layer = self.layers[i]
            object = layer["object"]
            object.convert(
                name="{layer_type}{index}".format(
                    layer_type=layer["type"], index=i),
                path=self.output_path)


if __name__ == '__main__':
    net = NetworkParser("xnor_net.yaml")
    net.parse_network()
    net.generate()