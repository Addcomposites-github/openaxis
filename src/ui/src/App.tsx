import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import WorkspaceView from './pages/WorkspaceView';
import Monitoring from './pages/Monitoring';
import Settings from './pages/Settings';
import { hydrateGeometryFiles } from './stores/workspaceStore';

function App() {
  // Restore geometry files from IndexedDB on app startup
  useEffect(() => {
    hydrateGeometryFiles().then((count) => {
      if (count > 0) {
        console.log(`[App] Geometry hydration complete: ${count} files available`);
      }
    });
  }, []);

  return (
    <Router>
      <Layout>
        <ErrorBoundary>
          <Routes>
            {/* Main workspace is the default landing page */}
            <Route path="/" element={<Navigate to="/workspace" replace />} />
            <Route path="/workspace" element={<WorkspaceView />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/settings" element={<Settings />} />
            {/* Redirect old routes for backwards compat */}
            <Route path="/projects" element={<Navigate to="/workspace" replace />} />
            <Route path="/robot-setup" element={<Navigate to="/workspace?mode=setup" replace />} />
            <Route path="/geometry" element={<Navigate to="/workspace?mode=geometry" replace />} />
            <Route path="/toolpath" element={<Navigate to="/workspace?mode=toolpath" replace />} />
            <Route path="/simulation" element={<Navigate to="/workspace?mode=simulation" replace />} />
          </Routes>
        </ErrorBoundary>
      </Layout>
    </Router>
  );
}

export default App;
