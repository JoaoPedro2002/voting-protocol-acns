from .classes import Veritext
from .compile import shared_library, ctypes
from .utils import clear_opening
from .primitives import encryption_scheme, commitment_scheme, vericrypt
from .protocol_sum import ProtocolSum


def clear_keys(code_key, decryption_key, public_key):
    pk_C, pk_V, pk_R = public_key
    _, dk_V = decryption_key
    _, _, dk_R = code_key
    encryption_scheme.keyfree(pk_R, dk_R)
    encryption_scheme.keyfree(pk_V, dk_V)
    commitment_scheme.keyfree(pk_C)


def clear_voter(voter):
    _, vck, _ = voter
    a, c_a, d_a = vck
    shared_library.nmod_poly_clear(a)
    shared_library.commit_free(ctypes.byref(c_a))
    clear_opening(shared_library, d_a)


def clear_ev_and_proof(ballot, proof):
    c, e_cipher, e_c = ballot
    z, c_r, e_r, sum_proof = proof
    shared_library.commit_free(ctypes.byref(c))
    shared_library.commit_free(ctypes.byref(c_r))
    vericrypt.cipher_clear(Veritext(
        cipher=e_cipher,
        c=e_c,
        r=z[0],
        e=z[1],
        e_=z[2],
        u=z[3]
    ))
    ProtocolSum.proof_clear(shared_library, sum_proof)