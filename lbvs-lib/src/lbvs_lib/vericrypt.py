from .compile import ctypes, VECTOR, DEGREE
from .encryption_scheme import EncryptionScheme
from .classes import Veritext, FMPZ_MOD_POLY_T, PublicKey, FLINT_RAND_T, PrivateKey, FMPZ_MOD_CTX_T


class Vericrypt:
    def __init__(self, shared_library, encryption_scheme: EncryptionScheme, rand: FLINT_RAND_T):
        self.encryption_scheme = encryption_scheme
        self.shared_library = shared_library
        self.rand = rand

    def encrypt(self, t: FMPZ_MOD_POLY_T * VECTOR, u: FMPZ_MOD_POLY_T, m: FMPZ_MOD_POLY_T * VECTOR,
                pk: PublicKey):
        """
        Encrypts a message m using the public key pk and the randomness u

        """
        veritext = Veritext()
        result = self.shared_library.vericrypt_doit(ctypes.byref(veritext), t, u, m,
                                                    self.encryption_scheme.scheme, ctypes.byref(pk), self.rand)
        return veritext, result

    def decrypt(self, veritext: Veritext, t: FMPZ_MOD_POLY_T * VECTOR, u: FMPZ_MOD_POLY_T,
                pk: PublicKey, sk: PrivateKey):
        """
        Verifies and decrypts a ciphertext using the public key pk and the secret key sk
        """
        m = (FMPZ_MOD_POLY_T * VECTOR)()
        c = FMPZ_MOD_POLY_T()
        for i in range(VECTOR):
            self.shared_library.fmpz_mod_poly_init(m[i], self.encryption_scheme.scheme[0].ctx_p)
        self.shared_library.fmpz_mod_poly_init(c, self.encryption_scheme.scheme[0].ctx_p)

        result = self.shared_library.vericrypt_undo(m, c, ctypes.byref(veritext), t, u, self.encryption_scheme.scheme,
                                                    ctypes.byref(pk), ctypes.byref(sk))
        return m, c, result

    def verify(self, veritext: Veritext, t: FMPZ_MOD_POLY_T * VECTOR, u: FMPZ_MOD_POLY_T, pk: PublicKey):
        """
        Verifies a ciphertext using the public key pk
        """
        result = self.shared_library.vericrypt_verify(ctypes.byref(veritext), t, u, self.encryption_scheme.scheme,
                                                      ctypes.byref(pk))
        return result

    def cipher_clear(self, veritext: Veritext):
        self.shared_library.vericrypt_cipher_clear(ctypes.byref(veritext), self.encryption_scheme.scheme)

    def new_t(self) -> FMPZ_MOD_POLY_T * VECTOR:
        t = (FMPZ_MOD_POLY_T * VECTOR)()
        for i in range(VECTOR):
            self.shared_library.fmpz_mod_poly_init(t[i], self.context_p)

        for i in range(VECTOR):
            self.shared_library.fmpz_mod_poly_randtest(t[i], self.rand, DEGREE, self.context)
        return t

    def new_u(self, t: FMPZ_MOD_POLY_T * VECTOR, m: FMPZ_MOD_POLY_T * VECTOR):
        u = FMPZ_MOD_POLY_T()
        tmp = FMPZ_MOD_POLY_T()
        self.shared_library.fmpz_mod_poly_init(u, self.context_p)
        self.shared_library.fmpz_mod_poly_init(tmp, self.context_p)

        for i in range(VECTOR):
            self.shared_library.fmpz_mod_poly_mulmod(tmp, t[i], m[i], self.encrypt_poly, self.context_p)
            self.shared_library.fmpz_mod_poly_add(u, u, tmp, self.context_p)

        self.shared_library.fmpz_mod_poly_clear(tmp, self.context_p)
        return u

    @property
    def context(self):
        return self.encryption_scheme.scheme[0].ctx_q

    @property
    def context_p(self):
        return self.encryption_scheme.scheme[0].ctx_p

    @property
    def encrypt_poly(self):
        return self.encryption_scheme.scheme[0].poly


if __name__ == '__main__':
    from .compile import shared_library
    wrapper = EncryptionScheme(shared_library)
    with wrapper as encryption_scheme:
        modulus_ctx = encryption_scheme.scheme[0].ctx_p
        encrypt_poly = encryption_scheme.scheme[0].poly

        print("Initializing variables")
        tmp = FMPZ_MOD_POLY_T()
        m = (FMPZ_MOD_POLY_T * VECTOR)()

        shared_library.fmpz_mod_poly_init(tmp, modulus_ctx)

        for i in range(VECTOR):
            shared_library.fmpz_mod_poly_init(m[i], modulus_ctx)

        print("Generating keys")
        pk, sk = encryption_scheme.keygen()

        print("Generating random values")

        for i in range(VECTOR):
            shared_library.encrypt_sample_short(m[i], modulus_ctx)

        print("Calculating t and u")
        vericrypt = Vericrypt(shared_library, encryption_scheme, encryption_scheme.rand)
        t = vericrypt.new_t()

        print("Encrypting")
        u = vericrypt.new_u(t, m)
        veritext, result = vericrypt.encrypt(t, u, m, pk)

        print("Encryption result: ", result)

        print("Verifying")
        result = vericrypt.verify(veritext, t, u, pk)

        print("Verification result: ", result)

        print("Decrypting")
        _m, c, result = vericrypt.decrypt(veritext, t, u, pk, sk)

        print("Decryption result: ", result)

        v = vericrypt.new_u(t, _m)

        shared_library.fmpz_mod_poly_mulmod(u, u, c, encrypt_poly, modulus_ctx)

        result = shared_library.fmpz_mod_poly_equal(v, u, modulus_ctx)

        print("Checking v = u: ", result == 1)

        print("Cleaning up")
        encryption_scheme.keyfree(pk, sk)
        shared_library.fmpz_mod_poly_clear(tmp, modulus_ctx)
        for i in range(VECTOR):
            shared_library.fmpz_mod_poly_clear(t[i], modulus_ctx)
            shared_library.fmpz_mod_poly_clear(m[i], modulus_ctx)
            shared_library.fmpz_mod_poly_clear(_m[i], modulus_ctx)
        shared_library.fmpz_mod_poly_clear(c, modulus_ctx)
        shared_library.fmpz_mod_poly_clear(u, modulus_ctx)
        shared_library.fmpz_mod_poly_clear(v, modulus_ctx)
