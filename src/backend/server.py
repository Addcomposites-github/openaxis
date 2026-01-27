"""
OpenAxis Backend Server

HTTP server for communication between Electron frontend and Python backend.
Provides REST API for geometry processing, toolpath generation, simulation, and robot control.
"""

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import threading
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import what's available - gracefully handle missing modules
try:
    from openaxis.slicing import Toolpath, ToolpathType
except ImportError:
    Toolpath = None
    ToolpathType = None

try:
    from backend.geometry_service import GeometryService
    GEOMETRY_SERVICE_AVAILABLE = True
except ImportError:
    GeometryService = None
    GEOMETRY_SERVICE_AVAILABLE = False

try:
    from backend.toolpath_service import ToolpathService
    TOOLPATH_SERVICE_AVAILABLE = True
except ImportError:
    ToolpathService = None
    TOOLPATH_SERVICE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenAxisAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OpenAxis API"""

    # Shared state
    projects = {}
    geometries = {}
    toolpaths = {}
    simulation = None
    robot_state = {
        'connected': False,
        'enabled': False,
        'moving': False,
        'joint_positions': [0.0] * 6,
        'tcp_position': [0.0, 0.0, 0.0],
        'tcp_orientation': [0.0, 0.0, 0.0],
    }
    geometry_service = GeometryService() if GEOMETRY_SERVICE_AVAILABLE else None
    toolpath_service = ToolpathService() if TOOLPATH_SERVICE_AVAILABLE else None

    def _set_headers(self, status=200):
        """Set HTTP response headers"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _send_json(self, data, status=200):
        """Send JSON response"""
        self._set_headers(status)
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _parse_body(self):
        """Parse JSON body from request"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self._set_headers()

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            if path == '/api/health':
                self._send_json({'status': 'ok', 'version': '0.1.0'})

            elif path == '/api/projects':
                self._send_json({
                    'status': 'success',
                    'data': list(self.projects.values())
                })

            elif path.startswith('/api/projects/'):
                project_id = path.split('/')[-1]
                if project_id in self.projects:
                    self._send_json({
                        'status': 'success',
                        'data': self.projects[project_id]
                    })
                else:
                    self._send_json({
                        'status': 'error',
                        'error': 'Project not found'
                    }, 404)

            elif path == '/api/robot/state':
                self._send_json({
                    'status': 'success',
                    'data': self.robot_state
                })

            elif path == '/api/monitoring/sensors':
                # Mock sensor data
                import random
                import time
                self._send_json({
                    'status': 'success',
                    'data': {
                        'timestamp': time.time(),
                        'temperature': 220 + random.uniform(-5, 5),
                        'flowRate': 10 + random.uniform(-1, 1),
                        'pressure': 5 + random.uniform(-0.5, 0.5),
                    }
                })

            elif path == '/api/monitoring/system':
                import psutil
                self._send_json({
                    'status': 'success',
                    'data': {
                        'cpuUsage': psutil.cpu_percent(),
                        'memoryUsage': psutil.virtual_memory().percent,
                        'diskUsage': psutil.disk_usage('/').percent,
                        'networkLatency': 0,
                    }
                })

            else:
                self._send_json({
                    'status': 'error',
                    'error': 'Endpoint not found'
                }, 404)

        except Exception as e:
            logger.error(f"Error handling GET {path}: {e}", exc_info=True)
            self._send_json({
                'status': 'error',
                'error': str(e)
            }, 500)

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            body = self._parse_body()

            if path == '/api/projects':
                # Create new project
                project = body
                project_id = project.get('id', str(len(self.projects) + 1))
                project['id'] = project_id
                self.projects[project_id] = project

                self._send_json({
                    'status': 'success',
                    'data': project
                })

            elif path == '/api/geometry/import':
                # Import geometry from file
                file_path = body.get('filePath')

                if self.geometry_service and GEOMETRY_SERVICE_AVAILABLE:
                    try:
                        # Use geometry service for real processing
                        geometry_data = self.geometry_service.load_geometry(file_path)
                        self.geometries[geometry_data['id']] = geometry_data

                        self._send_json({
                            'status': 'success',
                            'data': geometry_data
                        })
                    except Exception as e:
                        logger.error(f"Failed to load geometry: {e}")
                        self._send_json({
                            'status': 'error',
                            'error': str(e)
                        }, 400)
                else:
                    # Fallback to mock data
                    geometry_id = str(len(self.geometries) + 1)
                    self.geometries[geometry_id] = {
                        'id': geometry_id,
                        'filePath': file_path,
                        'format': file_path.split('.')[-1] if file_path else 'unknown',
                    }

                    self._send_json({
                        'status': 'success',
                        'data': self.geometries[geometry_id]
                    })

            elif path == '/api/toolpath/generate':
                # Generate toolpath
                geometry_path = body.get('geometryPath')
                params = body.get('params', {})

                if self.toolpath_service and TOOLPATH_SERVICE_AVAILABLE and geometry_path:
                    try:
                        # Use toolpath service for real generation
                        toolpath_data = self.toolpath_service.generate_toolpath(
                            geometry_path,
                            params
                        )
                        self.toolpaths[toolpath_data['id']] = toolpath_data

                        self._send_json({
                            'status': 'success',
                            'data': toolpath_data
                        })
                    except Exception as e:
                        logger.error(f"Failed to generate toolpath: {e}")
                        self._send_json({
                            'status': 'error',
                            'error': str(e)
                        }, 400)
                else:
                    # Fallback to mock data
                    geometry_id = body.get('geometryId', 'unknown')
                    toolpath_id = str(len(self.toolpaths) + 1)
                    self.toolpaths[toolpath_id] = {
                        'id': toolpath_id,
                        'geometryId': geometry_id,
                        'params': params,
                        'segments': [],
                    }

                    self._send_json({
                        'status': 'success',
                        'data': self.toolpaths[toolpath_id]
                    })

            elif path == '/api/robot/connect':
                # Connect to robot
                ip_address = body.get('ipAddress')
                port = body.get('port')

                # TODO: Implement actual robot connection
                self.robot_state['connected'] = True

                self._send_json({
                    'status': 'success',
                    'data': self.robot_state
                })

            elif path == '/api/robot/disconnect':
                # Disconnect from robot
                self.robot_state['connected'] = False
                self.robot_state['enabled'] = False

                self._send_json({
                    'status': 'success',
                    'data': self.robot_state
                })

            elif path == '/api/robot/home':
                # Home robot
                if not self.robot_state['connected']:
                    self._send_json({
                        'status': 'error',
                        'error': 'Robot not connected'
                    }, 400)
                    return

                # TODO: Implement actual homing
                self.robot_state['joint_positions'] = [0.0] * 6

                self._send_json({
                    'status': 'success',
                    'data': self.robot_state
                })

            elif path == '/api/simulation/start':
                # Start simulation
                toolpath_id = body.get('toolpathId')

                # TODO: Implement actual simulation start
                if self.simulation is None:
                    self.simulation = {
                        'running': True,
                        'toolpathId': toolpath_id,
                        'currentTime': 0,
                    }

                self._send_json({
                    'status': 'success',
                    'data': self.simulation
                })

            else:
                self._send_json({
                    'status': 'error',
                    'error': 'Endpoint not found'
                }, 404)

        except Exception as e:
            logger.error(f"Error handling POST {path}: {e}", exc_info=True)
            self._send_json({
                'status': 'error',
                'error': str(e)
            }, 500)

    def do_PUT(self):
        """Handle PUT requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            body = self._parse_body()

            if path.startswith('/api/projects/'):
                # Update project
                project_id = path.split('/')[-1]
                if project_id in self.projects:
                    self.projects[project_id].update(body)
                    self._send_json({
                        'status': 'success',
                        'data': self.projects[project_id]
                    })
                else:
                    self._send_json({
                        'status': 'error',
                        'error': 'Project not found'
                    }, 404)

            else:
                self._send_json({
                    'status': 'error',
                    'error': 'Endpoint not found'
                }, 404)

        except Exception as e:
            logger.error(f"Error handling PUT {path}: {e}", exc_info=True)
            self._send_json({
                'status': 'error',
                'error': str(e)
            }, 500)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            if path.startswith('/api/projects/'):
                # Delete project
                project_id = path.split('/')[-1]
                if project_id in self.projects:
                    del self.projects[project_id]
                    self._send_json({
                        'status': 'success'
                    })
                else:
                    self._send_json({
                        'status': 'error',
                        'error': 'Project not found'
                    }, 404)

            else:
                self._send_json({
                    'status': 'error',
                    'error': 'Endpoint not found'
                }, 404)

        except Exception as e:
            logger.error(f"Error handling DELETE {path}: {e}", exc_info=True)
            self._send_json({
                'status': 'error',
                'error': str(e)
            }, 500)

    def log_message(self, format, *args):
        """Override to use logger instead of print"""
        logger.info("%s - %s" % (self.address_string(), format % args))


def run_server(host='localhost', port=8080):
    """Run the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, OpenAxisAPIHandler)

    logger.info(f'Starting OpenAxis backend server on {host}:{port}')
    logger.info('Press Ctrl+C to stop')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info('Shutting down server...')
        httpd.shutdown()


if __name__ == '__main__':
    # Check for psutil
    try:
        import psutil
    except ImportError:
        logger.warning('psutil not installed, system monitoring will be limited')

    run_server()
