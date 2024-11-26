BUILD_DIR := ${CURR_DIR}/build
__dummy := $(shell mkdir -p ${BUILD_DIR} ${SO_OUTPUT_DIR} ${WASM_OUTPUT_DIR})

# Libraries
FLINT_VERSION=3.1.2
FLINT=flint-${FLINT_VERSION}
FLINT_SOURCE=https://flintlib.org/${FLINT}.tar.gz

# Compile flags
FLINT_FLAGS= --enable-shared

# Map to link a library to its source
${FLINT} := FLINT

# Commands
COMPILE_MAKE = make -j $(shell expr $(shell nproc) + 1)

.PHONY: libflint clean

libflint: ${BUILD_DIR}/${FLINT}/
	cd ${BUILD_DIR}/${FLINT}/ && ./configure ${FLINT_FLAGS} && ${COMPILE_MAKE} && make install

${BUILD_DIR}/%/: %.tar.gz
	tar -xzf $< -C ${BUILD_DIR}

%.tar.gz:
	wget -q $($($*)_SOURCE) -O $@

clean:
	rm -rf ${BUILD_DIR} ${OUTPUT_DIR}
