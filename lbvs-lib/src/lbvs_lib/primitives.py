from .commitment_scheme import CommitmentScheme
from .encryption_scheme import EncryptionScheme
from .vericrypt import Vericrypt

from .utils import new_flint_random
from .compile import shared_library as lib


class Primitives:
    def __init__(self, shared_library):
        self.__shared_library = shared_library
        self.__flint_rand = new_flint_random(shared_library)
        self.__commitment_scheme = CommitmentScheme(shared_library)
        self.__commitment_scheme.load(self.__flint_rand)
        self.__encryption_scheme = EncryptionScheme(shared_library)
        self.__encryption_scheme.load(self.__flint_rand)
        self.__vericrypt = Vericrypt(shared_library, self.__encryption_scheme, self.__flint_rand)

    @property
    def flint_rand(self):
        return self.__flint_rand

    @property
    def commitment_scheme(self):
        return self.__commitment_scheme

    @property
    def encryption_scheme(self):
        return self.__encryption_scheme

    @property
    def vericrypt(self):
        return self.__vericrypt

    def __del__(self):
        self.__commitment_scheme.terminate()
        self.__encryption_scheme.terminate()
        self.__shared_library.flint_randclear(self.__flint_rand)


primitives = Primitives(lib)

flint_rand = primitives.flint_rand
commitment_scheme = primitives.commitment_scheme
encryption_scheme = primitives.encryption_scheme
vericrypt = primitives.vericrypt


