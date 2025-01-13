from typing import Any

from .primitives import primitives

from .classes import *
from .primitives import vericrypt
from .utils import nmod_poly_to_string, fmpz_mod_poly_to_string, fmpz_mod_poly_from_string, nmod_poly_from_string

class NmodRepr:

    def str_poly_serialize(self, poly):
        return nmod_poly_to_string(shared_library, poly)

    def str_poly_deserialize(self, poly, s):
        shared_library.utils_nmod_poly_from_string(poly, s.encode('ascii'))

    def list_poly_serialize(self, poly):
        length = shared_library.nmod_poly_length(poly)
        list_of_coeffs = []
        for i in range(length):
            coeff = shared_library.nmod_poly_get_coeff_ui(poly, i)
            if coeff != 0:
                list_of_coeffs.append([i, coeff])

        return list_of_coeffs

    def list_poly_deserialize(self, poly, s):
        shared_library.nmod_poly_zero(poly)
        for coeff in s:
            shared_library.nmod_poly_set_coeff_ui(poly, coeff[0], coeff[1])

    def __init__(self, type='list'):
        self.type = type
        if type == 'list':
            self.serialize = self.list_poly_serialize
            self.deserialize = self.list_poly_deserialize
        elif type == 'str':
            self.serialize = self.str_poly_serialize
            self.deserialize = self.str_poly_deserialize


class FmpzRepr:

    def str_poly_serialize(self, poly, ctx):
        return fmpz_mod_poly_to_string(shared_library, poly, ctx)

    def str_poly_deserialize(self, poly, s, ctx):
        shared_library.utils_fmpz_mod_poly_from_string(poly, s.encode('ascii'))

    def list_poly_serialize(self, poly, ctx):
        length = shared_library.fmpz_mod_poly_length(poly)
        list_of_coeffs = []
        fmpz = FMPZ_T()
        shared_library.fmpz_init(fmpz)
        for i in range(length):
            shared_library.fmpz_mod_poly_get_coeff_fmpz(fmpz, poly, i, ctx)
            coeff = shared_library.fmpz_get_str(None, 10, fmpz)
            if coeff != b'0':
                list_of_coeffs.append([i, coeff.decode('ascii')])
        shared_library.fmpz_clear(fmpz)
        return list_of_coeffs

    def list_poly_deserialize(self, poly, s, ctx):
        shared_library.fmpz_mod_poly_zero(poly, ctx)
        fmpz = FMPZ_T()
        shared_library.fmpz_init(fmpz)
        for coeff in s:
            shared_library.fmpz_set_str(fmpz, coeff[1].encode("ascii"), 10)
            shared_library.fmpz_mod_poly_set_coeff_fmpz(poly, coeff[0], fmpz, ctx)
        shared_library.fmpz_clear(fmpz)

    def __init__(self, type='list'):
        self.type = type
        if type == 'list':
            self.serialize = self.list_poly_serialize
            self.deserialize = self.list_poly_deserialize
        elif type == 'str':
            self.serialize = self.str_poly_serialize
            self.deserialize = self.str_poly_deserialize


fmpz_repr = FmpzRepr()
nmod_repr = NmodRepr()

def set_repr(repr):
    global fmpz_repr, nmod_repr
    fmpz_repr = FmpzRepr(repr)
    nmod_repr = NmodRepr(repr)

def serialize_nmod_poly(poly: NMOD_POLY_TYPE) -> list[list[int]] | str:
    """
    Serialize an NMOD_POLY_TYPE
    :param poly: the NMOD_POLY_TYPE to serialize
    :return: the serialized NMOD_POLY_TYPE
    """
    return nmod_repr.serialize(poly)


def deserialize_nmod_poly(s: list[list[int]]) -> NMOD_POLY_TYPE:
    """
    Deserialize an NMOD_POLY_TYPE
    :param s: the serialized NMOD_POLY_TYPE
    :return
    """
    poly = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(poly, MODP)
    nmod_repr.deserialize(poly, s)
    return poly

def serialize_fmpz_mod_poly(poly: FMPZ_MOD_POLY_T, ctx) -> list[list[str]] | str:
    """
    Serialize an FMPZ_MOD_POLY_TYPE
    :param poly: the FMPZ_MOD_POLY_TYPE to serialize
    :param ctx: the context
    :return: the serialized FMPZ_MOD_POLY_TYPE
    """
    return fmpz_repr.serialize(poly, ctx)

def deserialize_fmpz_mod_poly(s: list[list[str]], ctx) -> FMPZ_MOD_POLY_T:
    """
    Deserialize an FMPZ_MOD_POLY_TYPE
    :param s: the serialized FMPZ_MOD_POLY_TYPE
    :param ctx: the context
    :return
    """
    poly = FMPZ_MOD_POLY_T()
    shared_library.fmpz_mod_poly_init(poly, ctx)
    fmpz_repr.deserialize(poly, s, ctx)
    return poly

def recursive_serialize_nmod_poly(poly_matrix, dimensions: list[int]):
    dimension_len = dimensions.pop(0)
    serialized_polys = []
    if len(dimensions) == 0:
        for i in range(dimension_len):
            serialized_polys.append(serialize_nmod_poly(poly_matrix[i]))
    else:
        for i in range(dimension_len):
            serialized_polys.append(recursive_serialize_nmod_poly(poly_matrix[i], dimensions.copy()))
    return serialized_polys


def recursive_deserialize_nmod_poly(poly_matrix, serialized_polys, dimensions: list[int]):
    dimension = dimensions.pop(0)
    if len(dimensions) == 0:
        for i in range(dimension):
            shared_library.nmod_poly_init(poly_matrix[i], MODP)
            nmod_repr.deserialize(poly_matrix[i], serialized_polys[i])
    else:
        for i in range(dimension):
            recursive_deserialize_nmod_poly(poly_matrix[i], serialized_polys[i], dimensions.copy())


def recursive_serialize_fmpz_mod_poly(poly_matrix, dimensions: list[int], ctx):
    dimension_len = dimensions.pop(0)
    serialized_polys = []
    if len(dimensions) == 0:
        for i in range(dimension_len):
            serialized_polys.append(serialize_fmpz_mod_poly(poly_matrix[i], ctx))
    else:
        for i in range(dimension_len):
            serialized_polys.append(recursive_serialize_fmpz_mod_poly(poly_matrix[i], dimensions.copy(), ctx))
    return serialized_polys

def recursive_deserialize_fmpz_mod_poly(poly_matrix, serialized_polys, dimensions: list[int], ctx):
    dimension = dimensions.pop(0)
    if len(dimensions) == 0:
        fmpz = FMPZ_T()
        shared_library.fmpz_init(fmpz)
        for i in range(dimension):
            shared_library.fmpz_mod_poly_init(poly_matrix[i], ctx)
            fmpz_repr.deserialize(poly_matrix[i], serialized_polys[i], ctx)
        shared_library.fmpz_clear(fmpz)
    else:
        for i in range(dimension):
            recursive_deserialize_fmpz_mod_poly(poly_matrix[i], serialized_polys[i], dimensions.copy(), ctx)

# encryption scheme
def serialize_public_key(key: PublicKey) -> dict[str, Any]:
    """
    Serialize a PublicKey
    :param key: the PublicKey to serialize
    :return: the serialized PublicKey
    """
    return {
        "A": recursive_serialize_fmpz_mod_poly(key.A, [DIM, DIM, 2], vericrypt.context),
        "t": recursive_serialize_fmpz_mod_poly(key.t, [DIM, 2], vericrypt.context)
    }

def deserialize_public_key(d: dict[str, Any]) -> PublicKey:
    """
    Deserialize a PublicKey
    :param d: the serialized PublicKey
    :return
    """
    key = PublicKey()
    recursive_deserialize_fmpz_mod_poly(key.A, d["A"], [DIM, DIM, 2], vericrypt.context)
    recursive_deserialize_fmpz_mod_poly(key.t, d["t"], [DIM, 2], vericrypt.context)
    return key

def serialize_private_key(key: PrivateKey) -> dict[str, Any]:
    """
    Serialize a PrivateKey
    :param key: the PrivateKey to serialize
    :return: the serialized PrivateKey
    """
    return {
        "s1": recursive_serialize_fmpz_mod_poly(key.s1, [DIM, 2], vericrypt.context),
        "s2": recursive_serialize_fmpz_mod_poly(key.s2, [DIM, 2], vericrypt.context)
    }

def deserialize_private_key(d: dict[str, Any]) -> PrivateKey:
    """
    Deserialize a PrivateKey
    :param d: the serialized PrivateKey
    :return
    """
    key = PrivateKey()
    recursive_deserialize_fmpz_mod_poly(key.s1, d["s1"], [DIM, 2], vericrypt.context)
    recursive_deserialize_fmpz_mod_poly(key.s2, d["s2"], [DIM, 2], vericrypt.context)
    return key

def serialize_ciphertext(ciphertext: Ciphertext) -> dict[str, Any]:
    """
    Serialize a Ciphertext
    :param ciphertext: the Ciphertext to serialize
    :return: the serialized Ciphertext
    """
    return {
        "v": recursive_serialize_fmpz_mod_poly(ciphertext.v, [DIM, 2], vericrypt.context),
        "w": recursive_serialize_fmpz_mod_poly(ciphertext.w, [2], vericrypt.context)
    }

def deserialize_ciphertext(d: dict[str, Any], ciphertext=None) -> Ciphertext:
    """
    Deserialize a Ciphertext
    :param d: the serialized Ciphertext
    :param ciphertext: the Ciphertext to deserialize
    :return
    """
    if ciphertext is None:
        ciphertext = Ciphertext()
    recursive_deserialize_fmpz_mod_poly(ciphertext.v, d["v"], [DIM, 2], vericrypt.context)
    recursive_deserialize_fmpz_mod_poly(ciphertext.w, d["w"], [2], vericrypt.context)
    return ciphertext

# vericrypt

def serialize_veritext(veritext: Veritext) -> dict[str, Any]:
    """
    Serialize a Veritext
    :param veritext: the Veritext to serialize
    :return: the serialized Veritext
    """
    return {
        "cipher": [serialize_ciphertext(veritext.cipher[i]) for i in range(VECTOR)],
        "c": serialize_fmpz_mod_poly(veritext.c, vericrypt.context_p),
        "r": recursive_serialize_fmpz_mod_poly(veritext.r, [VECTOR, DIM, 2], vericrypt.context),
        "e": recursive_serialize_fmpz_mod_poly(veritext.e, [VECTOR, DIM, 2], vericrypt.context),
        "e_": recursive_serialize_fmpz_mod_poly(veritext.e_, [VECTOR, 2], vericrypt.context),
        "u": recursive_serialize_fmpz_mod_poly(veritext.u, [VECTOR], vericrypt.context_p)
    }

def deserialize_veritext(d: dict[str, Any]) -> Veritext:
    """
    Deserialize a Veritext
    :param d: the serialized Veritext
    :return
    """
    veritext = Veritext()
    for i in range(VECTOR):
        deserialize_ciphertext(d["cipher"][i], veritext.cipher[i])
    veritext.c = deserialize_fmpz_mod_poly(d["c"], vericrypt.context_p)
    recursive_deserialize_fmpz_mod_poly(veritext.r, d["r"], [VECTOR, DIM, 2], vericrypt.context)
    recursive_deserialize_fmpz_mod_poly(veritext.e, d["e"], [VECTOR, DIM, 2], vericrypt.context)
    recursive_deserialize_fmpz_mod_poly(veritext.e_, d["e_"], [VECTOR, 2], vericrypt.context)
    recursive_deserialize_fmpz_mod_poly(veritext.u, d["u"], [VECTOR], vericrypt.context_p)
    return veritext

# commitment scheme
def serialize_commitment(commitment: Commitment) -> dict[str, list[Any]]:
    """
    Serialize a Commitment
    :param commitment: the Commitment to serialize
    :return: the serialized Commitment
    """
    return {
        "c1": recursive_serialize_nmod_poly(commitment.c1, [2]),
        "c2": recursive_serialize_nmod_poly(commitment.c2, [2])
    }

def deserialize_commitment(d: dict[str, list[Any]]) -> Commitment:
    """
    Deserialize a Commitment
    :param d: the serialized Commitment
    :return
    """
    commitment = Commitment()
    recursive_deserialize_nmod_poly(commitment.c1, d["c1"], [2])
    recursive_deserialize_nmod_poly(commitment.c2, d["c2"], [2])
    return commitment

def serialize_commitment_key(key: CommitmentKey) -> dict[str, Any]:
    """
    Serialize a CommitmentKey
    :param key: the CommitmentKey to serialize
    :return: the serialized CommitmentKey
    """
    return {
        "B1": recursive_serialize_nmod_poly(key.B1, [HEIGHT, WIDTH, 2]),
        "b2": recursive_serialize_nmod_poly(key.b2, [WIDTH, 2])
    }

def deserialize_commitment_key(d: dict[str, Any]) -> CommitmentKey:
    """
    Deserialize a CommitmentKey
    :param d: the serialized CommitmentKey
    :return
    """
    key = CommitmentKey()
    recursive_deserialize_nmod_poly(key.B1, d["B1"], [HEIGHT, WIDTH, 2])
    recursive_deserialize_nmod_poly(key.b2, d["b2"], [WIDTH, 2])
    return key

# setup

def serialize_pk(pk):
    pk_C, pk_V, pk_R = pk
    return {
        "pk_C": serialize_commitment_key(pk_C),
        "pk_V": serialize_public_key(pk_V),
        "pk_R": serialize_public_key(pk_R)
    }

def deserialize_pk(d):
    pk_C = deserialize_commitment_key(d["pk_C"])
    pk_V = deserialize_public_key(d["pk_V"])
    pk_R = deserialize_public_key(d["pk_R"])
    return pk_C, pk_V, pk_R

def serialize_dk(dk):
    pk_C, dk_V = dk
    return {
        "pk_C": serialize_commitment_key(pk_C),
        "dk_V": serialize_private_key(dk_V)
    }

def deserialize_dk(d):
    pk_C = deserialize_commitment_key(d["pk_C"])
    dk_V = deserialize_private_key(d["dk_V"])
    return pk_C, dk_V

def serialize_ck(ck):
    pk_C, pk_V, dk_R = ck
    return {
        "pk_C": serialize_commitment_key(pk_C),
        "pk_V": serialize_public_key(pk_V),
        "dk_R": serialize_private_key(dk_R)
    }

def deserialize_ck(d):
    pk_C = deserialize_commitment_key(d["pk_C"])
    pk_V = deserialize_public_key(d["pk_V"])
    dk_R = deserialize_private_key(d["dk_R"])
    return pk_C, pk_V, dk_R

# register

def serialize_vvk(vvk):
    return serialize_commitment(vvk)

def deserialize_vvk(vvk):
    return deserialize_commitment(vvk)

def serialize_vck(vck):
    a, c_a, d_a = vck
    return {
        "a": serialize_nmod_poly(a),
        "c_a": serialize_commitment(c_a),
        "d_a": recursive_serialize_nmod_poly(d_a, [WIDTH, 2])
    }

def deserialize_vck(vck):
    a = deserialize_nmod_poly(vck["a"])
    c_a = deserialize_commitment(vck["c_a"])
    d_a = (NMOD_POLY_TYPE * 2 * WIDTH)()
    recursive_deserialize_nmod_poly(d_a, vck["d_a"], [WIDTH, 2])
    return a, c_a, d_a

# cast

def serialize_encrypted_ballot(ev):
    c, cipher, e_c = ev
    return {
        "c": serialize_commitment(c),
        "cipher": [serialize_ciphertext(cipher[i]) for i in range(VECTOR)],
        "e_c": serialize_fmpz_mod_poly(e_c, vericrypt.context_p),
    }

def deserialize_encrypted_ballot(ev):
    c = deserialize_commitment(ev["c"])
    cipher = (Ciphertext * VECTOR)()
    for i in range(VECTOR):
        deserialize_ciphertext(ev["cipher"][i], cipher[i])
    e_c = deserialize_fmpz_mod_poly(ev["e_c"], vericrypt.context_p)
    return c, cipher, e_c

def serialize_sum_proof(proof):
    y1, y2, y3, t1, t2, t3, u = proof
    return {
        "y1": recursive_serialize_nmod_poly(y1, [WIDTH, 2]),
        "y2": recursive_serialize_nmod_poly(y2, [WIDTH, 2]),
        "y3": recursive_serialize_nmod_poly(y3, [WIDTH, 2]),
        "t1": recursive_serialize_nmod_poly(t1, [2]),
        "t2": recursive_serialize_nmod_poly(t2, [2]),
        "t3": recursive_serialize_nmod_poly(t3, [2]),
        "u": recursive_serialize_nmod_poly(u, [2])
    }

def deserialize_sum_proof(proof):
    y1 = (NMOD_POLY_TYPE * 2 * WIDTH)()
    recursive_deserialize_nmod_poly(y1, proof["y1"], [WIDTH, 2])
    y2 = (NMOD_POLY_TYPE * 2 * WIDTH)()
    recursive_deserialize_nmod_poly(y2, proof["y2"], [WIDTH, 2])
    y3 = (NMOD_POLY_TYPE * 2 * WIDTH)()
    recursive_deserialize_nmod_poly(y3, proof["y3"], [WIDTH, 2])
    t1 = (NMOD_POLY_TYPE * 2)()
    recursive_deserialize_nmod_poly(t1, proof["t1"], [2])
    t2 = (NMOD_POLY_TYPE * 2)()
    recursive_deserialize_nmod_poly(t2, proof["t2"], [2])
    t3 = (NMOD_POLY_TYPE * 2)()
    recursive_deserialize_nmod_poly(t3, proof["t3"], [2])
    u = (NMOD_POLY_TYPE * 2)()
    recursive_deserialize_nmod_poly(u, proof["u"], [2])

    return y1, y2, y3, t1, t2, t3, u

def serialize_z(z):
    r, e, e_, u = z
    return {
        "r": recursive_serialize_fmpz_mod_poly(r, [VECTOR, DIM, 2], vericrypt.context),
        "e": recursive_serialize_fmpz_mod_poly(e, [VECTOR, DIM, 2], vericrypt.context),
        "e_": recursive_serialize_fmpz_mod_poly(e_, [VECTOR, 2], vericrypt.context),
        "u": recursive_serialize_fmpz_mod_poly(u, [VECTOR], vericrypt.context_p)
    }

def deserialize_z(z):
    r = (FMPZ_MOD_POLY_T * 2 * DIM * VECTOR)()
    recursive_deserialize_fmpz_mod_poly(r, z["r"], [VECTOR, DIM, 2], vericrypt.context)
    e = (FMPZ_MOD_POLY_T * 2 * DIM * VECTOR)()
    recursive_deserialize_fmpz_mod_poly(e, z["e"], [VECTOR, DIM, 2], vericrypt.context)
    e_ = (FMPZ_MOD_POLY_T * 2 * VECTOR)()
    recursive_deserialize_fmpz_mod_poly(e_, z["e_"], [VECTOR, 2], vericrypt.context)
    u = (FMPZ_MOD_POLY_T * VECTOR)()
    recursive_deserialize_fmpz_mod_poly(u, z["u"], [VECTOR], vericrypt.context_p)
    return r, e, e_, u

def serialize_ballot_proof(proof):
    z, c_r, e_r, sproof = proof
    return {
        "z": serialize_z(z),
        "c_r": serialize_commitment(c_r),
        "e_r": serialize_veritext(e_r),
        "sproof": serialize_sum_proof(sproof)
    }

def deserialize_ballot_proof(proof):
    z = deserialize_z(proof["z"])
    c_r = deserialize_commitment(proof["c_r"])
    e_r = deserialize_veritext(proof["e_r"])
    sproof = deserialize_sum_proof(proof["sproof"])
    return z, c_r, e_r, sproof

def serialize_shuffle_proof(proof):
    y, _y, t, _t, u, d, s, rho = proof

    length = len(y)
    return {
        "y": recursive_serialize_nmod_poly(y, [length, WIDTH, 2]),
        "_y": recursive_serialize_nmod_poly(_y, [length, WIDTH, 2]),
        "t": recursive_serialize_nmod_poly(t, [length, 2]),
        "_t": recursive_serialize_nmod_poly(_t, [length, 2]),
        "u": recursive_serialize_nmod_poly(u, [length, 2]),
        "d": [serialize_commitment(d[i]) for i in range(length)],
        "s": recursive_serialize_nmod_poly(s, [length]),
        "rho": serialize_nmod_poly(rho)
    }

def deserialize_shuffle_proof(proof):
    length = len(proof["y"])
    y = (NMOD_POLY_TYPE * 2 * WIDTH * length)()
    recursive_deserialize_nmod_poly(y, proof["y"], [length, WIDTH, 2])
    _y = (NMOD_POLY_TYPE * 2 * WIDTH * length)()
    recursive_deserialize_nmod_poly(_y, proof["_y"], [length, WIDTH, 2])
    t = (NMOD_POLY_TYPE * 2 * length)()
    recursive_deserialize_nmod_poly(t, proof["t"], [length, 2])
    _t = (NMOD_POLY_TYPE * 2 * length)()
    recursive_deserialize_nmod_poly(_t, proof["_t"], [length, 2])
    u = (NMOD_POLY_TYPE * 2 * length)()
    recursive_deserialize_nmod_poly(u, proof["u"], [length, 2])
    d = (Commitment * length)()
    for i in range(length):
        d[i] = deserialize_commitment(proof["d"][i])
    s = (NMOD_POLY_TYPE * length)()
    recursive_deserialize_nmod_poly(s, proof["s"], [length])
    rho = deserialize_nmod_poly(proof["rho"])
    return y, _y, t, _t, u, d, s, rho