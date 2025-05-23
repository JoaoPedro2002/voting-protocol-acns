from pydantic import BaseModel

########################################
# Primitive types
########################################

Poly = list[list[int | str]] | str

########################################
# - Verifiable encryption
########################################

QcrtPoly = list[Poly] # 2

class PublicKey(BaseModel):
    A: list[list[QcrtPoly]] # DIM * DIM
    t: list[QcrtPoly] # DIM

class PrivateKey(BaseModel):
    s1: list[QcrtPoly] # DIM
    s2: list[QcrtPoly] # DIM

class Ciphertext(BaseModel):
    v: list[QcrtPoly] # DIM
    w: QcrtPoly

class Veritext(BaseModel):
    cipher: list[Ciphertext] # VECTOR
    c: Poly
    r: list[list[list[Poly]]] # 2 * DIM * VECTOR
    e: list[list[list[Poly]]] # 2 * DIM * VECTOR
    e_: list[list[Poly]] # 2 * VECTOR
    u: list[Poly] # VECTOR

class VeritextZ(BaseModel):
    r: list[list[list[Poly]]] # 2 * DIM * VECTOR
    e: list[list[list[Poly]]] # 2 * DIM * VECTOR
    e_: list[list[Poly]] # 2 * VECTOR
    u: list[Poly] # VECTOR

########################################
# - Commitment
########################################

PcrtPoly = list[Poly] # 2

class CommitmentKey(BaseModel):
    B1: list[list[PcrtPoly]] # WIDTH * HEIGHT
    b2: list[PcrtPoly] # WIDTH

class Commitment(BaseModel):
    c1: PcrtPoly
    c2: PcrtPoly

Opening = list[PcrtPoly]

########################################
# - ZK Proofs
########################################

class SumProof(BaseModel):
    y1: list[list[Poly]] # 2 * WIDTH
    y2: list[list[Poly]] # 2 * WIDTH
    y3: list[list[Poly]] # 2 * WIDTH
    t1: list[Poly] # 2
    t2: list[Poly] # 2
    t3: list[Poly] # 2
    u: list[Poly] # 2

class ShuffleProof(BaseModel):
    d: list[Commitment]
    y: list[Opening]
    _y: list[Opening]
    t: list[PcrtPoly]
    _t: list[PcrtPoly]
    u: list[PcrtPoly]
    s: list[Poly]
    rho: Poly

########################################
# Setup Phase
########################################

class ElectionPK(BaseModel):
    pk_C: CommitmentKey
    pk_V: PublicKey
    pk_R: PublicKey

class ElectionDK(BaseModel):
    pk_C: CommitmentKey
    dk_V: PrivateKey

class ElectionCK(BaseModel):
    pk_C: CommitmentKey
    pk_V: PublicKey
    dk_R: PrivateKey

class ElectionInstance(BaseModel):
    pk: ElectionPK | None
    auditors_urls: list[str]
    shuffle_server_url: str
    return_code_server_url: str
    ballot_box_url: str
    election_uuid: str
    ballot_box_uuid: str

class ReturnCodeSetup(BaseModel):
    instance: ElectionInstance
    ck: ElectionCK

class ShuffleServerSetup(BaseModel):
    instance: ElectionInstance
    dk: ElectionDK

class AuditorSetup(BaseModel):
    instance: ElectionInstance

class PrfKey(BaseModel):
    key: str

########################################
# Registration Phase
########################################

VoterVVK = Commitment

class VoterToRegister(BaseModel):
    url: str
    election_uuid: str
    user: str
    password: str
    voter_phone: str

class VoterRegistration(BaseModel):
    voter_uuid: str
    voter_phone_address: str | None
    vvk: VoterVVK
    election_uuid: str

class PhoneRegistration(BaseModel):
    voter_uuid: str
    rct: list[dict]

########################################
# Casting Phase
########################################
# - Voting
########################################

# class EncryptedBallot(BaseModel):
#     c: Commitment
#     cipher: list[Ciphertext]
#     e_c: Poly
#
# class BallotProof(BaseModel):
#     z: VeritextZ
#     c_r: Commitment
#     e_r: Veritext
#     proof: SumProof

class Question(BaseModel):
    ev: dict
    proof: dict

class Vote(BaseModel):
    voter_uuid: str
    election_uuid: str
    questions: list[Question]

class PlainVote(BaseModel):
    questions: list[list[int]]

class TBCastVote(BaseModel):
    voter_uuid: str
    username: str
    password: str
    vote: PlainVote

class VoteToPhone(BaseModel):
    voter_uuid: str
    vote: PlainVote

########################################
# - Code
########################################

"""
Return Code Server -> Voter
"""
class ReturnCode(BaseModel):
    code: str

class PhoneVerification(BaseModel):
    voter_uuid: str
    return_codes: list[ReturnCode]

"""
Voter -> Return Code Server -> Ballot Box
"""
class VoteConfirmation(BaseModel):
    voter_uuid: str
    confirmation: bool

########################################
# Counting Phase
########################################

"""
Ballot Box -> Shuffle Server
"""
class EncryptedBallotList(BaseModel):
    ballots: list[list[dict]]
    election_uuid: str


"""
Return Code Server & Ballot Box -> Auditor
"""
class EncryptedBallotProof(BaseModel):
    ev: dict
    proof: dict

"""
List all votes and proofs per question for a given election
"""
class EncryptedBallotProofList(BaseModel):
    election_uuid: str
    ballots_and_proofs: list[list[EncryptedBallotProof]]

"""
Shuffle Server -> Auditor
"""
class DecipheredBallots(BaseModel):
    election_uuid: str
    ballots: list[list[Poly]]
    shuffle_proof: list[dict]
