# LBVS Lib

[![PyPI - Version](https://img.shields.io/pypi/v/lbvs-lib.svg)](https://pypi.org/project/lbvs-lib)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/lbvs-lib.svg)](https://pypi.org/project/lbvs-lib)

-----

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

First you need to compile the shared object file. Go to the lattice-voting-ctrsa21 directory 
and run the following command:
```console
make shared-lib
```

Then move the shared object file to the lbvs-lib directory:
```console
mv lattice-voting-ctrsa21/shared_lib.so lbvs-lib/src/lbvs_lib/
```

Then you can install the package using pip:

```console
pip install lbvs-lib
```

## License

`lbvs-lib` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
