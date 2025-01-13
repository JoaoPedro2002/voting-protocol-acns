from typing import Tuple
import timeit

from .classes import Commitment, CommitmentKey, Ciphertext, PublicKey, NMOD_POLY_TYPE, PCRT_POLY_TYPE, FMPZ_MOD_POLY_T, \
    Veritext
from .compile import DEGREE, MODP, VECTOR, WIDTH, shared_library, ctypes
from .primitives import commitment_scheme, encryption_scheme, vericrypt, flint_rand
from .protocol_sum import ProtocolSum
from .shuffle import Shuffle
from .utils import (fmpz_to_opening, opening_to_fmpz, c1_to_fmpz, b1_to_fmpz, print_nmod_poly,
                    print_fmpz_mod_poly)
from .cleanup import clear_opening


def ballot_to_precode(v, a):
    returnable = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(returnable, MODP)
    shared_library.nmod_poly_add(returnable, v, a)
    return returnable


def setup():
    """
    In the setup phase, a trusted set of players run the setup algorithm Setup.
    The derived public key pk is given to every player, the decryption key dk is given
    to the shuffler S and the code key ck is given to the return code generator R
    """

    # pk_C <- KeyGen_C
    pk_C = commitment_scheme.keygen()

    # (pk_V, dk_V) <- KeyGen_VE
    pk_V, dk_V = encryption_scheme.keygen()

    # (pk_R, dk_R) <- KeyGen_VE
    pk_R, dk_R = encryption_scheme.keygen()

    # public key
    pk = (pk_C, pk_V, pk_R)
    # decryption key
    dk = (pk_C, dk_V)
    # code key
    ck = (pk_C, pk_V, dk_R)

    return pk, dk, ck


def register(pk):
    """
    :param pk: public key (pk_C, pk_V, pk_R)
    """
    pk_C, pk_V, pk_R = pk

    # samples a <- R_p
    a = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(a, MODP)
    shared_library.nmod_poly_randtest(a, flint_rand, DEGREE)

    # computes (c_a, d_a) ← Com(pk_C , a)
    c_a, d_a = commitment_scheme.commit(pk_C, a, only_r=True)

    # the voter verification key is vvk = c_a
    vvk = c_a

    # the voter casting key is vck = (a, c_a, d_a)
    vck = (a, c_a, d_a)

    # the function f is v -> v + a
    def _f(v):
        return ballot_to_precode(v, a)

    f = _f

    return vvk, vck, f


def __decrypt_opening(dk, e: Ciphertext * VECTOR) -> NMOD_POLY_TYPE:
    r = (FMPZ_MOD_POLY_T * VECTOR)()
    for i in range(VECTOR):
        r[i], result = encryption_scheme.decrypt(e[i], dk)
        assert result, "Decryption failed for r [%d]" % i
    return r


def __encrypt_opening(pk, d, c: Commitment, pk_C: CommitmentKey) -> Veritext:
    # convert c.c1 to FMPZ
    u = c1_to_fmpz(shared_library, c.c1, commitment_scheme.scheme, vericrypt.context_p)
    # conver pk_C.B1 to fmpz
    t = b1_to_fmpz(shared_library, pk_C.B1, commitment_scheme.scheme, vericrypt.context_p)
    # convert d to FMPZ_MOD_POLY_T * VECTOR
    fmpz_d = opening_to_fmpz(shared_library, d, commitment_scheme.scheme, vericrypt.context_p)
    e, result = vericrypt.encrypt(t, u, fmpz_d, pk)
    # print_message_space(self.shared_library, fmpz_d, self.vericrypt.context)
    assert result, "Encryption failed for pk"
    return e


def cast(pk: Tuple[CommitmentKey, PublicKey, PublicKey],
         vck: Tuple[NMOD_POLY_TYPE, Commitment, PCRT_POLY_TYPE * WIDTH],
         v: NMOD_POLY_TYPE):
    """
    :param pk: public key (pk_C, pk_V, pk_R)
    :param vck: voter casting key (a, c_a, d_a)
    :param v: vote
    """
    pk_C, pk_V, pk_R = pk
    a, c_a, d_a = vck

    # computes (c, d) ← Com(pk_C , v)
    (c, d) = commitment_scheme.commit(pk_C, v, only_r=True)

    # r ← a + v
    r: NMOD_POLY_TYPE = ballot_to_precode(v, a)

    # (c_r, d_r) ← Com(pk_C , r)
    (c_r, d_r) = commitment_scheme.commit(pk_C, r, only_r=True)
    # print_opening(self.shared_library, d_r)

    # Π^sum is a proof that c, c_a and c_r satisfy the relation v + a = r
    alpha = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(alpha, MODP)
    shared_library.utils_nmod_poly_one(alpha)
    beta = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(beta, MODP)
    shared_library.utils_nmod_poly_one(beta)

    proof = ProtocolSum.prover(shared_library, commitment_scheme.scheme,
                               c, c_a, c_r, pk_C,
                               alpha, beta,
                               d, d_a, d_r)

    # e = (v, w, c, z) ← Enc_{VE} (pkV , d)
    e = __encrypt_opening(pk_V, d, c, pk_C)

    # e_r = (v_r , w_r , c_r , z_r ) ← Enc_{VE} (pk_R, d_r )
    e_r = __encrypt_opening(pk_R, d_r, c_r, pk_C)

    # The encrypted ballot is ev = (c, _v, _w, _c)
    # v, w = cipher
    encrypted_ballot = (c, e.cipher, e.c)
    # the ballot proof is Π^v = (z, c_r , e_r , Π^sum_r )
    ballot_proof = (e.z, c_r, e_r, proof)
    # with the encrypted_ballot and ballot_proof e can be reconstructed

    # Cleanup
    shared_library.nmod_poly_clear(alpha)
    shared_library.nmod_poly_clear(beta)
    shared_library.nmod_poly_clear(r)
    clear_opening(d)
    clear_opening(d_r)

    return encrypted_ballot, ballot_proof


def code(pk: tuple, ck: tuple, vvk: Commitment, ev: tuple, ballot_proof: tuple):
    """
    :param pk: public key (pk_C, pk_V, pk_R)
    :param ck: code key (pk_C, pk_V, dk_R)
    :param vvk: voter verification key (c_a)
    :param ev: encrypted ballot (c, d, cipher, _c, u)
    :param ballot_proof: ballot proof (z, c_r, e_r, lin_proof)
    """
    final_result = True

    pk_C, pk_V, pk_R = pk
    _, _, dk_R = ck
    c, cipher, _c = ev
    z, c_r, e_r, sum_proof = ballot_proof
    c_a = vvk

    alpha = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(alpha, MODP)
    shared_library.utils_nmod_poly_one(alpha)
    beta = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(beta, MODP)
    shared_library.utils_nmod_poly_one(beta)

    # It verifies Π^sum_r
    result = ProtocolSum.verifier(shared_library, *sum_proof, commitment_scheme.scheme,
                                  c, c_a, c_r, pk_C,
                                  alpha, beta)


    final_result &= result

    # recover e from (cipher{v,w}, _c, z)
    e = Veritext(
        cipher=cipher,
        c=_c,
        r=z[0],
        e=z[1],
        e_=z[2],
        u=z[3]
    )

    # and then verifies (v, w, c, z)
    t = b1_to_fmpz(shared_library, pk_C.B1, commitment_scheme.scheme, vericrypt.context_p)
    u = c1_to_fmpz(shared_library, c.c1, commitment_scheme.scheme, vericrypt.context_p)
    result = vericrypt.verify(e, t, u, pk_V)
    final_result &= result

    # and e_r
    u_r = c1_to_fmpz(shared_library, c_r.c1, commitment_scheme.scheme, vericrypt.context_p)
    result = vericrypt.verify(e_r, t, u_r, pk_R)
    final_result &= result

    # It then decrypts d_r ← e_r
    fmpz_d_r = __decrypt_opening(dk_R, e_r.cipher)

    # print_message_space(self.shared_library, d_r, self.vericrypt.context)

    d_r = fmpz_to_opening(shared_library, fmpz_d_r, commitment_scheme.scheme)
    # print_opening(self.shared_library, d_r_)

    # and recovers r from c_r and d_r
    r = commitment_scheme.message_rec(c_r, pk_C, d_r)

    return r, final_result


def count(dk, encrypted_ballots):
    from .utils import random
    pk_C, dk_V = dk

    # chooses a random permutation π on {1, 2, . . . , lt}, sets vπ(i) = v′i,
    permutation = [*range(len(encrypted_ballots))]
    random.shuffle(permutation)

    votes = (NMOD_POLY_TYPE * len(encrypted_ballots))()
    shuffled_votes = (NMOD_POLY_TYPE * len(encrypted_ballots))()
    commits = (ctypes.POINTER(Commitment) * len(encrypted_ballots))()
    randomness = (NMOD_POLY_TYPE * 2 * WIDTH * len(encrypted_ballots))()

    for i, encrypted_ballot in enumerate(encrypted_ballots):
        (c, cipher, _c) = encrypted_ballot
        fmpz_d = __decrypt_opening(dk_V, cipher)
        d = fmpz_to_opening(shared_library, fmpz_d, commitment_scheme.scheme)
        # recover v from d and c
        v = commitment_scheme.message_rec(c, pk_C, d)

        # sets v'(i) = vi
        shared_library.nmod_poly_init(votes[i], MODP)
        shared_library.nmod_poly_set(votes[i], v)

        # sets vπ(i) = vi
        shared_library.nmod_poly_init(shuffled_votes[permutation[i]], MODP)
        shared_library.nmod_poly_set(shuffled_votes[permutation[i]], v)

        # sets randomness
        for j in range(WIDTH):
            for k in range(2):
                shared_library.nmod_poly_init(randomness[i][j][k], MODP)
                shared_library.nmod_poly_set(randomness[i][j][k], d[j][k])

        commits[i] = ctypes.pointer(c)

    # and creates a proof of shuffle of known values Πc.
    proof_of_shuffle = Shuffle.prover(shared_library, commitment_scheme.scheme, commits,
                                      votes, shuffled_votes, randomness, pk_C, flint_rand,
                                      len(encrypted_ballots))

    # It outputs v1, v2,..., vlt and Πc
    return shuffled_votes, proof_of_shuffle


def verify(pk, encrypted_ballots, ballots, count_proof):
    """
    It verifies that Πc is a correct proof of shuffle of known values for
    c1, c2, ..., clt and v1, v2, ..., vlt . It outputs 1 if verification holds, otherwise
    it outputs 0
    """
    pk_C, pk_V, pk_R = pk
    y, _y, t, _t, u, d, s, rho = count_proof
    commits = (ctypes.POINTER(Commitment) * len(encrypted_ballots))()
    for i, encrypted_ballot in enumerate(encrypted_ballots):
        (c, _, _) = encrypted_ballot
        commits[i] = ctypes.pointer(c)

    return Shuffle.verifier(shared_library, y, _y, t, _t, u,
                            commitment_scheme.scheme, d, s,
                            commits, ballots, rho, pk_C, len(encrypted_ballots))


if __name__ == "__main__":
    from .serializers import serialize_encrypted_ballot, serialize_ballot_proof, deserialize_ballot_proof, \
    deserialize_encrypted_ballot, deserialize_dk, serialize_dk, deserialize_pk, serialize_pk

    pk, dk, ck = setup()
    pk = deserialize_pk(serialize_pk(pk))

    from .utils import ev_equals, pv_equals

    evs = []
    proofs = []
    for i in range(3):
        vvk, vck, f = register(pk)
        vote = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(vote, MODP)
        shared_library.nmod_poly_randtest(vote, flint_rand, DEGREE)
        encrypted_ballot, ballot_proof = cast(pk, vck, vote)

        serialized_encrypted_ballot = serialize_encrypted_ballot(encrypted_ballot)
        serialized_proof = serialize_ballot_proof(ballot_proof)

        ev = deserialize_encrypted_ballot(serialized_encrypted_ballot)
        proof = deserialize_ballot_proof(serialized_proof)
        evs.append(serialized_encrypted_ballot)
        proofs.append(serialized_proof)
        assert ev_equals(shared_library, encrypted_ballot, ev, vericrypt.context)
        assert pv_equals(shared_library, ballot_proof, proof, vericrypt.context)

    der_dk = serialize_dk(dk)
    dk = deserialize_dk(der_dk)
    shuffled_ballots, s_proof = count(dk, [deserialize_encrypted_ballot(ev) for ev in evs])

    evs_des = [deserialize_encrypted_ballot(ev) for ev in evs]

    t0 = NMOD_POLY_TYPE()
    t1 = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(t0, MODP)
    shared_library.nmod_poly_init(t1, MODP)

    shared_library.nmod_poly_rem(t0, s_proof[7], commitment_scheme.scheme[0].irred[0])
    shared_library.nmod_poly_rem(t1, s_proof[7], commitment_scheme.scheme[0].irred[1])
    for ev in evs_des:
        shared_library.nmod_poly_sub(ev[0].c2[0], ev[0].c2[0], t0)
        shared_library.nmod_poly_sub(ev[0].c2[1], ev[0].c2[1], t1)

    assert verify(pk, evs_des, shuffled_ballots, s_proof)


