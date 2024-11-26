from .compile import ctypes, shared_library, DEGREE
from .classes import FLINT_RAND_T, ENCRYPTION_SCHEME_TYPE, PublicKey, PrivateKey, FMPZ_MOD_POLY_T, \
    Ciphertext
from .utils import new_flint_random


class EncryptionScheme:
    def __init__(self, shared_library):
        self.__clear_rand = False
        self.__shared_library = shared_library
        self.__is_loaded = False
        self.scheme: ENCRYPTION_SCHEME_TYPE = None
        self.rand = None

    def load(self, rand: FLINT_RAND_T = None):
        if self.__is_loaded:
            return
        self.scheme = ENCRYPTION_SCHEME_TYPE()
        self.__shared_library.encrypt_setup(self.scheme)
        if rand is None:
            rand = new_flint_random(self.__shared_library)
            self.__clear_rand = True
        self.rand = rand
        self.__is_loaded = True

    def terminate(self):
        if not self.__is_loaded:
            return
        self.__shared_library.encrypt_finish(self.scheme)
        if self.__clear_rand:
            self.__shared_library.flint_randclear(self.rand)
        self.__is_loaded = False

    def keygen(self) -> (PublicKey, PrivateKey):
        """
        Generate a key pair for the encryption scheme
        """
        public_key = PublicKey()
        private_key = PrivateKey()
        self.__shared_library.encrypt_keygen(self.scheme,
                                             ctypes.byref(public_key),
                                             ctypes.byref(private_key),
                                             self.rand)
        return public_key, private_key

    def encrypt(self, message, public_key) -> Ciphertext:
        """
        Encrypt a message
        :param message: the message to encrypt
        :param public_key: the public key to use for encryption
        :return: the ciphertext
        """
        ciphertext = Ciphertext()
        self.__shared_library.encrypt_doit(self.scheme,
                                           ctypes.byref(ciphertext),
                                           message,
                                           ctypes.byref(public_key),
                                           self.rand)
        return ciphertext

    def decrypt(self, ciphertext, private_key, challenge=None):
        """
        Decrypt a ciphertext
        :param ciphertext: the ciphertext to decrypt
        :param private_key: the private key to use for decryption
        :param challenge: an optional decryption challenge
        :return: True if the decryption was successful under the challenge or if the challenge is null,
        False otherwise
        """
        message = FMPZ_MOD_POLY_T()
        self.__shared_library.fmpz_mod_poly_init(message, self.scheme[0].ctx_p)

        result = self.__shared_library.encrypt_undo(self.scheme,
                                                    message,
                                                    challenge,
                                                    ctypes.byref(ciphertext),
                                                    ctypes.byref(private_key)) == 1
        return message, result

    def keyfree(self, public_key, private_key):
        self.__shared_library.encrypt_keyfree(self.scheme, ctypes.byref(public_key), ctypes.byref(private_key))

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
        return False


if __name__ == "__main__":
    wrapper = EncryptionScheme(shared_library)
    with wrapper as encryption_scheme:
        message = FMPZ_MOD_POLY_T()
        _message = FMPZ_MOD_POLY_T()
        shared_library.fmpz_mod_poly_init(message, encryption_scheme.scheme[0].ctx_q)
        shared_library.fmpz_mod_poly_init(_message, encryption_scheme.scheme[0].ctx_q)

        w = (FMPZ_MOD_POLY_T * 2)()
        for i in range(2):
            shared_library.fmpz_mod_poly_init(w[i], encryption_scheme.scheme[0].ctx_q)

        print("Check if CRT representation is correct")
        shared_library.fmpz_mod_poly_randtest(message, encryption_scheme.rand,
                                              DEGREE, encryption_scheme.scheme[0].ctx_q)

        for i in range(2):
            shared_library.fmpz_mod_poly_rem(w[i], message, encryption_scheme.scheme[0].irred[i],
                                             encryption_scheme.scheme[0].ctx_q)
        shared_library.qcrt_poly_rec(encryption_scheme.scheme, _message, w)
        result = shared_library.fmpz_mod_poly_equal(message, _message,
                                                    encryption_scheme.scheme[0].ctx_q)

        print("CRT representation is correct" if result else "CRT representation is incorrect")

        shared_library.fmpz_mod_poly_clear(message, encryption_scheme.scheme[0].ctx_q)
        shared_library.fmpz_mod_poly_clear(_message, encryption_scheme.scheme[0].ctx_q)

        shared_library.fmpz_mod_poly_init(message, encryption_scheme.scheme[0].ctx_p)

        print("Check if encryption and decryption are consistent")
        shared_library.encrypt_sample_short(message, encryption_scheme.scheme[0].ctx_p)
        pk, sk = encryption_scheme.keygen()
        ciphertext = encryption_scheme.encrypt(message, pk)
        _message, result = encryption_scheme.decrypt(ciphertext, sk)
        print("Successful decryption: ", result)
        result = shared_library.fmpz_mod_poly_equal(message, _message,
                                                    encryption_scheme.scheme[0].ctx_p)
        print("Decryption generated the same message: ", result == 1)

        shared_library.fmpz_mod_poly_clear(message, encryption_scheme.scheme[0].ctx_q)
        shared_library.fmpz_mod_poly_clear(_message, encryption_scheme.scheme[0].ctx_q)
        for i in range(2):
            shared_library.fmpz_mod_poly_clear(w[i], encryption_scheme.scheme[0].ctx_q)

        encryption_scheme.keyfree(pk, sk)
