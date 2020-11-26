import pickle


weights_path = "./tiny/tiny_weights.h"
bn_variance_path = "./tiny/tiny_variance.h"
bn_mean_path = "./tiny/tiny_mean.h"
scale_path = "./tiny/tiny_scale.h"
biases_path = "./tiny/tiny_biases.h"

bin_weights_path = "./tiny/tiny_weights.pickle"
bin_bn_variance_path = "./tiny/tiny_variance.pickle"
bin_bn_mean_path = "./tiny/tiny_mean.pickle"
bin_scale_path = "./tiny/tiny_scale.pickle"
bin_biases_path = "./tiny/tiny_biases.pickle"

file_paths = [
    (weights_path, bin_weights_path),
    (bn_variance_path, bin_bn_variance_path),
    (bn_mean_path, bin_bn_mean_path),
    (scale_path, bin_scale_path),
    (biases_path, bin_biases_path),
]

for text_file_path, bin_file_path in file_paths:
    float_values = []

    with open(text_file_path, "r") as text_stream:
        text = text_stream.read().replace("\n", "").replace("\t", "")
        text = text.split("{")
        text = text[1].split("}")
        text = text[0].split(",")

        try:
            for i in range(len(text)):
                float_values.append(float(text[i]))
        except Exception:
            pass

    with open(bin_file_path, "wb") as binary_stream:
        pickle.dump(float_values, binary_stream)
