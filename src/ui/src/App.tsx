import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ProjectManager from './pages/ProjectManager';
import GeometryEditor from './pages/GeometryEditor';
import ToolpathEditor from './pages/ToolpathEditor';
import Simulation from './pages/Simulation';
import Monitoring from './pages/Monitoring';
import Settings from './pages/Settings';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<ProjectManager />} />
          <Route path="/geometry" element={<GeometryEditor />} />
          <Route path="/toolpath" element={<ToolpathEditor />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
