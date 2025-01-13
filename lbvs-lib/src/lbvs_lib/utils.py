import itertools

from Crypto.Random.random import StrongRandom

from .compile import ctypes, MODP, WIDTH, VECTOR, DIM
from .classes import (FLINT_RAND_T, NMOD_POLY_TYPE, FMPZ_MOD_POLY_T, PCRT_POLY_TYPE,
                     COMMITMENT_SCHEME_TYPE, FMPZ_MOD_CTX_T, Commitment, Ciphertext, Veritext)

random = StrongRandom()

"""
Utility functions
"""
def get_all_voting_combinations(answers, minimum, maximum) -> iter:
    return (combination for i in range(minimum, maximum + 1)
            for combination in itertools.combinations(range(len(answers)), i))


def new_random_question(len_a=None, len_max=None, len_min=None, answers=None) -> dict:
    if answers is not None:
        len_a = len(answers)
    elif len_a is None:
        len_a = random.randint(1, 10)

    len_max = random.randint(1, len_a) if len_max is None else len_max
    len_min = random.randint(1, len_max) if len_min is None else len_min

    answers = [random.randint(0, 100) for _ in range(len_a)] if answers is None else answers
    return {
        'answers': answers,
        'min': len_min,
        'max': len_max,
        'result_type': 'relative',
        'tally_type': 'homomorphic',
        'choice_type': 'approval',
    }


def valid_vote_for_question(question, vote) -> bool:
    try:
        assert len(vote) < question['min'] or len(vote) > question['max'], 'Invalid vote length'
        assert max(vote) >= (len(question['answers']) - 1) or min(vote) < 0, 'Invalid vote value'
        assert len(vote) != len(set(vote)), 'Duplicate vote'
        return True
    except AssertionError:
        return False


def new_flint_random(shared_library) -> FLINT_RAND_T:
    uint64_bit_size = 64
    b1 = ctypes.c_ulong(random.getrandbits(uint64_bit_size))
    b2 = ctypes.c_ulong(random.getrandbits(uint64_bit_size))
    rand = FLINT_RAND_T()
    shared_library.flint_randinit(rand)
    shared_library.flint_randseed(rand, b1, b2)
    return rand


def nmod_poly_to_fmpz(shared_library, poly: NMOD_POLY_TYPE, ctx) -> FMPZ_MOD_POLY_T:
    fmpz = FMPZ_MOD_POLY_T()
    shared_library.fmpz_mod_poly_init(fmpz, ctx)
    shared_library.utils_nmod_to_fmpz(fmpz, poly)
    return fmpz


def fmpz_to_nmod_poly(shared_library, fmpz: FMPZ_MOD_POLY_T) -> NMOD_POLY_TYPE:
    poly = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(poly, MODP)
    shared_library.utils_fmpz_to_nmod(poly, fmpz)
    return poly


def pcrt_poly_rec(shared_library, scheme: COMMITMENT_SCHEME_TYPE, poly: PCRT_POLY_TYPE) -> NMOD_POLY_TYPE:
    c = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(c, MODP)
    shared_library.pcrt_poly_rec(scheme, c, poly)
    return c


def pcrt_poly_conv(shared_library, scheme: COMMITMENT_SCHEME_TYPE, poly: NMOD_POLY_TYPE) -> FMPZ_MOD_POLY_T:
    c = PCRT_POLY_TYPE()
    shared_library.nmod_poly_init(c[0], MODP)
    shared_library.nmod_poly_init(c[1], MODP)
    shared_library.pcrt_poly_conv(scheme, c, poly)
    return c


def opening_to_fmpz(shared_library, opening: PCRT_POLY_TYPE * WIDTH, scheme: COMMITMENT_SCHEME_TYPE,
                    ctx: FMPZ_MOD_CTX_T) -> (FMPZ_MOD_POLY_T * WIDTH, FMPZ_MOD_POLY_T * WIDTH):
    fmpz = (FMPZ_MOD_POLY_T * WIDTH)()
    for i in range(WIDTH):
        tmp = pcrt_poly_rec(shared_library, scheme, opening[i])
        fmpz[i] = nmod_poly_to_fmpz(shared_library, tmp, ctx)
        shared_library.nmod_poly_clear(tmp)

    return fmpz

def c1_to_fmpz(shared_library, c1, scheme, ctx):
    tmp = pcrt_poly_rec(shared_library, scheme, c1)
    fmpz = nmod_poly_to_fmpz(shared_library, tmp, ctx)
    shared_library.nmod_poly_clear(tmp)
    return fmpz


def b1_to_fmpz(shared_library, b1, scheme, ctx):
    return opening_to_fmpz(shared_library, b1[0], scheme, ctx)


def fmpz_to_opening(shared_library, fmpz: FMPZ_MOD_POLY_T * WIDTH,
                    scheme: COMMITMENT_SCHEME_TYPE) -> PCRT_POLY_TYPE * WIDTH:
    opening = (PCRT_POLY_TYPE * WIDTH)()
    for i in range(WIDTH):
        tmp = fmpz_to_nmod_poly(shared_library, fmpz[i])
        opening[i] = pcrt_poly_conv(shared_library, scheme, tmp)
        shared_library.nmod_poly_clear(tmp)

    return opening


def print_fmpz_mod_poly(shared_library, poly: FMPZ_MOD_POLY_T, ctx: FMPZ_MOD_CTX_T, pretty=True):
    if pretty:
        shared_library.utils_pretty_print_fmpz_poly(poly, ctx)
    else:
        shared_library.utils_print_fmpz_poly(poly, ctx)
    print()


def print_message_space(shared_library, message: FMPZ_MOD_POLY_T * VECTOR, ctx: FMPZ_MOD_CTX_T, pretty=True):
    for i in range(VECTOR):
        print_fmpz_mod_poly(shared_library, message[i], ctx, pretty)
    print()


def print_nmod_poly(shared_library, poly: NMOD_POLY_TYPE, pretty=True):
    if pretty:
        shared_library.utils_pretty_print_nmod_poly(poly)
    else:
        shared_library.utils_print_nmod_poly(poly)
    print()


def print_opening(shared_library, opening: PCRT_POLY_TYPE * WIDTH, pretty=True):
    for i in range(WIDTH):
        for j in range(2):
            print_nmod_poly(shared_library, opening[i][j], pretty)
    print()


def nmod_poly_to_string(shared_library, poly: NMOD_POLY_TYPE) -> str:
    c_p = shared_library.utils_nmod_poly_to_string(poly)
    s = ctypes.string_at(c_p).decode('ascii')
    return s


def nmod_poly_from_string(shared_library, s):
    poly = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(poly, MODP)
    shared_library.utils_nmod_poly_from_string(poly, s.encode('ascii'))
    return poly


def fmpz_mod_poly_to_string(shared_library, poly: FMPZ_MOD_POLY_T, ctx: FMPZ_MOD_CTX_T) -> str:
    c_p = shared_library.utils_fmpz_mod_poly_to_string(poly, ctx)
    s = ctypes.string_at(c_p).decode('ascii')
    return s


def fmpz_mod_poly_from_string(shared_library, s: str, ctx):
    poly = FMPZ_MOD_POLY_T()
    shared_library.fmpz_mod_poly_init(poly, ctx)
    shared_library.utils_fmpz_mod_poly_from_string(poly, s.encode('ascii'))
    return poly


# ----- Auditor Utils -----

def ev_equals(shared_library, ev1, ev2, ctx):
    """
    Compare encrypted_votes
    :param shared_library: Shared library
    :param ev1: first encrypted_vote
    :param ev2: second encrypted_vote
    :param ctx: Context
    """
    ev1_com, ev1_cipher, ev1_c = ev1
    ev2_com, ev2_cipher, ev2_c = ev2

    if not Commitment.equals(ev1_com, ev2_com):
        return False

    for i in range(VECTOR):
        if not Ciphertext.equals(ev1_cipher[i], ev2_cipher[i], ctx):
            return False

    return shared_library.fmpz_mod_poly_equal(ev1_c, ev1_c, ctx) == 1

def pv_equals(shared_library, pv1, pv2, ctx):
    """
    Compare ballot proofs
    :param shared_library: Shared library
    :param pv1: first ballot proof
    :param pv2: second ballot proof
    :param ctx: Context
    """
    pv1_z, pv1_com, pv1_enc, pv1_proof = pv1
    pv2_z, pv2_com, pv2_enc, pv2_proof = pv2

    if not Commitment.equals(pv1_com, pv2_com):
        return False

    if not Veritext.equals(pv1_enc, pv2_enc, ctx):
        return False



    if not proof_equals(shared_library, pv1_proof, pv2_proof):
        return False

    z1_r, z1_e, z1_e_, z1_u = pv1_z
    z2_r, z2_e, z2_e_, z2_u = pv2_z

    for i in range(VECTOR):
        for j in range(DIM):
            for k in range(2):
                if not shared_library.fmpz_mod_poly_equal(z1_r[i][j][k], z2_r[i][j][k], ctx) == 1:
                    return False
                if not shared_library.fmpz_mod_poly_equal(z1_e[i][j][k], z2_e[i][j][k], ctx) == 1:
                    return False
        for j in range(2):
            if not shared_library.fmpz_mod_poly_equal(z1_e_[i][j], z2_e_[i][j], ctx) == 1:
                return False
        if not shared_library.fmpz_mod_poly_equal(z1_u[i], z2_u[i], ctx) == 1:
            return False
    return True

def proof_equals(shared_library, pv1_proof, pv2_proof):
    """
    Compare proofs for sum
    :param shared_library: Shared library
    :param pv1_proof: first proof
    :param pv2_proof: second proof
    """
    pv1_y1, pv1_y2, pv1_y3, pv1_t1, pv1_t2, pv1_t3, pv1_u = pv1_proof
    pv2_y1, pv2_y2, pv2_y3, pv2_t1, pv2_t2, pv2_t3, pv2_u = pv2_proof

    for i in range(WIDTH):
        for j in range(2):
            if not shared_library.nmod_poly_equal(pv1_y1[i][j], pv2_y1[i][j]) == 1:
                return False
            if not shared_library.nmod_poly_equal(pv1_y2[i][j], pv2_y2[i][j]) == 1:
                return False
            if not shared_library.nmod_poly_equal(pv1_y3[i][j], pv2_y3[i][j]) == 1:
                return False

    for i in range(2):
        if not shared_library.nmod_poly_equal(pv1_t1[i], pv2_t1[i]) == 1:
            return False
        if not shared_library.nmod_poly_equal(pv1_t2[i], pv2_t2[i]) == 1:
            return False
        if not shared_library.nmod_poly_equal(pv1_t3[i], pv2_t3[i]) == 1:
            return False
        if not shared_library.nmod_poly_equal(pv1_u[i], pv2_u[i]) == 1:
            return False
    return True
