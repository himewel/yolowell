# Darknet HDL

The main objective of this repository is generate vhd files to use in a co-project implementation of Darknet and Yolo in FPGA devices. The Yolo reference version used to compose the constants in the ComponentClass is yolov3-tiny.

The generated vhd components are extensively replicated in their units, which is why they are transcribed in Python via MyHDL; so don't think that I don't know how to program in VHDL (at some point that phrase sounds funny to me).

![Darknet Logo](http://pjreddie.com/media/files/darknet-black-small.png)

# About Darknet #

Darknet is an open source neural network framework written in C and CUDA. It is fast, easy to install, and supports CPU and GPU computation.

For more information see the [Darknet project website](http://pjreddie.com/darknet).

For questions or issues please use the [Google Group](https://groups.google.com/forum/#!forum/darknet).
