from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import hashlib
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
from functools import wraps
import traceback
import re
from collections import Counter

# Professional logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database configuration with connection pooling
class DatabaseManager:
    _instance = None
    _client = None
    _database = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """Initialize database connection with proper configuration"""
        try:
            mongo_url = os.environ.get('MONGO_URL')
            db_name = os.environ.get('DB_NAME', 'pucrs_innovation')
            
            if not mongo_url:
                raise ValueError("MONGO_URL environment variable not found")
            
            # Connection with advanced options
            self._client = AsyncIOMotorClient(
                mongo_url,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                waitQueueTimeoutMS=5000,
                connectTimeoutMS=20000,
                socketTimeoutMS=20000,
                serverSelectionTimeoutMS=5000
            )
            
            self._database = self._client[db_name]
            
            # Test connection
            await self._client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB: {db_name}")
            
            # Initialize sample data if empty
            await self._initialize_sample_data()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @property
    def db(self):
        if self._database is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._database
    
    async def close(self):
        if self._client:
            self._client.close()
            logger.info("Database connection closed")
    
    async def _initialize_sample_data(self):
        """Initialize sample data with Brazilian names and realistic expectations"""
        try:
            # Check if users already exist
            user_count = await self._database.users.count_documents({})
            
            if user_count == 0:
                sample_users = [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "João Silva",
                        "email": "joao.silva@pucrs.br",
                        "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
                        "type": "professor",
                        "points": 50,
                        "expectations": "Busco alunos com pensamento crítico, adaptabilidade, competências digitais e habilidades de comunicação eficaz. Valorizo muito a criatividade e capacidade de trabalho em equipe.",
                        "created_at": datetime.utcnow()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Maria Oliveira",
                        "email": "maria.oliveira@pucrs.br",
                        "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
                        "type": "aluno",
                        "points": 85,
                        "expectations": "Procuro uma empresa com ambiente inclusivo, oportunidades de crescimento profissional, tecnologia moderna, horário flexível e que valorize propósito e responsabilidade social.",
                        "created_at": datetime.utcnow()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Pedro Santos",
                        "email": "pedro.santos@techcorp.com.br",
                        "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
                        "type": "empresa",
                        "points": 30,
                        "expectations": "Nossa empresa busca recém-formados com competências digitais, inteligência emocional, capacidade de inovação e forte ética profissional. Valorizamos diversidade e aprendizado contínuo.",
                        "created_at": datetime.utcnow()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Ana Costa",
                        "email": "ana.costa@pucrs.br",
                        "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
                        "type": "aluno",
                        "points": 120,
                        "expectations": "Busco empresas que ofereçam planos de saúde, cultura colaborativa, feedback regular, possibilidade de trabalho remoto e oportunidades de desenvolvimento pessoal e profissional.",
                        "created_at": datetime.utcnow()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Carlos Fernandes",
                        "email": "carlos.fernandes@pucrs.br",
                        "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
                        "type": "professor",
                        "points": 75,
                        "expectations": "Procuro estudantes com pensamento crítico, habilidades de resolução de problemas, consciência cultural, capacidade de comunicação e comprometimento com ética e responsabilidade.",
                        "created_at": datetime.utcnow()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Augusto Ribeiro",
                        "email": "augusto.ribeiro@inovacorp.com.br",
                        "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
                        "type": "empresa",
                        "points": 95,
                        "expectations": "Buscamos talentos com adaptabilidade, trabalho em equipe, criatividade, competências tecnológicas e forte capacidade de comunicação. Valorizamos diversidade e inovação.",
                        "created_at": datetime.utcnow()
                    }
                ]
                
                await self._database.users.insert_many(sample_users)
                logger.info(f"Inserted {len(sample_users)} sample users with expectations")
                
                # Sample challenges
                sample_challenges = [
                    {
                        "id": str(uuid.uuid4()),
                        "title": "Sistema de Gestão Sustentável",
                        "description": "Desenvolver uma plataforma para otimizar o consumo de energia em edifícios corporativos, utilizando sensores IoT e algoritmos de machine learning para reduzir custos e impacto ambiental.",
                        "creator_id": sample_users[0]["id"],
                        "creator_name": sample_users[0]["name"],
                        "deadline": "2025-06-15",
                        "reward": "R$ 10.000 + Estágio na empresa",
                        "active": True,
                        "created_at": datetime.utcnow()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "title": "App de Mobilidade Urbana Inteligente",
                        "description": "Criar um aplicativo que integre dados de transporte público, trânsito e rotas de bicicleta para otimizar deslocamentos urbanos, incluindo funcionalidades de gamificação para incentivar mobilidade sustentável.",
                        "creator_id": sample_users[5]["id"],
                        "creator_name": sample_users[5]["name"],
                        "deadline": "2025-07-20",
                        "reward": "R$ 15.000 + Mentoria técnica",
                        "active": True,
                        "created_at": datetime.utcnow()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "title": "Plataforma de Educação Adaptativa com IA",
                        "description": "Desenvolver uma solução educacional que utiliza inteligência artificial para personalizar o aprendizado de estudantes, adaptando conteúdo e metodologia conforme o perfil e progresso individual.",
                        "creator_id": sample_users[4]["id"],
                        "creator_name": sample_users[4]["name"],
                        "deadline": "2025-08-10",
                        "reward": "R$ 8.000 + Publicação em revista científica",
                        "active": True,
                        "created_at": datetime.utcnow()
                    }
                ]
                
                await self._database.challenges.insert_many(sample_challenges)
                logger.info(f"Inserted {len(sample_challenges)} sample challenges")
                
        except Exception as e:
            logger.error(f"Failed to initialize sample data: {e}")
            # Don't raise the exception to avoid breaking the startup

# Initialize database manager
db_manager = DatabaseManager()

# FastAPI app configuration
app = FastAPI(
    title="PUC-RS Innovation Platform",
    description="Advanced platform connecting business challenges with academic solutions",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# API router with enhanced configuration
api_router = APIRouter(
    prefix="/api",
    tags=["PUC-RS Innovation API"]
)

# Security configuration
security = HTTPBearer(auto_error=False)

# Enhanced Pydantic models with validation
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="User full name")
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$', description="Valid email address")
    type: str = Field(..., pattern=r'^(aluno|professor|empresa)$', description="User type")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip().title()
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="User password")
    shareExpectations: Optional[bool] = False
    expectations: Optional[str] = Field(None, max_length=1000, description="User expectations")

class UserLogin(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    password_hash: str
    points: int = 0
    expectations: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserResponse(UserBase):
    id: str
    points: int
    expectations: Optional[str] = None

class ChallengeBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=200, description="Challenge title")
    description: str = Field(..., min_length=10, max_length=2000, description="Challenge description")
    deadline: Optional[str] = Field(None, description="Challenge deadline (YYYY-MM-DD)")
    reward: Optional[str] = Field(None, max_length=200, description="Challenge reward")
    
    @validator('title')
    def validate_title(cls, v):
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        return v.strip()

class ChallengeCreate(ChallengeBase):
    pass

class Challenge(ChallengeBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    creator_name: str
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SolutionBase(BaseModel):
    description: str = Field(..., min_length=10, max_length=2000, description="Solution description")
    
    @validator('description')
    def validate_description(cls, v):
        return v.strip()

class SolutionCreate(SolutionBase):
    challenge_id: str = Field(..., description="Challenge ID")

class Solution(SolutionBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    challenge_id: str
    author_id: str
    author_name: str
    votes: int = 0
    submission_date: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Vote(BaseModel):
    user_id: str
    solution_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Enhanced error handling decorator
def handle_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, 
                detail=f"Internal server error: {str(e)}"
            )
    return wrapper

# Enhanced utility functions
class SecurityUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return SecurityUtils.hash_password(password) == hashed

class AuthService:
    @staticmethod
    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
        """Get current authenticated user"""
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        try:
            user_id = credentials.credentials
            user_doc = await db_manager.db.users.find_one({"id": user_id})
            
            if not user_doc:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
            
            return UserResponse(**user_doc)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    @staticmethod
    async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[UserResponse]:
        """Get current user if authenticated, None otherwise"""
        try:
            if not credentials:
                return None
            return await AuthService.get_current_user(credentials)
        except HTTPException:
            return None

# Matching Analysis Service
class MatchingService:
    
    # Predefined keywords for analysis
    COMPANY_KEYWORDS = {
        'adaptabilidade': ['adaptabilidade', 'adaptação', 'flexibilidade', 'mudança'],
        'pensamento_critico': ['pensamento crítico', 'crítico', 'análise', 'analítico'],
        'competencias_digitais': ['digital', 'tecnologia', 'programação', 'tech', 'dados'],
        'trabalho_equipe': ['equipe', 'colaboração', 'time', 'colaborativo'],
        'comunicacao': ['comunicação', 'comunicar', 'apresentação'],
        'criatividade': ['criatividade', 'criativo', 'inovação', 'inovador'],
        'inteligencia_emocional': ['emocional', 'relacionamento', 'interpessoal'],
        'diversidade': ['diversidade', 'inclusão', 'cultural'],
        'aprendizado': ['aprendizado', 'desenvolvimento', 'crescimento'],
        'etica': ['ética', 'responsabilidade', 'valores']
    }
    
    STUDENT_KEYWORDS = {
        'beneficios': ['benefícios', 'saúde', 'plano', 'vale'],
        'flexibilidade': ['flexível', 'remoto', 'horário', 'home office'],
        'crescimento': ['crescimento', 'desenvolvimento', 'carreira'],
        'ambiente_inclusivo': ['inclusivo', 'diverso', 'acolhedor'],
        'tecnologia': ['tecnologia', 'inovação', 'moderno'],
        'proposito': ['propósito', 'social', 'sustentabilidade'],
        'feedback': ['feedback', 'reconhecimento', 'valorização'],
        'cultura': ['cultura', 'ambiente', 'clima'],
        'colaboracao': ['colaborativo', 'equipe', 'participativo'],
        'estabilidade': ['estabilidade', 'segurança', 'permanência']
    }
    
    @staticmethod
    def analyze_text(text: str, keywords_dict: dict) -> dict:
        """Analyze text and return keyword matches with percentages"""
        if not text:
            return {}
        
        text_lower = text.lower()
        results = {}
        total_matches = 0
        
        for category, keywords in keywords_dict.items():
            matches = 0
            for keyword in keywords:
                if keyword in text_lower:
                    matches += 1
            
            if matches > 0:
                results[category] = min(matches * 20, 100)  # Cap at 100%
                total_matches += matches
        
        return results
    
    @staticmethod
    async def generate_matching_analysis() -> dict:
        """Generate comprehensive matching analysis"""
        try:
            # Get all users with expectations
            users_cursor = db_manager.db.users.find({"expectations": {"$exists": True, "$ne": None}})
            users = await users_cursor.to_list(length=1000)
            
            company_expectations = []
            student_expectations = []
            
            # Separate by type
            for user in users:
                if user.get('expectations'):
                    if user['type'] == 'empresa':
                        company_expectations.append(user['expectations'])
                    elif user['type'] == 'aluno':
                        student_expectations.append(user['expectations'])
            
            # Analyze company expectations
            company_analysis = {}
            for text in company_expectations:
                analysis = MatchingService.analyze_text(text, MatchingService.COMPANY_KEYWORDS)
                for category, score in analysis.items():
                    if category not in company_analysis:
                        company_analysis[category] = []
                    company_analysis[category].append(score)
            
            # Analyze student expectations
            student_analysis = {}
            for text in student_expectations:
                analysis = MatchingService.analyze_text(text, MatchingService.STUDENT_KEYWORDS)
                for category, score in analysis.items():
                    if category not in student_analysis:
                        student_analysis[category] = []
                    student_analysis[category].append(score)
            
            # Calculate averages and format results
            company_results = []
            for category, scores in company_analysis.items():
                avg_score = sum(scores) / len(scores) if scores else 0
                formatted_category = category.replace('_', ' ').title()
                company_results.append({
                    'expectation': formatted_category,
                    'percentage': round(avg_score, 1)
                })
            
            student_results = []
            for category, scores in student_analysis.items():
                avg_score = sum(scores) / len(scores) if scores else 0
                formatted_category = category.replace('_', ' ').title()
                student_results.append({
                    'expectation': formatted_category,
                    'percentage': round(avg_score, 1)
                })
            
            # Sort by percentage
            company_results.sort(key=lambda x: x['percentage'], reverse=True)
            student_results.sort(key=lambda x: x['percentage'], reverse=True)
            
            # Calculate overall compatibility
            total_compatibility = 0
            matches_count = 0
            
            if company_results and student_results:
                total_compatibility = (sum(r['percentage'] for r in company_results[:5]) + 
                                    sum(r['percentage'] for r in student_results[:5])) / 10
                matches_count = min(len(company_results), len(student_results))
            
            # Generate top matches
            top_matches = []
            if matches_count > 0:
                for i in range(min(3, matches_count)):
                    match_score = (company_results[i]['percentage'] + 
                                 (student_results[i]['percentage'] if i < len(student_results) else 0)) / 2
                    
                    top_matches.append({
                        'score': round(match_score, 1),
                        'commonExpectations': f"{company_results[i]['expectation']} & Ambiente Profissional"
                    })
            
            return {
                'totalMatches': round(total_compatibility, 1),
                'companies': len(company_expectations),
                'students': len(student_expectations),
                'companyExpectations': company_results[:8],
                'studentExpectations': student_results[:8],
                'topMatches': top_matches
            }
            
        except Exception as e:
            logger.error(f"Error generating matching analysis: {e}")
            return {
                'totalMatches': 0,
                'companies': 0,
                'students': 0,
                'companyExpectations': [],
                'studentExpectations': [],
                'topMatches': []
            }

# API Endpoints with enhanced functionality

@api_router.post("/register", response_model=UserResponse, summary="Register new user")
@handle_exceptions
async def register_user(user_data: UserCreate) -> UserResponse:
    """Register a new user with enhanced validation and expectations"""
    
    # Check if email already exists
    existing_user = await db_manager.db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email address already registered. Please use a different email."
        )
    
    # Create new user
    user_dict = user_data.dict()
    user_dict['password_hash'] = SecurityUtils.hash_password(user_data.password)
    del user_dict['password']
    del user_dict['shareExpectations']  # Remove the flag, keep only expectations
    
    # Only keep expectations if they shared them
    if not user_data.shareExpectations or not user_data.expectations:
        user_dict['expectations'] = None
    
    user_obj = User(**user_dict)
    
    # Insert to database
    await db_manager.db.users.insert_one(user_obj.dict())
    
    logger.info(f"New user registered: {user_obj.name} ({user_obj.type})")
    
    return UserResponse(**user_obj.dict())

@api_router.post("/login", summary="User authentication")
@handle_exceptions
async def login_user(login_data: UserLogin) -> Dict[str, Any]:
    """Authenticate user and return access token"""
    
    user_doc = await db_manager.db.users.find_one({"email": login_data.email})
    
    if not user_doc or not SecurityUtils.verify_password(login_data.password, user_doc['password_hash']):
        raise HTTPException(
            status_code=401, 
            detail="Invalid email or password. Please check your credentials."
        )
    
    logger.info(f"User logged in: {user_doc['name']} ({user_doc['email']})")
    
    # Return user ID as simple token (for MVP - in production use JWT)
    return {
        "token": user_doc['id'],
        "user": UserResponse(**user_doc),
        "message": "Login successful"
    }

@api_router.get("/profile", response_model=UserResponse, summary="Get user profile")
@handle_exceptions
async def get_user_profile(current_user: UserResponse = Depends(AuthService.get_current_user)) -> UserResponse:
    """Get current user profile information"""
    return current_user

@api_router.post("/challenges", response_model=Challenge, summary="Create new challenge")
@handle_exceptions
async def create_challenge(
    challenge_data: ChallengeCreate,
    current_user: UserResponse = Depends(AuthService.get_current_user)
) -> Challenge:
    """Create a new challenge (professors and companies only)"""
    
    # Authorization check
    if current_user.type not in ['professor', 'empresa']:
        raise HTTPException(
            status_code=403,
            detail="Only professors and companies can create challenges"
        )
    
    # Create challenge
    challenge_dict = challenge_data.dict()
    challenge_dict.update({
        'creator_id': current_user.id,
        'creator_name': current_user.name
    })
    
    challenge_obj = Challenge(**challenge_dict)
    
    # Insert to database
    await db_manager.db.challenges.insert_one(challenge_obj.dict())
    
    logger.info(f"New challenge created: '{challenge_obj.title}' by {current_user.name}")
    
    return challenge_obj

@api_router.get("/challenges", response_model=List[Challenge], summary="List all challenges")
@handle_exceptions
async def list_challenges() -> List[Challenge]:
    """Get all active challenges"""
    
    challenges_cursor = db_manager.db.challenges.find({"active": True}).sort("created_at", -1).limit(100)
    challenges = await challenges_cursor.to_list(length=100)
    
    return [Challenge(**challenge) for challenge in challenges]

@api_router.get("/challenges/{challenge_id}", response_model=Challenge, summary="Get challenge by ID")
@handle_exceptions
async def get_challenge_by_id(challenge_id: str) -> Challenge:
    """Get specific challenge by ID"""
    
    challenge_doc = await db_manager.db.challenges.find_one({"id": challenge_id})
    
    if not challenge_doc:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    return Challenge(**challenge_doc)

@api_router.post("/solutions", response_model=Solution, summary="Submit solution")
@handle_exceptions
async def submit_solution(
    solution_data: SolutionCreate,
    current_user: UserResponse = Depends(AuthService.get_current_user)
) -> Solution:
    """Submit a solution to a challenge"""
    
    # Verify challenge exists
    challenge_doc = await db_manager.db.challenges.find_one({"id": solution_data.challenge_id})
    if not challenge_doc:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    # Check if user already submitted a solution for this challenge
    existing_solution = await db_manager.db.solutions.find_one({
        "challenge_id": solution_data.challenge_id,
        "author_id": current_user.id
    })
    
    if existing_solution:
        raise HTTPException(
            status_code=400,
            detail="You have already submitted a solution for this challenge"
        )
    
    # Create solution
    solution_dict = solution_data.dict()
    solution_dict.update({
        'author_id': current_user.id,
        'author_name': current_user.name
    })
    
    solution_obj = Solution(**solution_dict)
    
    # Insert to database
    await db_manager.db.solutions.insert_one(solution_obj.dict())
    
    logger.info(f"New solution submitted by {current_user.name} for challenge: {challenge_doc['title']}")
    
    return solution_obj

@api_router.get("/challenges/{challenge_id}/solutions", response_model=List[Solution], summary="Get solutions for challenge")
@handle_exceptions
async def get_challenge_solutions(challenge_id: str) -> List[Solution]:
    """Get all solutions for a specific challenge, ordered by votes"""
    
    solutions_cursor = db_manager.db.solutions.find({"challenge_id": challenge_id}).sort("votes", -1).limit(100)
    solutions = await solutions_cursor.to_list(length=100)
    
    return [Solution(**solution) for solution in solutions]

@api_router.get("/solutions", response_model=List[Solution], summary="Get all solutions")
@handle_exceptions
async def get_all_solutions() -> List[Solution]:
    """Get all solutions ordered by votes"""
    
    solutions_cursor = db_manager.db.solutions.find().sort("votes", -1).limit(100)
    solutions = await solutions_cursor.to_list(length=100)
    
    return [Solution(**solution) for solution in solutions]

@api_router.post("/solutions/{solution_id}/vote", summary="Vote on solution")
@handle_exceptions
async def vote_on_solution(
    solution_id: str,
    current_user: UserResponse = Depends(AuthService.get_current_user)
) -> Dict[str, str]:
    """Vote on a solution with enhanced validation"""
    
    # Verify solution exists
    solution_doc = await db_manager.db.solutions.find_one({"id": solution_id})
    if not solution_doc:
        raise HTTPException(status_code=404, detail="Solution not found")
    
    # Prevent self-voting
    if solution_doc['author_id'] == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot vote on your own solution"
        )
    
    # Check for duplicate votes
    existing_vote = await db_manager.db.votes.find_one({
        "user_id": current_user.id,
        "solution_id": solution_id
    })
    
    if existing_vote:
        raise HTTPException(
            status_code=400,
            detail="You have already voted on this solution"
        )
    
    # Add vote
    vote_obj = Vote(user_id=current_user.id, solution_id=solution_id)
    await db_manager.db.votes.insert_one(vote_obj.dict())
    
    # Update solution vote count
    await db_manager.db.solutions.update_one(
        {"id": solution_id},
        {"$inc": {"votes": 1}}
    )
    
    # Award points to solution author (10 points per vote)
    await db_manager.db.users.update_one(
        {"id": solution_doc['author_id']},
        {"$inc": {"points": 10}}
    )
    
    logger.info(f"Vote cast by {current_user.name} on solution by {solution_doc['author_name']}")
    
    return {"message": "Vote successfully registered. Author awarded 10 points!"}

@api_router.get("/solutions/{solution_id}/votes", summary="Get solution vote details")
@handle_exceptions
async def get_solution_votes(solution_id: str) -> Dict[str, Any]:
    """Get vote details for a specific solution"""
    
    votes_cursor = db_manager.db.votes.find({"solution_id": solution_id})
    votes = await votes_cursor.to_list(length=1000)
    
    return {
        "solution_id": solution_id,
        "total_votes": len(votes),
        "votes": [Vote(**vote) for vote in votes]
    }

@api_router.get("/leaderboard", response_model=List[UserResponse], summary="Get user leaderboard")
@handle_exceptions
async def get_leaderboard() -> List[UserResponse]:
    """Get top users ranked by points"""
    
    users_cursor = db_manager.db.users.find().sort("points", -1).limit(20)
    users = await users_cursor.to_list(length=20)
    
    return [UserResponse(**user) for user in users]

@api_router.get("/stats", summary="Get platform statistics")
@handle_exceptions
async def get_platform_stats() -> Dict[str, int]:
    """Get comprehensive platform statistics"""
    
    # Run all counts concurrently for better performance
    stats = await asyncio.gather(
        db_manager.db.challenges.count_documents({"active": True}),
        db_manager.db.solutions.count_documents({}),
        db_manager.db.users.count_documents({}),
        db_manager.db.votes.count_documents({})
    )
    
    return {
        "total_challenges": stats[0],
        "total_solutions": stats[1],
        "total_users": stats[2],
        "total_votes": stats[3]
    }

@api_router.get("/matching-analysis", summary="Get matching analysis")
@handle_exceptions
async def get_matching_analysis() -> Dict[str, Any]:
    """Get comprehensive matching analysis between companies and students"""
    
    return await MatchingService.generate_matching_analysis()

# User management endpoints (for admin purposes)
@api_router.get("/users", response_model=List[UserResponse], summary="List all users")
@handle_exceptions
async def list_all_users() -> List[UserResponse]:
    """Get all users (for administrative purposes)"""
    
    users_cursor = db_manager.db.users.find().sort("created_at", -1).limit(100)
    users = await users_cursor.to_list(length=100)
    
    return [UserResponse(**user) for user in users]

@api_router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID")
@handle_exceptions
async def get_user_by_id(user_id: str) -> UserResponse:
    """Get specific user by ID"""
    
    user_doc = await db_manager.db.users.find_one({"id": user_id})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(**user_doc)

# Health check endpoint
@api_router.get("/health", summary="Health check")
async def health_check() -> Dict[str, str]:
    """API health check endpoint"""
    try:
        # Test database connection
        await db_manager.db.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Include router in main app
app.include_router(api_router)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # In production, specify exact origins
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Application event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        await db_manager.initialize()
        logger.info("🚀 PUC-RS Innovation Platform started successfully!")
        logger.info("📊 Access API documentation at: /api/docs")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown"""
    try:
        await db_manager.close()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Root endpoint
@app.get("/", summary="API Root")
async def root():
    """API root endpoint with information"""
    return {
        "message": "🎓 PUC-RS Innovation Platform API",
        "version": "2.0.0",
        "description": "Connecting business challenges with academic innovation",
        "docs": "/api/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )