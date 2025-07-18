import { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Set up axios defaults
axios.defaults.headers.common['Authorization'] = localStorage.getItem('token') ? `Bearer ${localStorage.getItem('token')}` : '';

function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('home');
  const [challenges, setChallenges] = useState([]);
  const [solutions, setSolutions] = useState([]);
  const [selectedChallenge, setSelectedChallenge] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [stats, setStats] = useState({});

  // Auth forms
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ name: '', email: '', password: '', type: 'aluno' });
  
  // Challenge form
  const [challengeForm, setChallengeForm] = useState({ title: '', description: '', deadline: '', reward: '' });
  
  // Solution form
  const [solutionForm, setSolutionForm] = useState({ description: '' });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchProfile();
    }
    fetchChallenges();
    fetchStats();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching profile:', error);
      localStorage.removeItem('token');
      axios.defaults.headers.common['Authorization'] = '';
    }
  };

  const fetchChallenges = async () => {
    try {
      const response = await axios.get(`${API}/challenges`);
      setChallenges(response.data);
    } catch (error) {
      console.error('Error fetching challenges:', error);
    }
  };

  const fetchSolutions = async (challengeId) => {
    try {
      const response = await axios.get(`${API}/challenges/${challengeId}/solutions`);
      setSolutions(response.data);
    } catch (error) {
      console.error('Error fetching solutions:', error);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const response = await axios.get(`${API}/leaderboard`);
      setLeaderboard(response.data);
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API}/login`, loginForm);
      localStorage.setItem('token', response.data.token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
      setUser(response.data.user);
      setCurrentView('challenges');
      setLoginForm({ email: '', password: '' });
    } catch (error) {
      alert('Erro no login: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API}/register`, registerForm);
      // Auto login after registration
      const loginResponse = await axios.post(`${API}/login`, {
        email: registerForm.email,
        password: registerForm.password
      });
      localStorage.setItem('token', loginResponse.data.token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${loginResponse.data.token}`;
      setUser(loginResponse.data.user);
      setCurrentView('challenges');
      setRegisterForm({ name: '', email: '', password: '', type: 'aluno' });
    } catch (error) {
      alert('Erro no registro: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    axios.defaults.headers.common['Authorization'] = '';
    setUser(null);
    setCurrentView('home');
  };

  const handleCreateChallenge = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/challenges`, challengeForm);
      setChallengeForm({ title: '', description: '', deadline: '', reward: '' });
      fetchChallenges();
      alert('Desafio criado com sucesso!');
    } catch (error) {
      alert('Erro ao criar desafio: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const handleCreateSolution = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/solutions`, {
        challenge_id: selectedChallenge.id,
        description: solutionForm.description
      });
      setSolutionForm({ description: '' });
      fetchSolutions(selectedChallenge.id);
      alert('Solução enviada com sucesso!');
    } catch (error) {
      alert('Erro ao enviar solução: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const handleVote = async (solutionId) => {
    try {
      await axios.post(`${API}/solutions/${solutionId}/vote`);
      fetchSolutions(selectedChallenge.id);
      fetchProfile(); // Update user points
      alert('Voto registrado com sucesso!');
    } catch (error) {
      alert('Erro ao votar: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
  };

  const renderHome = () => (
    <div className="home-container">
      <div className="hero-section">
        <h1>Plataforma de Inovação PUC-RS</h1>
        <p>Conectando desafios empresariais com soluções inovadoras da comunidade acadêmica</p>
        
        <div className="stats-grid">
          <div className="stat-card">
            <h3>{stats.total_challenges || 0}</h3>
            <p>Desafios Ativos</p>
          </div>
          <div className="stat-card">
            <h3>{stats.total_solutions || 0}</h3>
            <p>Soluções Enviadas</p>
          </div>
          <div className="stat-card">
            <h3>{stats.total_users || 0}</h3>
            <p>Usuários Cadastrados</p>
          </div>
          <div className="stat-card">
            <h3>{stats.total_votes || 0}</h3>
            <p>Votos Registrados</p>
          </div>
        </div>
      </div>

      {!user && (
        <div className="auth-section">
          <div className="auth-container">
            <div className="auth-forms">
              <div className="auth-form">
                <h2>Entrar</h2>
                <form onSubmit={handleLogin}>
                  <input
                    type="email"
                    placeholder="Email"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({...loginForm, email: e.target.value})}
                    required
                  />
                  <input
                    type="password"
                    placeholder="Senha"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                    required
                  />
                  <button type="submit">Entrar</button>
                </form>
              </div>

              <div className="auth-form">
                <h2>Cadastrar</h2>
                <form onSubmit={handleRegister}>
                  <input
                    type="text"
                    placeholder="Nome"
                    value={registerForm.name}
                    onChange={(e) => setRegisterForm({...registerForm, name: e.target.value})}
                    required
                  />
                  <input
                    type="email"
                    placeholder="Email"
                    value={registerForm.email}
                    onChange={(e) => setRegisterForm({...registerForm, email: e.target.value})}
                    required
                  />
                  <input
                    type="password"
                    placeholder="Senha"
                    value={registerForm.password}
                    onChange={(e) => setRegisterForm({...registerForm, password: e.target.value})}
                    required
                  />
                  <select
                    value={registerForm.type}
                    onChange={(e) => setRegisterForm({...registerForm, type: e.target.value})}
                    required
                  >
                    <option value="aluno">Aluno</option>
                    <option value="professor">Professor</option>
                    <option value="empresa">Empresa</option>
                  </select>
                  <button type="submit">Cadastrar</button>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderChallenges = () => (
    <div className="challenges-container">
      <div className="challenges-header">
        <h2>Desafios Disponíveis</h2>
        {user && (user.type === 'professor' || user.type === 'empresa') && (
          <button onClick={() => setCurrentView('create-challenge')} className="create-btn">
            Criar Desafio
          </button>
        )}
      </div>
      
      <div className="challenges-grid">
        {challenges.map(challenge => (
          <div key={challenge.id} className="challenge-card">
            <h3>{challenge.title}</h3>
            <p>{challenge.description}</p>
            <div className="challenge-meta">
              <span className="creator">Por: {challenge.creator_name}</span>
              {challenge.deadline && <span className="deadline">Prazo: {challenge.deadline}</span>}
              {challenge.reward && <span className="reward">Recompensa: {challenge.reward}</span>}
            </div>
            <button 
              onClick={() => {
                setSelectedChallenge(challenge);
                fetchSolutions(challenge.id);
                setCurrentView('solutions');
              }}
              className="view-btn"
            >
              Ver Soluções
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  const renderCreateChallenge = () => (
    <div className="create-challenge-container">
      <h2>Criar Novo Desafio</h2>
      <form onSubmit={handleCreateChallenge} className="challenge-form">
        <input
          type="text"
          placeholder="Título do desafio"
          value={challengeForm.title}
          onChange={(e) => setChallengeForm({...challengeForm, title: e.target.value})}
          required
        />
        <textarea
          placeholder="Descrição detalhada do desafio"
          value={challengeForm.description}
          onChange={(e) => setChallengeForm({...challengeForm, description: e.target.value})}
          required
        />
        <input
          type="date"
          placeholder="Data limite"
          value={challengeForm.deadline}
          onChange={(e) => setChallengeForm({...challengeForm, deadline: e.target.value})}
        />
        <input
          type="text"
          placeholder="Recompensa (opcional)"
          value={challengeForm.reward}
          onChange={(e) => setChallengeForm({...challengeForm, reward: e.target.value})}
        />
        <button type="submit">Criar Desafio</button>
      </form>
    </div>
  );

  const renderSolutions = () => (
    <div className="solutions-container">
      <div className="solutions-header">
        <h2>Soluções para: {selectedChallenge?.title}</h2>
        <button onClick={() => setCurrentView('challenges')} className="back-btn">
          Voltar aos Desafios
        </button>
      </div>
      
      <div className="challenge-details">
        <p>{selectedChallenge?.description}</p>
      </div>

      {user && (
        <div className="solution-form-container">
          <h3>Enviar Solução</h3>
          <form onSubmit={handleCreateSolution} className="solution-form">
            <textarea
              placeholder="Descreva sua solução"
              value={solutionForm.description}
              onChange={(e) => setSolutionForm({...solutionForm, description: e.target.value})}
              required
            />
            <button type="submit">Enviar Solução</button>
          </form>
        </div>
      )}

      <div className="solutions-list">
        {solutions.map(solution => (
          <div key={solution.id} className="solution-card">
            <div className="solution-header">
              <h4>Por: {solution.author_name}</h4>
              <div className="solution-votes">
                <span>{solution.votes} votos</span>
                {user && user.id !== solution.author_id && (
                  <button onClick={() => handleVote(solution.id)} className="vote-btn">
                    Votar
                  </button>
                )}
              </div>
            </div>
            <p>{solution.description}</p>
            <small>Enviado em: {new Date(solution.submission_date).toLocaleDateString()}</small>
          </div>
        ))}
      </div>
    </div>
  );

  const renderLeaderboard = () => {
    useEffect(() => {
      fetchLeaderboard();
    }, []);

    return (
      <div className="leaderboard-container">
        <h2>Ranking de Pontuação</h2>
        <div className="leaderboard-list">
          {leaderboard.map((player, index) => (
            <div key={player.id} className="leaderboard-item">
              <div className="rank">#{index + 1}</div>
              <div className="player-info">
                <h4>{player.name}</h4>
                <span className="player-type">{player.type}</span>
              </div>
              <div className="points">{player.points} pts</div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <nav className="navbar">
        <div className="nav-brand">
          <h1>PUC-RS Inovação</h1>
        </div>
        <div className="nav-links">
          <button onClick={() => setCurrentView('home')}>Home</button>
          <button onClick={() => setCurrentView('challenges')}>Desafios</button>
          <button onClick={() => setCurrentView('leaderboard')}>Ranking</button>
          {user && (
            <div className="user-info">
              <span>Olá, {user.name}! ({user.points} pts)</span>
              <button onClick={handleLogout}>Sair</button>
            </div>
          )}
        </div>
      </nav>

      <main className="main-content">
        {currentView === 'home' && renderHome()}
        {currentView === 'challenges' && renderChallenges()}
        {currentView === 'create-challenge' && renderCreateChallenge()}
        {currentView === 'solutions' && renderSolutions()}
        {currentView === 'leaderboard' && renderLeaderboard()}
      </main>
    </div>
  );
}

export default App;