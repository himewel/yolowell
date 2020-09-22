import yaml
import logging

from conv_layer import ConvLayer
from max_pool_layer import MaxPoolLayer
# from buffer_layer import BufferLayer
from utils import read_floats


class NetworkParser():
    def __init__(self, network_file=""):
        self.logger = logging.getLogger(__class__.__name__)
        with open(network_file) as stream:
            network = yaml.load(stream, Loader=yaml.FullLoader)

        self.weight_file = network["weights"]
        self.output_path = network["output_path"]
        self.input_channels = network["channels"]
        self.layer_groups = network["layer_groups"]
        self.width = network["width"]
        self.project = network.get("project", "darknet_hdl.qsf")

        # parse the file with weights
        self.logger.info("Reading weights...")
        self.weights = read_floats(file_path=self.weight_file)
        self.logger.info(f"{len(self.weights)} float values were readed")

        # initialize index of buckets to each conv layer
        self.weights_index = 0
        self.weights_offset = 0

    def __parse_layer(self, index, layer, filters, channels):
        self.logger.info(f"Parsing {layer['type']}: {layer}")
        if (layer["type"] == "conv_layer"):
            self.__parse_conv_layer(index, layer, filters, channels)
        elif (layer["type"] == "max_pool_layer"):
            self.__parse_max_pool_layer(index, layer, filters, channels)
        elif (layer["type"] == "buffer_layer"):
            self.__parse_buffer_layer(index, layer, filters, channels)
        else:
            self.logger.warning(f"Layer type not recognized: {layer['type']}")

    def __parse_conv_layer(self, index, layer, filters, channels):
        size = layer["size"]
        binary = layer["binary"]
        bin_input = layer["bin_input"]
        bin_output = layer["bin_output"]
        parallelism = layer.get("parallelism", 8)
        proccess_filters = int(filters/parallelism)

        for process_id in range(parallelism):
            # update start and end indexes of weights
            self.weights_offset = (size**2) * channels * proccess_filters
            self.weights_offset += self.weights_index

            layer_weights = \
                self.weights[self.weights_index:self.weights_offset]

            layer = {
                "class": ConvLayer,
                "filename": f"ConvLayerL{index}P{process_id}",
                "path": f"{self.output_path}/ConvLayerL{index}",
                "args": {
                    "size": size,
                    "filters": proccess_filters,
                    "channels": channels,
                    "binary": binary,
                    "bin_input": bin_input,
                    "bin_output": bin_output,
                    "weights": layer_weights,
                    "layer_id": index,
                    "process_id": process_id
                }
            }
            self.layers.append(layer)
            self.weights_index = self.weights_offset + 1

        layer = {
            "class": ConvLayer,
            "filename": f"ConvLayerL{index}",
            "path": f"{self.output_path}",
            "args": {
                "size": size,
                "filters": filters,
                "channels": channels,
                "binary": binary,
                "bin_input": bin_input,
                "bin_output": bin_output,
                "layer_id": index,
                "parallelism": parallelism,
                "top_entity": True
            }
        }
        self.layers.append(layer)

    def __parse_max_pool_layer(self, index, layer, filters, channels):
        binary = layer["binary"]
        self.width /= 2

        layer = {
            "class": MaxPoolLayer,
            "filename": f"MaxPoolLayerL{index}",
            "path": f"{self.output_path}",
            "args": {
                "filters": filters,
                "binary": binary,
                "layer_id": index
            }
        }
        self.layers.append(layer)

    def __parse_buffer_layer(self, index, layer, filters, channels):
        binary = layer["binary"]
        scattering = layer["scattering"]

        layer = BufferLayer(  # noqa
            binary=binary, filters=filters, scattering=scattering,
            width=self.width, layer_id=index, top_entity=False)
        self.layers.append(layer)

    def parse_network(self):
        self.logger.info("Starting network parser...")
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
        del self.weights
        return self.layers

    def build_project(self, layers):
        text = "\n"
        for i in range(len(layers)-1, -1, -1):
            filename = f"{layers[i]['filename']}.vhd"
            path = f"{layers[i]['path']}"

            text += "set_global_assignment -name VHDL_FILE "
            text += f"{path}/{filename}\n"

        with open(self.project, "a+") as file:
            file.write(text)

    def generate(self, layers, convert_function):
        from multiprocessing import Pool
        import os

        self.logger.info("Starting network convertion...")
        cores = round(os.cpu_count()*4/4)
        self.logger.info(f"Multiprocessing: {cores} cpus...")

        pool = Pool(processes=cores)
        for i in range(cores):
            pool.apply_async(func=worker_healthcheck)

        for i in range(len(layers)):
            layer = layers[i]
            layer_class = layer["class"]
            layer_args = layer["args"]
            path = layer["path"]
            name = layer["filename"]

            pool.apply_async(
                func=worker_process,
                args=([layer_class, str(path), str(name), convert_function]),
                kwds=layer_args)
        pool.close()
        pool.join()


def worker_healthcheck():
    import logging
    import os
    logger = logging.getLogger("Worker")
    logger.info(f"Worker healthcheck: PID {os.getpid()}")


def worker_process(layer_class, path, name, convert_function, **kwargs):
    unit = layer_class(**kwargs)
    try:
        convert_function(unit, path, name)
    except Exception as e:
        unit.logger.critical(e, exc_info=True)
        raise


if __name__ == '__main__':
    from utils import get_file_logger, get_std_logger, to_vhdl  # noqa
    get_file_logger()
    # get_std_logger()
    net = NetworkParser("xnor_net.yaml")
    layers = net.parse_network()
    net.generate(layers, to_vhdl)
    # net.build_project(layers)
