from lbvs_lib.cleanup import clear_ev_and_proof
from lbvs_lib.scheme_algorithms import *
from lbvs_lib.serializers2 import *
from lbvs_lib.utils import pv_equals, ev_equals

if __name__ == '__main__':

    set_repr("str")

    pk, dk, ck = setup()
    print("Serializing pk")
    pk_s = serialize_pk(pk)
    print("Serializing dk")
    dk_s = serialize_dk(dk)
    print("Serializing ck")
    ck_s = serialize_ck(ck)

    print("Deserializing pk")
    pk2 = deserialize_pk(pk_s)
    print("Deserializing dk")
    dk2 = deserialize_dk(dk_s)
    print("Deserializing ck")
    ck2 = deserialize_ck(ck_s)

    pk_C, pk_V, pk_R = pk
    _, dk_V = dk
    _, _, dk_R = ck

    pk_C2, pk_V2, pk_R2 = pk2
    _, dk_V2 = dk2
    _, _, dk_R2 = ck2

    assert CommitmentKey.equals(pk_C, pk_C2)
    assert PublicKey.equals(pk_V, pk_V2, vericrypt.context)
    assert PublicKey.equals(pk_R, pk_R2, vericrypt.context)
    assert PrivateKey.equals(dk_V, dk_V2, vericrypt.context)
    assert PrivateKey.equals(dk_R, dk_R2, vericrypt.context)

    evs = []
    pvs = []

    for i in range(10):
        print(f"Vote {i}")
        vvk, vck, f = register(pk)
        vvk_s = serialize_vvk(vvk)
        vck_s = serialize_vck(vck)

        vvk2 = deserialize_vvk(vvk_s)
        vck2 = deserialize_vck(vck_s)

        assert Commitment.equals(vvk, vvk2)
        assert shared_library.nmod_poly_equal(vck[0], vck2[0])
        for i in range(WIDTH):
            for j in range(2):
                assert shared_library.nmod_poly_equal(vck[2][i][j], vck2[2][i][j])


        vote = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(vote, MODP)
        shared_library.nmod_poly_set_coeff_ui(vote, 1, 1)
        shared_library.nmod_poly_set_coeff_ui(vote, 4, 1)

        ev, pv = cast(pk2, vck2, vote)

        ev_s = serialize_encrypted_ballot(ev)
        pv_s = serialize_ballot_proof(pv)

        print("Deserializing ballot")
        ev2 = deserialize_encrypted_ballot(ev_s)
        print("Deserializing proof")
        pv2 = deserialize_ballot_proof(pv_s)

        assert pv_equals(shared_library, pv, pv2, vericrypt.context)
        assert ev_equals(shared_library, ev, ev2, vericrypt.context)

        print("Attempting to verify vote with deserialized objects")


        r, result = code(pk2, ck2, vvk2, ev2, pv2)

        aux = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(aux, MODP)
        shared_library.nmod_poly_add(aux, vote, vck[0])
        if not shared_library.nmod_poly_equal(r, aux):
            print("Code failed")
        if not result:
            print("Proofs failed")

        evs.append(ev2)
        pvs.append(pv2)

        shared_library.nmod_poly_clear(vote)
        clear_ev_and_proof(ev, pv)

    votes, proof = count(dk2, evs)
    proof_s = serialize_shuffle_proof(proof)

    proof2 = deserialize_shuffle_proof(proof_s)

    result = verify(pk2, evs, votes, proof)
    print("Verification result:", result)




