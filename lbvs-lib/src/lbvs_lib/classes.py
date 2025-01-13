from .compile import WIDTH, HEIGHT, ctypes, shared_library, DIM, VECTOR, MODP

# TODO one file per module and see if it works using only one ctypes import
"""
Mapping of Flint structures to Python ctypes 
"""

MP_PTR = ctypes.POINTER(ctypes.c_ulong)


class MpzStruct(ctypes.Structure):
    _fields_ = [
        ("_mp_alloc", ctypes.c_int),
        ("_mp_size", ctypes.c_int),
        ("_mp_d", MP_PTR)
    ]


MpzStruct_T = MpzStruct * 1


class AlgData(ctypes.Union):
    _fields_ = [
        ("_mp_lc", ctypes.c_void_p),
    ]


class GMPRandS(ctypes.Structure):
    _fields_ = [
        ("_mp_seed", MpzStruct_T),
        ("_mp_alg", ctypes.c_int),
        ("_mp_algdata", AlgData)
    ]


GMPSRandT = GMPRandS * 1


class FlintRandS(ctypes.Structure):
    _fields_ = [
        ("gmp_state", GMPSRandT),
        ("gmp_init", ctypes.c_int),
        ("__randval", ctypes.c_ulong),
        ("__randval2", ctypes.c_ulong)
    ]


FLINT_RAND_T = FlintRandS * 1

"""
Mapping of Flint nmod_poly structure
"""


class Nmod(ctypes.Structure):
    _fields_ = [
        ("n", ctypes.c_ulong),
        ("ninv", ctypes.c_ulong),
        ("norm", ctypes.c_ulong),
    ]


class NmodPoly(ctypes.Structure):
    _fields_ = [
        ("coeffs", MP_PTR),
        ("alloc", ctypes.c_long),
        ("length", ctypes.c_long),
        ("mod", Nmod),
    ]


NMOD_POLY_TYPE = NmodPoly * 1

"""
Mapping of Flint fmpz_mod_poly structure
"""

FMPZ = ctypes.c_long
FMPZ_T = FMPZ * 1


class FmpzModPoly(ctypes.Structure):
    _fields_ = [
        ("coeffs", ctypes.POINTER(FMPZ)),
        ("alloc", ctypes.c_long),
        ("length", ctypes.c_long)
    ]


FMPZ_MOD_POLY_T = FmpzModPoly * 1


class FmpzPreInvn(ctypes.Structure):
    _fields_ = [
        ("dinv", MP_PTR),
        ("n", ctypes.c_long),
        ("norm", ctypes.c_ulong)
    ]


class FmpzModCtx(ctypes.Structure):
    _fields_ = [
        ("n", FMPZ_T),
        ("mod", Nmod),
        ("add_fxn", ctypes.c_void_p),
        ("sub_fxn", ctypes.c_void_p),
        ("mul_fxn", ctypes.c_void_p),
        ("n_limbs", ctypes.c_ulong * 3),
        ("ninv_limbs", ctypes.c_ulong * 3),
        ("ninv_huge", ctypes.POINTER(FmpzPreInvn))
    ]


FMPZ_MOD_CTX_T = FmpzModCtx * 1

"""
Mapping of Encryption Scheme structures to Python ctypes
"""
QCRT_POLY_TYPE = FMPZ_MOD_POLY_T * 2


class EncryptionScheme(ctypes.Structure):
    _fields_ = [
        ("p", FMPZ_T),
        ("q", FMPZ_T),
        ("ctx_q", FMPZ_MOD_CTX_T),
        ("ctx_p", FMPZ_MOD_CTX_T),
        ("large_poly", FMPZ_MOD_POLY_T),
        ("poly", FMPZ_MOD_POLY_T),
        ("irred", QCRT_POLY_TYPE),
        ("inv", QCRT_POLY_TYPE),
    ]


ENCRYPTION_SCHEME_TYPE = EncryptionScheme * 1


class PublicKey(ctypes.Structure):
    _fields_ = [
        ("A", (QCRT_POLY_TYPE * DIM) * DIM),
        ("t", QCRT_POLY_TYPE * DIM)
    ]

    @staticmethod
    def equals(key1, key2, ctx):
        for i in range(DIM):
            for j in range(DIM):
                for k in range(2):
                    if not shared_library.fmpz_mod_poly_equal(key1.A[i][j][k], key2.A[i][j][k], ctx):
                        return False
            for j in range(2):
                if not shared_library.fmpz_mod_poly_equal(key1.t[i][j], key2.t[i][j], ctx):
                    return False
        return True


class PrivateKey(ctypes.Structure):
    _fields_ = [
        ("s1", QCRT_POLY_TYPE * DIM),
        ("s2", QCRT_POLY_TYPE * DIM)
    ]

    @staticmethod
    def equals(key1, key2, ctx):
        for i in range(DIM):
            for j in range(2):
                if (not shared_library.fmpz_mod_poly_equal(key1.s1[i][j], key2.s1[i][j], ctx)
                        or not shared_library.fmpz_mod_poly_equal(key1.s2[i][j], key2.s2[i][j], ctx)):
                    return False
        return True


class Ciphertext(ctypes.Structure):
    _fields_ = [
        ("v", QCRT_POLY_TYPE * DIM),
        ("w", QCRT_POLY_TYPE)
    ]

    @staticmethod
    def equals(cipher1, cipher2, ctx):
        for j in range(2):
            for i in range(DIM):
                if shared_library.fmpz_mod_poly_equal(cipher1.v[i][j],
                                                      cipher2.v[i][j],
                                                      ctx) == 0:
                    return False
            if shared_library.fmpz_mod_poly_equal(cipher1.w[j], cipher2.w[j], ctx) == 0:
                return False
        return True


"""
Mapping of Vericrypt structures to Python ctypes
"""


class Veritext(ctypes.Structure):
    _fields_ = [
        ("cipher", Ciphertext * VECTOR),
        ("c", FMPZ_MOD_POLY_T),
        ("r", FMPZ_MOD_POLY_T * 2 * DIM * VECTOR),
        ("e", FMPZ_MOD_POLY_T * 2 * DIM * VECTOR),
        ("e_", FMPZ_MOD_POLY_T * 2 * VECTOR),
        ("u", FMPZ_MOD_POLY_T * VECTOR),
    ]

    @property
    def z(self):
        return self.r, self.e, self.e_, self.u

    @staticmethod
    def equals(vt1, vt2, ctx):
        for i in range(VECTOR):
            if not Ciphertext.equals(vt1.cipher[i], vt2.cipher[i], ctx):
                return False
        if shared_library.fmpz_mod_poly_equal(vt1.c, vt2.c, ctx) == 0:
            return False
        for i in range(VECTOR):
            for j in range(DIM):
                for k in range(2):
                    if shared_library.fmpz_mod_poly_equal(vt1.r[i][j][k], vt2.r[i][j][k], ctx) == 0:
                        return False
                    if shared_library.fmpz_mod_poly_equal(vt1.e[i][j][k], vt2.e[i][j][k], ctx) == 0:
                        return False
        for i in range(VECTOR):
            for j in range(2):
                if shared_library.fmpz_mod_poly_equal(vt1.e_[i][j], vt2.e_[i][j], ctx) == 0:
                    return False
        return True


"""
Mapping of Commitment Scheme structures to Python ctypes
"""
PCRT_POLY_TYPE = NMOD_POLY_TYPE * 2
OPENING_TYPE = PCRT_POLY_TYPE * WIDTH


class CommitmentScheme(ctypes.Structure):
    _fields_ = [
        ("irred", PCRT_POLY_TYPE),
        ("inv", PCRT_POLY_TYPE),
        ("cyclo_poly", NMOD_POLY_TYPE)
    ]


COMMITMENT_SCHEME_TYPE = CommitmentScheme * 1


class CommitmentKey(ctypes.Structure):
    _fields_ = [
        ("B1", (PCRT_POLY_TYPE * WIDTH) * HEIGHT),
        ("b2", PCRT_POLY_TYPE * WIDTH),
    ]

    @staticmethod
    def equals(key1, key2):
        for i in range(WIDTH):
            for j in range(HEIGHT):
                for k in range(2):
                    if not shared_library.nmod_poly_equal(key1.B1[j][i][k], key2.B1[j][i][k]):
                        return False
                if not shared_library.nmod_poly_equal(key1.b2[i][j], key2.b2[i][j]):
                    return False
        return True


class Commitment(ctypes.Structure):
    _fields_ = [
        ("c1", PCRT_POLY_TYPE),
        ("c2", PCRT_POLY_TYPE),
    ]

    @staticmethod
    def equals(com1, com2):
        for i in range(2):
            if (shared_library.nmod_poly_equal(com1.c1[i], com2.c1[i]) == 0 or
                    shared_library.nmod_poly_equal(com1.c2[i], com2.c2[i]) == 0):
                return False
        return True


COMMITMENT_TYPE = Commitment * 1

"""
Loading functions
"""
# Flint
shared_library.flint_randinit.argtypes = (FLINT_RAND_T,)
shared_library.flint_randseed.argtypes = (FLINT_RAND_T, ctypes.c_ulong, ctypes.c_ulong)
shared_library.flint_randclear.argtypes = (FLINT_RAND_T,)

shared_library.nmod_poly_init.argtypes = (NMOD_POLY_TYPE, ctypes.c_ulong)
shared_library.nmod_poly_randtest.argtypes = (NMOD_POLY_TYPE, FLINT_RAND_T, ctypes.c_long)
shared_library.nmod_poly_zero.argtypes = (NMOD_POLY_TYPE,)
shared_library.nmod_poly_add.argtypes = (NMOD_POLY_TYPE, NMOD_POLY_TYPE, NMOD_POLY_TYPE)
shared_library.nmod_poly_sub.argtypes = (NMOD_POLY_TYPE, NMOD_POLY_TYPE, NMOD_POLY_TYPE)
shared_library.nmod_poly_mul.argtypes = (NMOD_POLY_TYPE, NMOD_POLY_TYPE, NMOD_POLY_TYPE)
shared_library.nmod_poly_mulmod.argtypes = (NMOD_POLY_TYPE, NMOD_POLY_TYPE, NMOD_POLY_TYPE)
shared_library.nmod_poly_get_coeff_ui.argtypes = (NMOD_POLY_TYPE, ctypes.c_long)
shared_library.nmod_poly_rem.argtypes = (NMOD_POLY_TYPE, NMOD_POLY_TYPE, NMOD_POLY_TYPE)
shared_library.nmod_poly_clear.argtypes = (NMOD_POLY_TYPE,)
shared_library.nmod_poly_set.argtypes = (NMOD_POLY_TYPE, NMOD_POLY_TYPE)
shared_library.nmod_poly_set_coeff_ui.argtypes = (NMOD_POLY_TYPE, ctypes.c_long, ctypes.c_ulong)

shared_library.fmpz_mod_poly_init.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.fmpz_mod_poly_randtest.argtypes = (FMPZ_MOD_POLY_T, FLINT_RAND_T, ctypes.c_long, FMPZ_MOD_CTX_T)
shared_library.fmpz_mod_poly_rem.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_POLY_T, FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.fmpz_mod_poly_equal.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.fmpz_mod_poly_equal.restype = ctypes.c_int
shared_library.fmpz_mod_poly_clear.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.fmpz_mod_poly_add.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_POLY_T, FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.fmpz_mod_poly_mulmod.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_POLY_T, FMPZ_MOD_POLY_T,
                                                FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)

# Utilities
shared_library.utils_fmpz_to_nmod.argtypes = (NMOD_POLY_TYPE, FMPZ_MOD_POLY_T)
shared_library.utils_nmod_to_fmpz.argtypes = (FMPZ_MOD_POLY_T, NMOD_POLY_TYPE)
shared_library.utils_fmpz_mod_poly_one.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.utils_nmod_poly_one.argtypes = (NMOD_POLY_TYPE,)
shared_library.utils_nmod_poly_zero.argtypes = (NMOD_POLY_TYPE,)
shared_library.utils_print_nmod_poly.argtypes = (NMOD_POLY_TYPE,)
shared_library.utils_pretty_print_nmod_poly.argtypes = (NMOD_POLY_TYPE,)
shared_library.utils_print_fmpz_poly.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.utils_pretty_print_fmpz_poly.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.utils_nmod_poly_to_string.argtypes = (NMOD_POLY_TYPE,)
shared_library.utils_nmod_poly_to_string.restype = ctypes.c_char_p
shared_library.utils_nmod_poly_from_string.argtypes = (NMOD_POLY_TYPE, ctypes.c_char_p)
shared_library.utils_fmpz_mod_poly_to_string.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.utils_fmpz_mod_poly_to_string.restype = ctypes.c_char_p
shared_library.utils_fmpz_mod_poly_from_string.argtypes = (FMPZ_MOD_POLY_T, ctypes.c_char_p)

shared_library.utils_flint_free.argtypes = (ctypes.c_void_p,)

# Encryption scheme
shared_library.qcrt_poly_rec.argtypes = (ENCRYPTION_SCHEME_TYPE, FMPZ_MOD_POLY_T, QCRT_POLY_TYPE)
shared_library.encrypt_setup.argtypes = (ENCRYPTION_SCHEME_TYPE,)
shared_library.encrypt_finish.argtypes = (ENCRYPTION_SCHEME_TYPE,)
shared_library.encrypt_keygen.argtypes = (ENCRYPTION_SCHEME_TYPE, ctypes.POINTER(PublicKey),
                                          ctypes.POINTER(PrivateKey), FLINT_RAND_T)
shared_library.encrypt_keyfree.argtypes = (ENCRYPTION_SCHEME_TYPE, ctypes.POINTER(PublicKey),
                                           ctypes.POINTER(PrivateKey))
shared_library.encrypt_doit.argtypes = (ENCRYPTION_SCHEME_TYPE, ctypes.POINTER(Ciphertext),
                                        # Message
                                        FMPZ_MOD_POLY_T, ctypes.POINTER(PublicKey), FLINT_RAND_T)
shared_library.encrypt_undo.argtypes = (ENCRYPTION_SCHEME_TYPE,
                                        # Message        Challenge
                                        FMPZ_MOD_POLY_T, ctypes.POINTER(FmpzModPoly),
                                        ctypes.POINTER(Ciphertext), ctypes.POINTER(PrivateKey))
shared_library.encrypt_undo.restype = ctypes.c_int
shared_library.encrypt_free.argtypes = (ENCRYPTION_SCHEME_TYPE, ctypes.POINTER(Ciphertext),)
shared_library.encrypt_sample_short.argtypes = (FMPZ_MOD_POLY_T, FMPZ_MOD_CTX_T)
shared_library.encrypt_sample_short_crt.argtypes = (ENCRYPTION_SCHEME_TYPE, QCRT_POLY_TYPE, FMPZ_MOD_CTX_T)
shared_library.encrypt_modulus_ctx.argtypes = (ENCRYPTION_SCHEME_TYPE,)
shared_library.encrypt_modulus_ctx.restype = FMPZ_MOD_CTX_T
shared_library.encrypt_poly.argtypes = (ENCRYPTION_SCHEME_TYPE,)
shared_library.encrypt_poly.restype = FMPZ_MOD_POLY_T

# Commitment scheme
shared_library.commit_scheme_init.argtypes = (COMMITMENT_SCHEME_TYPE,)
shared_library.commit_scheme_finish.argtypes = (COMMITMENT_SCHEME_TYPE,)
shared_library.commit_keygen.argtypes = (ctypes.POINTER(CommitmentKey), FLINT_RAND_T)
shared_library.commit_keyfree.argtypes = (ctypes.POINTER(CommitmentKey),)
shared_library.commit_doit.argtypes = (COMMITMENT_SCHEME_TYPE, ctypes.POINTER(Commitment),
                                       NMOD_POLY_TYPE, ctypes.POINTER(CommitmentKey), PCRT_POLY_TYPE * 3)
shared_library.commit_open.argtypes = (
    COMMITMENT_SCHEME_TYPE,
    # Commitment
    ctypes.POINTER(Commitment),
    # Message
    NMOD_POLY_TYPE,
    # Key
    ctypes.POINTER(CommitmentKey),
    # Randomness
    PCRT_POLY_TYPE * WIDTH,
    # Challenge
    PCRT_POLY_TYPE
)
shared_library.commit_open.restype = ctypes.c_int
shared_library.commit_message_rec.argtypes = (
    COMMITMENT_SCHEME_TYPE,
    # Message
    NMOD_POLY_TYPE,
    # Commitment
    ctypes.POINTER(Commitment),
    # Key
    ctypes.POINTER(CommitmentKey),
    # Randomness
    PCRT_POLY_TYPE * WIDTH
)
shared_library.commit_message_rec.restype = ctypes.c_int
shared_library.commit_sample_rand.argtypes = (NMOD_POLY_TYPE, FLINT_RAND_T, ctypes.c_int)
shared_library.commit_sample_short_crt.argtypes = (COMMITMENT_SCHEME_TYPE, PCRT_POLY_TYPE,)
shared_library.commit_sample_chall_crt.argtypes = (COMMITMENT_SCHEME_TYPE, PCRT_POLY_TYPE,)
shared_library.commit_sample_chall.argtypes = (NMOD_POLY_TYPE,)
shared_library.commit_irred.argtypes = (COMMITMENT_SCHEME_TYPE, ctypes.c_int)
shared_library.commit_irred.restype = ctypes.POINTER(NMOD_POLY_TYPE)
shared_library.commit_free.argtypes = (ctypes.POINTER(Commitment),)

shared_library.commit_ptr_init.argtypes = ()
shared_library.commit_ptr_init.restype = ctypes.POINTER(Commitment)
shared_library.commit_ptr_free.argtypes = (ctypes.POINTER(Commitment),)

shared_library.pcrt_poly_conv.argtypes = (COMMITMENT_SCHEME_TYPE, PCRT_POLY_TYPE, NMOD_POLY_TYPE)
shared_library.pcrt_poly_rec.argtypes = (COMMITMENT_SCHEME_TYPE, NMOD_POLY_TYPE, PCRT_POLY_TYPE)

# Vericrypt
shared_library.vericrypt_doit.argtypes = (ctypes.POINTER(Veritext), FMPZ_MOD_POLY_T * VECTOR, FMPZ_MOD_POLY_T,
                                          FMPZ_MOD_POLY_T * VECTOR, ENCRYPTION_SCHEME_TYPE, ctypes.POINTER(PublicKey),
                                          FLINT_RAND_T)
shared_library.vericrypt_doit.restype = ctypes.c_int
shared_library.vericrypt_undo.argtypes = (FMPZ_MOD_POLY_T * VECTOR, FMPZ_MOD_POLY_T, ctypes.POINTER(Veritext),
                                          FMPZ_MOD_POLY_T * VECTOR, FMPZ_MOD_POLY_T, ENCRYPTION_SCHEME_TYPE,
                                          ctypes.POINTER(PublicKey), ctypes.POINTER(PrivateKey))
shared_library.vericrypt_undo.restype = ctypes.c_int
shared_library.vericrypt_verify.argtypes = (ctypes.POINTER(Veritext), FMPZ_MOD_POLY_T * VECTOR, FMPZ_MOD_POLY_T,
                                            ENCRYPTION_SCHEME_TYPE, ctypes.POINTER(PublicKey))
shared_library.vericrypt_verify.restype = ctypes.c_int
shared_library.vericrypt_cipher_clear.argtypes = (ctypes.POINTER(Veritext), ENCRYPTION_SCHEME_TYPE)

# Shuffle
shared_library.sum_prover.argtypes = (NMOD_POLY_TYPE * 2 * WIDTH,  # y1
                                      NMOD_POLY_TYPE * 2 * WIDTH,  # y2
                                      NMOD_POLY_TYPE * 2 * WIDTH,  # _y1
                                      NMOD_POLY_TYPE * 2,  # t1
                                      NMOD_POLY_TYPE * 2,  # t2
                                      NMOD_POLY_TYPE * 2,  # t3
                                      NMOD_POLY_TYPE * 2,  # u
                                      COMMITMENT_SCHEME_TYPE,
                                      Commitment,  # x1
                                      Commitment,  # x2
                                      Commitment,  # x3
                                      ctypes.POINTER(CommitmentKey),
                                      NMOD_POLY_TYPE,  # alpha
                                      NMOD_POLY_TYPE,  # beta
                                      NMOD_POLY_TYPE * 2 * WIDTH,  # r1
                                      NMOD_POLY_TYPE * 2 * WIDTH,  # r2
                                      NMOD_POLY_TYPE * 2 * WIDTH  # r3
                                      )

shared_library.sum_verifier.argtypes = (NMOD_POLY_TYPE * 2 * WIDTH,  # y1
                                        NMOD_POLY_TYPE * 2 * WIDTH,  # y2
                                        NMOD_POLY_TYPE * 2 * WIDTH,  # _y1
                                        NMOD_POLY_TYPE * 2,  # t1
                                        NMOD_POLY_TYPE * 2,  # t2
                                        NMOD_POLY_TYPE * 2,  # t3
                                        NMOD_POLY_TYPE * 2,  # u
                                        COMMITMENT_SCHEME_TYPE,
                                        Commitment,  # x1
                                        Commitment,  # x2
                                        Commitment,  # x3
                                        ctypes.POINTER(CommitmentKey),
                                        NMOD_POLY_TYPE,  # alpha
                                        NMOD_POLY_TYPE  # beta
                                        )
shared_library.sum_verifier.restype = ctypes.c_int

shared_library.lin_prover.argtypes = (NMOD_POLY_TYPE * 2 * WIDTH,
                                      NMOD_POLY_TYPE * 2 * WIDTH,
                                      NMOD_POLY_TYPE * 2,
                                      NMOD_POLY_TYPE * 2,
                                      NMOD_POLY_TYPE * 2,
                                      COMMITMENT_SCHEME_TYPE,
                                      Commitment,
                                      Commitment,
                                      ctypes.POINTER(CommitmentKey),
                                      NMOD_POLY_TYPE,
                                      NMOD_POLY_TYPE,
                                      NMOD_POLY_TYPE * 2 * WIDTH,
                                      NMOD_POLY_TYPE * 2 * WIDTH,
                                      ctypes.c_int)

shared_library.lin_verifier.argtypes = (NMOD_POLY_TYPE * 2 * WIDTH,
                                        NMOD_POLY_TYPE * 2 * WIDTH,
                                        NMOD_POLY_TYPE * 2,
                                        NMOD_POLY_TYPE * 2,
                                        NMOD_POLY_TYPE * 2,
                                        COMMITMENT_SCHEME_TYPE,
                                        Commitment,
                                        Commitment,
                                        ctypes.POINTER(CommitmentKey),
                                        NMOD_POLY_TYPE,
                                        NMOD_POLY_TYPE,
                                        ctypes.c_int,
                                        ctypes.c_int)

shared_library.lin_verifier.restype = ctypes.c_int

shared_library.shuffle_prover.argtypes = (ctypes.POINTER(OPENING_TYPE),  # y
                                          ctypes.POINTER(OPENING_TYPE),  # _y
                                          ctypes.POINTER(PCRT_POLY_TYPE),  # t
                                          ctypes.POINTER(PCRT_POLY_TYPE),  # _t
                                          ctypes.POINTER(PCRT_POLY_TYPE),  # u
                                          COMMITMENT_SCHEME_TYPE,  # commitment_scheme
                                          ctypes.POINTER(Commitment),  # d
                                          ctypes.POINTER(NMOD_POLY_TYPE),  # s
                                          ctypes.POINTER(ctypes.POINTER(Commitment)),  # com
                                          ctypes.POINTER(NMOD_POLY_TYPE),  # m
                                          ctypes.POINTER(NMOD_POLY_TYPE),  # _m
                                          ctypes.POINTER(OPENING_TYPE),  # r
                                          NMOD_POLY_TYPE,  # rho
                                          ctypes.POINTER(CommitmentKey),  # key
                                          FLINT_RAND_T,  # rng
                                          ctypes.c_int)  # len

shared_library.shuffle_verifier.argtypes = (ctypes.POINTER(OPENING_TYPE),  # y
                                            ctypes.POINTER(OPENING_TYPE),  # _y
                                            ctypes.POINTER(PCRT_POLY_TYPE),  # t
                                            ctypes.POINTER(PCRT_POLY_TYPE),  # _t
                                            ctypes.POINTER(PCRT_POLY_TYPE),  # u
                                            COMMITMENT_SCHEME_TYPE,  # commitment_scheme
                                            ctypes.POINTER(Commitment),  # d
                                            ctypes.POINTER(NMOD_POLY_TYPE),  # s
                                            ctypes.POINTER(ctypes.POINTER(Commitment)),  # com
                                            ctypes.POINTER(NMOD_POLY_TYPE),  # _m
                                            NMOD_POLY_TYPE,  # rho
                                            ctypes.POINTER(CommitmentKey),  # key
                                            ctypes.c_int)  # len
shared_library.shuffle_verifier.restype = ctypes.c_int

shared_library.shuffle_run.argtypes = (COMMITMENT_SCHEME_TYPE,  # commitment_scheme
                                       ctypes.POINTER(ctypes.POINTER(Commitment)),  # com
                                       ctypes.POINTER(NMOD_POLY_TYPE),  # m
                                       ctypes.POINTER(NMOD_POLY_TYPE),  # _m
                                       ctypes.POINTER(OPENING_TYPE),  # r
                                       ctypes.POINTER(CommitmentKey),  # key
                                       FLINT_RAND_T,  # rng
                                       ctypes.c_int)  # len
shared_library.shuffle_run.restype = ctypes.c_int

shared_library.malloc_opening.argtypes = (ctypes.c_size_t,)
shared_library.malloc_opening.restype = ctypes.POINTER(OPENING_TYPE)

shared_library.malloc_pcrt_poly.argtypes = (ctypes.c_size_t,)
shared_library.malloc_pcrt_poly.restype = ctypes.POINTER(PCRT_POLY_TYPE)

shared_library.malloc_poly.argtypes = (ctypes.c_size_t,)
shared_library.malloc_poly.restype = ctypes.POINTER(NMOD_POLY_TYPE)

shared_library.malloc_commit.argtypes = (ctypes.c_size_t,)
shared_library.malloc_commit.restype = ctypes.POINTER(Commitment)

shared_library.fmpz_get_ui.argtypes = (FMPZ_T,)
shared_library.fmpz_get_ui.restype = ctypes.c_ulong

shared_library.fmpz_get_str.argtypes = (ctypes.c_char_p, ctypes.c_int, FMPZ_T)
shared_library.fmpz_get_str.restype = ctypes.c_char_p

shared_library.fmpz_set_str.argtypes = (FMPZ_T, ctypes.c_char_p, ctypes.c_int)
