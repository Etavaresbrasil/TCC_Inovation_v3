#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for PUC-RS Innovation Platform
Tests all endpoints with different user types and scenarios
"""

import requests
import sys
import json
from datetime import datetime, date
import uuid

class PlatformAPITester:
    def __init__(self, base_url="https://8a30ab99-f2ac-4a7c-a857-b3e6663b2eed.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.challenges = []  # Store created challenges
        self.solutions = []   # Store created solutions
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🚀 Starting API tests for: {self.api_url}")

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            
            success = response.status_code == expected_status
            result_data = {}
            
            try:
                result_data = response.json()
            except:
                result_data = {"raw_response": response.text}
                
            return success, response.status_code, result_data
            
        except Exception as e:
            return False, 0, {"error": str(e)}

    def test_stats_endpoint(self):
        """Test stats endpoint (should work without auth)"""
        success, status, data = self.make_request('GET', 'stats')
        expected_keys = ['total_challenges', 'total_solutions', 'total_users', 'total_votes']
        
        if success and all(key in data for key in expected_keys):
            return self.log_test("Stats Endpoint", True, f"- Got stats: {data}")
        else:
            return self.log_test("Stats Endpoint", False, f"- Status: {status}, Data: {data}")

    def test_user_registration(self, user_type, name_suffix=""):
        """Test user registration for different types"""
        timestamp = datetime.now().strftime("%H%M%S")
        user_data = {
            "name": f"Test {user_type.title()} {name_suffix}{timestamp}",
            "email": f"test_{user_type}_{timestamp}@test.com",
            "password": "TestPass123!",
            "type": user_type
        }
        
        success, status, response_data = self.make_request('POST', 'register', user_data, expected_status=200)
        
        if success:
            self.users[user_type] = {**user_data, **response_data}
            return self.log_test(f"Register {user_type.title()}", True, f"- ID: {response_data.get('id', 'N/A')}")
        else:
            return self.log_test(f"Register {user_type.title()}", False, f"- Status: {status}, Error: {response_data}")

    def test_user_registration_with_expectations(self, user_type):
        """Test NEW user registration with expectations feature"""
        timestamp = datetime.now().strftime("%H%M%S")
        
        # Define expectations based on user type
        expectations_map = {
            "empresa": "Buscamos profissionais com pensamento crítico, adaptabilidade, competências digitais e trabalho em equipe. Valorizamos criatividade e inovação.",
            "aluno": "Procuro empresa com ambiente inclusivo, oportunidades de crescimento, tecnologia moderna e horário flexível. Valorizo propósito e responsabilidade social.",
            "professor": "Busco estudantes com pensamento crítico, habilidades de resolução de problemas e comprometimento com ética e responsabilidade."
        }
        
        user_data = {
            "name": f"Test {user_type.title()} Expectations {timestamp}",
            "email": f"test_{user_type}_exp_{timestamp}@test.com",
            "password": "TestPass123!",
            "type": user_type,
            "shareExpectations": True,
            "expectations": expectations_map.get(user_type, "Test expectations")
        }
        
        success, status, response_data = self.make_request('POST', 'register', user_data, expected_status=200)
        
        if success and response_data.get('expectations') is not None:
            return self.log_test(f"Register {user_type.title()} with Expectations", True, 
                               f"- ID: {response_data.get('id', 'N/A')}, Has expectations: Yes")
        else:
            return self.log_test(f"Register {user_type.title()} with Expectations", False, 
                               f"- Status: {status}, Has expectations: {response_data.get('expectations') is not None if success else 'Failed'}")

    def test_user_login(self, user_type):
        """Test user login"""
        if user_type not in self.users:
            return self.log_test(f"Login {user_type.title()}", False, "- User not registered")
            
        login_data = {
            "email": self.users[user_type]["email"],
            "password": self.users[user_type]["password"]
        }
        
        success, status, response_data = self.make_request('POST', 'login', login_data, expected_status=200)
        
        if success and 'token' in response_data:
            self.tokens[user_type] = response_data['token']
            return self.log_test(f"Login {user_type.title()}", True, f"- Token received")
        else:
            return self.log_test(f"Login {user_type.title()}", False, f"- Status: {status}, Data: {response_data}")

    def test_profile_access(self, user_type):
        """Test profile access with token"""
        if user_type not in self.tokens:
            return self.log_test(f"Profile {user_type.title()}", False, "- No token available")
            
        success, status, response_data = self.make_request('GET', 'profile', token=self.tokens[user_type])
        
        if success and 'id' in response_data:
            return self.log_test(f"Profile {user_type.title()}", True, f"- Name: {response_data.get('name', 'N/A')}")
        else:
            return self.log_test(f"Profile {user_type.title()}", False, f"- Status: {status}, Data: {response_data}")

    def test_create_challenge(self, creator_type):
        """Test challenge creation (only professors and companies should succeed)"""
        if creator_type not in self.tokens:
            return self.log_test(f"Create Challenge ({creator_type})", False, "- No token available")
            
        challenge_data = {
            "title": f"Test Challenge by {creator_type}",
            "description": f"This is a test challenge created by a {creator_type} user for testing purposes.",
            "deadline": str(date.today()),
            "reward": "Test Reward"
        }
        
        expected_status = 200 if creator_type in ['professor', 'empresa'] else 403
        success, status, response_data = self.make_request(
            'POST', 'challenges', challenge_data, 
            token=self.tokens[creator_type], 
            expected_status=expected_status
        )
        
        if success:
            if creator_type in ['professor', 'empresa']:
                self.challenges.append(response_data)
                return self.log_test(f"Create Challenge ({creator_type})", True, f"- ID: {response_data.get('id', 'N/A')}")
            else:
                return self.log_test(f"Create Challenge ({creator_type})", True, "- Correctly rejected")
        else:
            return self.log_test(f"Create Challenge ({creator_type})", False, f"- Status: {status}, Data: {response_data}")

    def test_list_challenges(self):
        """Test listing challenges (should work without auth)"""
        success, status, response_data = self.make_request('GET', 'challenges')
        
        if success and isinstance(response_data, list):
            return self.log_test("List Challenges", True, f"- Found {len(response_data)} challenges")
        else:
            return self.log_test("List Challenges", False, f"- Status: {status}, Data: {response_data}")

    def test_create_solution(self, user_type):
        """Test solution creation"""
        if user_type not in self.tokens:
            return self.log_test(f"Create Solution ({user_type})", False, "- No token available")
            
        if not self.challenges:
            return self.log_test(f"Create Solution ({user_type})", False, "- No challenges available")
            
        solution_data = {
            "challenge_id": self.challenges[0]['id'],
            "description": f"Test solution from {user_type} user. This is a comprehensive solution to the challenge."
        }
        
        success, status, response_data = self.make_request(
            'POST', 'solutions', solution_data, 
            token=self.tokens[user_type]
        )
        
        if success:
            self.solutions.append(response_data)
            return self.log_test(f"Create Solution ({user_type})", True, f"- ID: {response_data.get('id', 'N/A')}")
        else:
            return self.log_test(f"Create Solution ({user_type})", False, f"- Status: {status}, Data: {response_data}")

    def test_list_solutions(self):
        """Test listing solutions for a challenge"""
        if not self.challenges:
            return self.log_test("List Solutions", False, "- No challenges available")
            
        challenge_id = self.challenges[0]['id']
        success, status, response_data = self.make_request('GET', f'challenges/{challenge_id}/solutions')
        
        if success and isinstance(response_data, list):
            return self.log_test("List Solutions", True, f"- Found {len(response_data)} solutions")
        else:
            return self.log_test("List Solutions", False, f"- Status: {status}, Data: {response_data}")

    def test_voting(self, voter_type):
        """Test voting on solutions"""
        if voter_type not in self.tokens:
            return self.log_test(f"Vote ({voter_type})", False, "- No token available")
            
        if not self.solutions:
            return self.log_test(f"Vote ({voter_type})", False, "- No solutions available")
            
        # Find a solution not created by the voter
        target_solution = None
        for solution in self.solutions:
            if solution.get('author_id') != self.users.get(voter_type, {}).get('id'):
                target_solution = solution
                break
                
        if not target_solution:
            return self.log_test(f"Vote ({voter_type})", False, "- No suitable solution to vote on")
            
        success, status, response_data = self.make_request(
            'POST', f'solutions/{target_solution["id"]}/vote', 
            token=self.tokens[voter_type]
        )
        
        if success:
            return self.log_test(f"Vote ({voter_type})", True, f"- Voted on solution {target_solution['id'][:8]}...")
        else:
            return self.log_test(f"Vote ({voter_type})", False, f"- Status: {status}, Data: {response_data}")

    def test_duplicate_vote(self, voter_type):
        """Test that duplicate voting is prevented"""
        if voter_type not in self.tokens or not self.solutions:
            return self.log_test(f"Duplicate Vote ({voter_type})", False, "- Prerequisites not met")
            
        target_solution = self.solutions[0]
        success, status, response_data = self.make_request(
            'POST', f'solutions/{target_solution["id"]}/vote', 
            token=self.tokens[voter_type],
            expected_status=400  # Should fail with 400
        )
        
        if success:  # Success means it correctly rejected the duplicate vote
            return self.log_test(f"Duplicate Vote Prevention ({voter_type})", True, "- Correctly prevented duplicate vote")
        else:
            return self.log_test(f"Duplicate Vote Prevention ({voter_type})", False, f"- Status: {status}, Data: {response_data}")

    def test_leaderboard(self):
        """Test leaderboard endpoint"""
        success, status, response_data = self.make_request('GET', 'leaderboard')
        
        if success and isinstance(response_data, list):
            return self.log_test("Leaderboard", True, f"- Found {len(response_data)} users in leaderboard")
        else:
            return self.log_test("Leaderboard", False, f"- Status: {status}, Data: {response_data}")

    def test_matching_analysis(self):
        """Test NEW matching analysis endpoint"""
        success, status, response_data = self.make_request('GET', 'matching-analysis')
        
        # Check if response has expected structure
        expected_keys = ['totalMatches', 'companies', 'students', 'companyExpectations', 'studentExpectations', 'topMatches']
        has_all_keys = success and all(key in response_data for key in expected_keys)
        
        # Validate data types
        valid_structure = False
        if has_all_keys:
            valid_structure = (
                isinstance(response_data['totalMatches'], (int, float)) and
                isinstance(response_data['companies'], int) and
                isinstance(response_data['students'], int) and
                isinstance(response_data['companyExpectations'], list) and
                isinstance(response_data['studentExpectations'], list) and
                isinstance(response_data['topMatches'], list)
            )
        
        if success and has_all_keys and valid_structure:
            return self.log_test("Matching Analysis", True, 
                               f"- Total matches: {response_data['totalMatches']}%, Companies: {response_data['companies']}, Students: {response_data['students']}")
        else:
            return self.log_test("Matching Analysis", False, 
                               f"- Status: {status}, Structure valid: {valid_structure if success else 'Failed'}")

    def test_health_check(self):
        """Test health check endpoint"""
        success, status, response_data = self.make_request('GET', 'health')
        
        if success and response_data.get('status') == 'healthy':
            return self.log_test("Health Check", True, f"- Status: {response_data.get('status')}")
        else:
            return self.log_test("Health Check", False, f"- Status: {status}, Data: {response_data}")

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        invalid_data = {
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        }
        
        success, status, response_data = self.make_request(
            'POST', 'login', invalid_data, expected_status=401
        )
        
        if success:  # Success means it correctly rejected invalid credentials
            return self.log_test("Invalid Login", True, "- Correctly rejected invalid credentials")
        else:
            return self.log_test("Invalid Login", False, f"- Status: {status}, Data: {response_data}")

    def test_unauthorized_access(self):
        """Test accessing protected endpoints without token"""
        success, status, response_data = self.make_request(
            'GET', 'profile', expected_status=401
        )
        
        if success:  # Success means it correctly rejected unauthorized access
            return self.log_test("Unauthorized Access", True, "- Correctly rejected unauthorized access")
        else:
            return self.log_test("Unauthorized Access", False, f"- Status: {status}, Data: {response_data}")

    def run_comprehensive_tests(self):
        """Run all tests in logical order"""
        print("\n" + "="*60)
        print("🧪 COMPREHENSIVE API TESTING STARTED")
        print("="*60)
        
        # Basic endpoint tests
        print("\n📊 Testing Basic Endpoints...")
        self.test_health_check()
        self.test_stats_endpoint()
        self.test_unauthorized_access()
        self.test_invalid_login()
        
        # User registration tests
        print("\n👥 Testing User Registration...")
        self.test_user_registration('aluno')
        self.test_user_registration('professor')
        self.test_user_registration('empresa')
        
        # NEW: User registration with expectations
        print("\n🆕 Testing NEW User Registration with Expectations...")
        self.test_user_registration_with_expectations('empresa')
        self.test_user_registration_with_expectations('aluno')
        self.test_user_registration_with_expectations('professor')
        
        # Authentication tests
        print("\n🔐 Testing Authentication...")
        self.test_user_login('aluno')
        self.test_user_login('professor')
        self.test_user_login('empresa')
        
        # Profile access tests
        print("\n👤 Testing Profile Access...")
        self.test_profile_access('aluno')
        self.test_profile_access('professor')
        self.test_profile_access('empresa')
        
        # Challenge management tests
        print("\n🎯 Testing Challenge Management...")
        self.test_create_challenge('aluno')      # Should fail
        self.test_create_challenge('professor')  # Should succeed
        self.test_create_challenge('empresa')    # Should succeed
        self.test_list_challenges()
        
        # Solution management tests
        print("\n💡 Testing Solution Management...")
        self.test_create_solution('aluno')
        self.test_create_solution('professor')
        self.test_list_solutions()
        
        # Voting system tests
        print("\n🗳️ Testing Voting System...")
        self.test_voting('aluno')
        self.test_voting('empresa')
        self.test_duplicate_vote('aluno')  # Should fail
        
        # Leaderboard tests
        print("\n🏆 Testing Leaderboard...")
        self.test_leaderboard()
        
        # NEW: Matching analysis tests
        print("\n🆕 Testing NEW Matching Analysis...")
        self.test_matching_analysis()
        
        # Final stats check
        print("\n📈 Final Stats Check...")
        self.test_stats_endpoint()
        
        # Print summary
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("⚠️ SOME TESTS FAILED!")
            return 1

def main():
    """Main test execution"""
    tester = PlatformAPITester()
    return tester.run_comprehensive_tests()

if __name__ == "__main__":
    sys.exit(main())