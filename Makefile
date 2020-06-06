conv_unit:
	python3 src/components/ConvUnit.py ConvUnit src/generated

multichannel:
	( \
		python3 src/components/MultiChannelConvUnit.py MultiChannelConvUnit src/generated; \
		sed -i -e 's/acc(i) </acc(i) :/g' src/generated/MultiChannelConvUnit.vhd; \
		sed -i -e 's/acc((output_index + i)) </acc((output_index + i)) :/g' src/generated/MultiChannelConvUnit.vhd; \
	)

multiplier:
	python3 src/components/FixedPointMultiplier.py Multiplier src/generated

conv_layer:
	( \
		python3 src/components/ConvLayer.py ConvLayer src/generated; \
		sed -i -e 's/acc(i) </acc(i) :/g' src/generated/ConvLayer.vhd; \
		sed -i -e 's/acc((output_index + i)) </acc((output_index + i)) :/g' src/generated/ConvLayer.vhd; \
	)

kernel:
	python3 src/components/KernelROM.py KernelROM src/generated
