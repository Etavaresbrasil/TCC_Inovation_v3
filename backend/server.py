from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, date
import hashlib
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Define Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    password_hash: str
    type: str  # 'aluno', 'professor', 'empresa'
    points: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    type: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    type: str
    points: int

class Challenge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    creator_id: str
    creator_name: str
    deadline: Optional[date] = None
    reward: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChallengeCreate(BaseModel):
    title: str
    description: str
    deadline: Optional[date] = None
    reward: Optional[str] = None

class Solution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    challenge_id: str
    author_id: str
    author_name: str
    description: str
    votes: int = 0
    submission_date: datetime = Field(default_factory=datetime.utcnow)

class SolutionCreate(BaseModel):
    challenge_id: str
    description: str

class Vote(BaseModel):
    user_id: str
    solution_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        user_id = credentials.credentials
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return UserResponse(**user)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth routes
@api_router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user_dict = user_data.dict()
    user_dict['password_hash'] = hash_password(user_data.password)
    del user_dict['password']
    
    user_obj = User(**user_dict)
    await db.users.insert_one(user_obj.dict())
    
    return UserResponse(**user_obj.dict())

@api_router.post("/login")
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Return user ID as token (simple implementation)
    return {"token": user['id'], "user": UserResponse(**user)}

@api_router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# Challenge routes
@api_router.post("/challenges", response_model=Challenge)
async def create_challenge(challenge_data: ChallengeCreate, current_user: UserResponse = Depends(get_current_user)):
    challenge_dict = challenge_data.dict()
    challenge_dict['creator_id'] = current_user.id
    challenge_dict['creator_name'] = current_user.name
    
    challenge_obj = Challenge(**challenge_dict)
    await db.challenges.insert_one(challenge_obj.dict())
    
    return challenge_obj

@api_router.get("/challenges", response_model=List[Challenge])
async def get_challenges():
    challenges = await db.challenges.find({"active": True}).sort("created_at", -1).to_list(100)
    return [Challenge(**challenge) for challenge in challenges]

@api_router.get("/challenges/{challenge_id}", response_model=Challenge)
async def get_challenge(challenge_id: str):
    challenge = await db.challenges.find_one({"id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return Challenge(**challenge)

# Solution routes
@api_router.post("/solutions", response_model=Solution)
async def create_solution(solution_data: SolutionCreate, current_user: UserResponse = Depends(get_current_user)):
    # Check if challenge exists
    challenge = await db.challenges.find_one({"id": solution_data.challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    solution_dict = solution_data.dict()
    solution_dict['author_id'] = current_user.id
    solution_dict['author_name'] = current_user.name
    
    solution_obj = Solution(**solution_dict)
    await db.solutions.insert_one(solution_obj.dict())
    
    return solution_obj

@api_router.get("/challenges/{challenge_id}/solutions", response_model=List[Solution])
async def get_solutions_by_challenge(challenge_id: str):
    solutions = await db.solutions.find({"challenge_id": challenge_id}).sort("votes", -1).to_list(100)
    return [Solution(**solution) for solution in solutions]

@api_router.get("/solutions", response_model=List[Solution])
async def get_all_solutions():
    solutions = await db.solutions.find().sort("votes", -1).to_list(100)
    return [Solution(**solution) for solution in solutions]

# Voting routes
@api_router.post("/solutions/{solution_id}/vote")
async def vote_solution(solution_id: str, current_user: UserResponse = Depends(get_current_user)):
    # Check if solution exists
    solution = await db.solutions.find_one({"id": solution_id})
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    
    # Check if user already voted
    existing_vote = await db.votes.find_one({"user_id": current_user.id, "solution_id": solution_id})
    if existing_vote:
        raise HTTPException(status_code=400, detail="You have already voted for this solution")
    
    # Add vote
    vote_obj = Vote(user_id=current_user.id, solution_id=solution_id)
    await db.votes.insert_one(vote_obj.dict())
    
    # Update solution vote count
    await db.solutions.update_one(
        {"id": solution_id},
        {"$inc": {"votes": 1}}
    )
    
    # Add points to solution author
    await db.users.update_one(
        {"id": solution['author_id']},
        {"$inc": {"points": 10}}
    )
    
    return {"message": "Vote registered successfully"}

@api_router.get("/solutions/{solution_id}/votes")
async def get_solution_votes(solution_id: str):
    votes = await db.votes.find({"solution_id": solution_id}).to_list(100)
    return {"count": len(votes), "votes": votes}

# Leaderboard route
@api_router.get("/leaderboard", response_model=List[UserResponse])
async def get_leaderboard():
    users = await db.users.find().sort("points", -1).limit(10).to_list(10)
    return [UserResponse(**user) for user in users]

# Stats route
@api_router.get("/stats")
async def get_stats():
    total_challenges = await db.challenges.count_documents({"active": True})
    total_solutions = await db.solutions.count_documents({})
    total_users = await db.users.count_documents({})
    total_votes = await db.votes.count_documents({})
    
    return {
        "total_challenges": total_challenges,
        "total_solutions": total_solutions,
        "total_users": total_users,
        "total_votes": total_votes
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()