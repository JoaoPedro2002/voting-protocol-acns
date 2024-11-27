from pydantic import BaseModel

########################################
# Primitive types
########################################

Poly = str

########################################
# - Verifiable encryption
########################################

class PublicKey(BaseModel):
    A: list[list[Poly]] # DIM * DIM
    t: list[Poly] # DIM

class PrivateKey(BaseModel):
    s1: list[Poly] # DIM
    s2: list[Poly] # DIM

class Ciphertext(BaseModel):
    v: list[Poly] # DIM
    w: Poly

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

class CommitmentKey(BaseModel):
    B1: list[list[Poly]] # WIDTH * HEIGHT
    b2: list[Poly] # WIDTH

class Commitment(BaseModel):
    c1: Poly
    c2: Poly

Opening = list[Poly]

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
    t: list[Poly]
    _t: list[Poly]
    u: list[Poly]
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

class ReturnCodeSetup(BaseModel):
    pk: ElectionPK
    ck: ElectionCK

class ShuffleServerSetup(BaseModel):
    pk: ElectionPK
    dk: ElectionDK

class AuditorSetup(BaseModel):
    pk: ElectionPK

########################################
# Registration Phase
########################################

VoterVVK = Poly

class VoterRegistration(BaseModel):
    voter_id: str
    voter_email: str
    vvk: VoterVVK

########################################
# Casting Phase
########################################
# - Voting
########################################

class EncryptedBallot(BaseModel):
    c: Commitment
    cipher: list[Ciphertext]
    e_c: Poly

class BallotProof(BaseModel):
    z: VeritextZ
    c_r: Commitment
    e_r: Veritext
    proof: SumProof

class Vote(BaseModel):
    voter_id: str
    voter_email: str
    ev: EncryptedBallot
    proof: BallotProof

########################################
# - Code
########################################

"""
Return Code Server -> Voter
"""
class ReturnCode(BaseModel):
    code: str

"""
Voter -> Return Code Server -> Ballot Box
"""
class VoteConfirmation(BaseModel):
    voter_id: str
    confirmation: bool

########################################
# Counting Phase
########################################

"""
Ballot Box -> Shuffle Server
"""
class EncryptedBallotList(BaseModel):
    ballots: list[EncryptedBallot]

class EncryptedBallotProof(BaseModel):
    ev: EncryptedBallot
    proof: BallotProof

"""
Return Code Server & Ballot Box -> Auditor
"""
class EncryptedBallotProofList(BaseModel):
    ballots_and_proofs: list[EncryptedBallotProof]

"""
Shuffle Server -> Auditor
"""
class DecipheredBallots(BaseModel):
    ballots: list[Poly]
    shuffle_proof: ShuffleProof