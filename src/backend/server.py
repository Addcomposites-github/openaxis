"""
OpenAxis Backend Server

FastAPI server for communication between Electron frontend and Python backend.
Provides REST API for geometry processing, toolpath generation, simulation, and robot control.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Determine project root for config paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# Import services - gracefully handle missing modules
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

try:
    from backend.robot_service import RobotService
    ROBOT_SERVICE_AVAILABLE = True
except ImportError:
    RobotService = None
    ROBOT_SERVICE_AVAILABLE = False

try:
    from backend.simulation_service import SimulationService
    SIMULATION_SERVICE_AVAILABLE = True
except ImportError:
    SimulationService = None
    SIMULATION_SERVICE_AVAILABLE = False

try:
    from openaxis.slicing.gcode import GCodeGenerator, GCodeConfig
    GCODE_AVAILABLE = True
except ImportError:
    GCODE_AVAILABLE = False

try:
    from backend.material_service import MaterialService
    MATERIAL_SERVICE_AVAILABLE = True
except ImportError:
    MaterialService = None
    MATERIAL_SERVICE_AVAILABLE = False

try:
    from backend.workframe_service import WorkFrameService
    WORKFRAME_SERVICE_AVAILABLE = True
except ImportError:
    WorkFrameService = None
    WORKFRAME_SERVICE_AVAILABLE = False

try:
    from backend.validation_service import ValidationService
    VALIDATION_SERVICE_AVAILABLE = True
except ImportError:
    ValidationService = None
    VALIDATION_SERVICE_AVAILABLE = False

try:
    from backend.postprocessor_service import PostProcessorService
    POSTPROCESSOR_SERVICE_AVAILABLE = True
except ImportError:
    PostProcessorService = None
    POSTPROCESSOR_SERVICE_AVAILABLE = False

try:
    from backend.toolpath_editor_service import ToolpathEditorService
    TOOLPATH_EDITOR_SERVICE_AVAILABLE = True
except ImportError:
    ToolpathEditorService = None
    TOOLPATH_EDITOR_SERVICE_AVAILABLE = False

try:
    from backend.mesh_service import MeshService
    MESH_SERVICE_AVAILABLE = True
except ImportError:
    MeshService = None
    MESH_SERVICE_AVAILABLE = False

try:
    from openaxis.core.config import ConfigManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    ConfigManager = None
    CONFIG_MANAGER_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class ApiResponse(BaseModel):
    """Standard API response wrapper."""
    status: str = "success"
    data: Any = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    services: Dict[str, bool] = {}


# -- Robot models --

class FKRequest(BaseModel):
    jointValues: List[float] = Field(default_factory=lambda: [0.0] * 6, min_length=1, max_length=12)
    tcpOffset: Optional[List[float]] = None  # [x, y, z] meters — tool center point offset from flange


class IKRequest(BaseModel):
    targetPosition: List[float] = Field(min_length=3, max_length=3)
    targetOrientation: Optional[List[float]] = None
    initialGuess: Optional[List[float]] = None


class TrajectoryIKRequest(BaseModel):
    waypoints: List[List[float]] = Field(min_length=1)
    initialGuess: Optional[List[float]] = None
    tcpOffset: Optional[List[float]] = None  # [x, y, z, rx, ry, rz] in meters
    maxWaypoints: int = 0  # Deprecated, ignored — full solve or use chunkStart/chunkSize
    chunkStart: int = 0     # Start index for chunked solving (0 = full batch)
    chunkSize: int = 0      # Number of waypoints to solve (0 = all)


class RobotLoadRequest(BaseModel):
    name: str = "abb_irb6700"


class RobotConnectRequest(BaseModel):
    pass


# -- Geometry models --

class GeometryImportRequest(BaseModel):
    filePath: str


# -- Toolpath models --

class ToolpathGenerateRequest(BaseModel):
    geometryPath: str
    params: Dict[str, Any] = Field(default_factory=dict)
    partPosition: Optional[List[float]] = None  # [x, y, z] in mm (Z-up)


class GCodeExportRequest(BaseModel):
    toolpathId: str
    outputPath: Optional[str] = None


# -- Simulation models --

class SimulationCreateRequest(BaseModel):
    toolpathId: str


class SimulationStartRequest(BaseModel):
    toolpathId: Optional[str] = None


# -- Project models --

class ProjectCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str = "Untitled Project"
    description: str = ""

    class Config:
        extra = "allow"


class ProjectUpdateRequest(BaseModel):
    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# Application state (replaces class-level mutable state)
# ---------------------------------------------------------------------------

class AppState:
    """Application state container — single instance per process."""

    def __init__(self) -> None:
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.geometries: Dict[str, Dict[str, Any]] = {}
        self.toolpaths: Dict[str, Dict[str, Any]] = {}
        self.robot_state: Dict[str, Any] = {
            'connected': False,
            'enabled': False,
            'moving': False,
            'joint_positions': [0.0] * 6,
            'tcp_position': [0.0, 0.0, 0.0],
            'tcp_orientation': [0.0, 0.0, 0.0],
        }

        # Initialize services
        self.geometry_service = GeometryService() if GEOMETRY_SERVICE_AVAILABLE else None
        self.toolpath_service = ToolpathService() if TOOLPATH_SERVICE_AVAILABLE else None
        self.robot_service = (
            RobotService(config_dir=str(CONFIG_DIR))
            if ROBOT_SERVICE_AVAILABLE and CONFIG_DIR.exists()
            else None
        )
        self.simulation_service = SimulationService() if SIMULATION_SERVICE_AVAILABLE else None
        self.material_service = MaterialService() if MATERIAL_SERVICE_AVAILABLE else None
        self.workframe_service = WorkFrameService() if WORKFRAME_SERVICE_AVAILABLE else None
        self.validation_service = ValidationService() if VALIDATION_SERVICE_AVAILABLE else None
        self.postprocessor_service = PostProcessorService() if POSTPROCESSOR_SERVICE_AVAILABLE else None
        self.toolpath_editor_service = ToolpathEditorService() if TOOLPATH_EDITOR_SERVICE_AVAILABLE else None
        self.mesh_service = MeshService() if MESH_SERVICE_AVAILABLE else None
        self.config_manager = (
            ConfigManager(config_dir=str(CONFIG_DIR))
            if CONFIG_MANAGER_AVAILABLE and CONFIG_DIR.exists()
            else None
        )


# ---------------------------------------------------------------------------
# FastAPI app setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OpenAxis API",
    version="0.1.0",
    description="REST API for robotic hybrid manufacturing",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = AppState()

# Upload directory for temporary file storage
UPLOAD_DIR = Path(tempfile.gettempdir()) / "openaxis_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return errors in the { status, error } format the frontend expects."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "error": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so the frontend always gets structured JSON, never raw HTML."""
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": "Internal server error"},
    )


@app.on_event("startup")
async def startup_log() -> None:
    logger.info(f"Geometry service: {'OK' if state.geometry_service else 'MOCK'}")
    logger.info(f"Toolpath service: {'OK' if state.toolpath_service else 'MOCK'}")
    logger.info(f"Robot service:    {'OK' if state.robot_service else 'MOCK'}")
    logger.info(f"Simulation:       {'OK' if state.simulation_service else 'MOCK'}")
    logger.info(f"G-code export:    {'OK' if GCODE_AVAILABLE else 'UNAVAILABLE'}")
    logger.info(f"Material service: {'OK' if state.material_service else 'UNAVAILABLE'}")
    logger.info(f"Workframe service: {'OK' if state.workframe_service else 'UNAVAILABLE'}")
    logger.info(f"Validation service: {'OK' if state.validation_service else 'UNAVAILABLE'}")
    logger.info(f"Post processor:    {'OK' if state.postprocessor_service else 'UNAVAILABLE'}")
    logger.info(f"Toolpath editor:   {'OK' if state.toolpath_editor_service else 'UNAVAILABLE'}")
    logger.info(f"Mesh service:      {'OK' if state.mesh_service else 'UNAVAILABLE'}")
    logger.info(f"Config directory:  {CONFIG_DIR}")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        services={
            "geometry": GEOMETRY_SERVICE_AVAILABLE,
            "toolpath": TOOLPATH_SERVICE_AVAILABLE,
            "robot": ROBOT_SERVICE_AVAILABLE,
            "simulation": SIMULATION_SERVICE_AVAILABLE,
            "gcode": GCODE_AVAILABLE,
        }
    )


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.get("/api/projects")
async def list_projects() -> ApiResponse:
    return ApiResponse(data=list(state.projects.values()))


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> ApiResponse:
    if project_id not in state.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=state.projects[project_id])


@app.post("/api/projects")
async def create_project(body: ProjectCreateRequest) -> ApiResponse:
    project = body.model_dump()
    project_id = project.get("id") or str(len(state.projects) + 1)
    project["id"] = project_id
    state.projects[project_id] = project
    return ApiResponse(data=project)


@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, body: ProjectUpdateRequest) -> ApiResponse:
    if project_id not in state.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    state.projects[project_id].update(body.model_dump(exclude_unset=True))
    return ApiResponse(data=state.projects[project_id])


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str) -> ApiResponse:
    if project_id not in state.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    del state.projects[project_id]
    return ApiResponse()


# ---------------------------------------------------------------------------
# Robot
# ---------------------------------------------------------------------------

@app.get("/api/robot/config")
async def robot_config(name: str = "abb_irb6700") -> ApiResponse:
    if state.robot_service:
        data = state.robot_service.get_robot_config(name)
    else:
        data = {
            "name": "ABB IRB 6700-200/2.60",
            "manufacturer": "ABB",
            "type": "industrial_arm",
            "dof": 6,
            "maxPayload": 200,
            "maxReach": 2600,
        }
    return ApiResponse(data=data)


@app.get("/api/robot/available")
async def robot_available() -> ApiResponse:
    robots = state.robot_service.get_available_robots() if state.robot_service else []
    return ApiResponse(data=robots)


@app.get("/api/robot/joint-limits")
async def robot_joint_limits() -> ApiResponse:
    if state.robot_service:
        data = state.robot_service.get_joint_limits()
    else:
        data = {
            "jointNames": [f"joint_{i+1}" for i in range(6)],
            "limits": {f"joint_{i+1}": {"min": -3.14, "max": 3.14} for i in range(6)},
        }
    return ApiResponse(data=data)


@app.get("/api/robot/state")
async def robot_state_get() -> ApiResponse:
    return ApiResponse(data=state.robot_state)


@app.post("/api/robot/load")
async def robot_load(body: RobotLoadRequest) -> ApiResponse:
    if state.robot_service:
        success = state.robot_service.load_robot(body.name)
        if success:
            return ApiResponse(data={"loaded": True, "name": body.name})
        raise HTTPException(status_code=400, detail="Failed to load robot model")
    return ApiResponse(data={"loaded": False, "mock": True})


@app.post("/api/robot/fk")
async def robot_fk(body: FKRequest) -> ApiResponse:
    if state.robot_service:
        data = state.robot_service.forward_kinematics(body.jointValues, tcp_offset=body.tcpOffset)
    else:
        import math
        j1 = body.jointValues[0] if body.jointValues else 0
        j2 = body.jointValues[1] if len(body.jointValues) > 1 else 0
        reach = 2.0
        data = {
            "position": {
                "x": round(reach * math.cos(j1) * math.cos(j2), 4),
                "y": round(reach * math.sin(j1) * math.cos(j2), 4),
                "z": round(0.78 + reach * math.sin(j2), 4),
            },
            "orientation": {"xaxis": [1, 0, 0], "yaxis": [0, 1, 0], "zaxis": [0, 0, 1]},
            "valid": True,
            "mock": True,
        }
    return ApiResponse(data=data)


@app.post("/api/robot/ik")
async def robot_ik(body: IKRequest) -> ApiResponse:
    if state.robot_service:
        data = state.robot_service.inverse_kinematics(
            body.targetPosition, body.targetOrientation, body.initialGuess
        )
    else:
        data = {"solution": None, "valid": False, "error": "Robot service not available"}
    return ApiResponse(data=data)


@app.post("/api/robot/solve-trajectory")
async def robot_solve_trajectory(body: TrajectoryIKRequest) -> ApiResponse:
    if state.robot_service:
        data = state.robot_service.solve_toolpath_ik(
            body.waypoints, body.initialGuess, body.tcpOffset,
            chunk_start=body.chunkStart, chunk_size=body.chunkSize,
        )
    else:
        data = {"trajectory": [], "error": "Robot service not available"}
    return ApiResponse(data=data)


@app.post("/api/robot/connect")
async def robot_connect() -> ApiResponse:
    state.robot_state["connected"] = True
    return ApiResponse(data=state.robot_state)


@app.post("/api/robot/disconnect")
async def robot_disconnect() -> ApiResponse:
    state.robot_state["connected"] = False
    state.robot_state["enabled"] = False
    return ApiResponse(data=state.robot_state)


@app.post("/api/robot/home")
async def robot_home() -> ApiResponse:
    if not state.robot_state["connected"]:
        raise HTTPException(status_code=400, detail="Robot not connected")
    state.robot_state["joint_positions"] = [0.0] * 6
    return ApiResponse(data=state.robot_state)


# ---------------------------------------------------------------------------
# Tool Library
# ---------------------------------------------------------------------------

@app.get("/api/tools")
async def list_tools() -> ApiResponse:
    """List available tool configurations from config/tools/*.yaml."""
    if state.config_manager:
        try:
            tool_names = state.config_manager.list_tools()
            tool_data = []
            for name in tool_names:
                t = state.config_manager.get_tool(name)
                tool_data.append({
                    "id": name,
                    "name": t.name,
                    "type": t.type,
                    "tcpOffset": t.tcp_offset,
                    "mass": t.mass,
                    "description": t.description,
                    "properties": t.properties,
                })
            return ApiResponse(data=tool_data)
        except Exception as e:
            logger.warning(f"Failed to load tools: {e}")
    return ApiResponse(data=[])


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

@app.post("/api/geometry/import")
async def geometry_import(body: GeometryImportRequest) -> ApiResponse:
    return await _geometry_import_handler(body)


@app.post("/api/geometry/upload")
async def geometry_upload(body: GeometryImportRequest) -> ApiResponse:
    return await _geometry_import_handler(body)


@app.post("/api/geometry/upload-file")
async def geometry_upload_file(file: UploadFile = File(...)) -> ApiResponse:
    """Upload a geometry file (STL/OBJ/PLY) and return the server-side path."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    allowed = {".stl", ".obj", ".ply", ".off", ".step", ".stp"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    # Save to upload directory with unique name
    import uuid
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest = UPLOAD_DIR / safe_name
    contents = await file.read()
    dest.write_bytes(contents)

    return ApiResponse(data={
        "serverPath": str(dest),
        "originalName": file.filename,
        "size": len(contents),
        "format": ext.lstrip("."),
    })


async def _geometry_import_handler(body: GeometryImportRequest) -> ApiResponse:
    if state.geometry_service and body.filePath:
        try:
            geometry_data = state.geometry_service.load_geometry(body.filePath)
            state.geometries[geometry_data["id"]] = geometry_data
            return ApiResponse(data=geometry_data)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"File not found: {body.filePath}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Fallback mock
    geometry_id = str(len(state.geometries) + 1)
    state.geometries[geometry_id] = {
        "id": geometry_id,
        "filePath": body.filePath,
        "format": body.filePath.rsplit(".", 1)[-1] if body.filePath else "unknown",
    }
    return ApiResponse(data=state.geometries[geometry_id])


# ---------------------------------------------------------------------------
# Toolpath
# ---------------------------------------------------------------------------

@app.get("/api/toolpath/{toolpath_id}")
async def get_toolpath(toolpath_id: str) -> ApiResponse:
    if state.toolpath_service:
        data = state.toolpath_service.get_toolpath(toolpath_id)
    else:
        data = state.toolpaths.get(toolpath_id)

    if data:
        return ApiResponse(data=data)
    raise HTTPException(status_code=404, detail="Toolpath not found")


@app.post("/api/toolpath/generate")
async def toolpath_generate(body: ToolpathGenerateRequest) -> ApiResponse:
    if state.toolpath_service and body.geometryPath:
        try:
            # Run the synchronous slicer (ORNL Slicer 2 subprocess) in a
            # thread pool so it doesn't block the async event loop.
            import asyncio

            toolpath_data = await asyncio.to_thread(
                state.toolpath_service.generate_toolpath,
                body.geometryPath,
                body.params,
                body.partPosition,
            )
            state.toolpaths[toolpath_data["id"]] = toolpath_data
            return ApiResponse(data=toolpath_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Fallback mock
    toolpath_id = str(len(state.toolpaths) + 1)
    state.toolpaths[toolpath_id] = {
        "id": toolpath_id,
        "geometryPath": body.geometryPath,
        "params": body.params,
        "segments": [],
        "statistics": {
            "totalSegments": 0,
            "totalPoints": 0,
            "layerCount": 0,
            "estimatedTime": 0,
            "estimatedMaterial": 0,
        },
    }
    return ApiResponse(data=state.toolpaths[toolpath_id])


@app.post("/api/toolpath/export-gcode")
async def toolpath_export_gcode(body: GCodeExportRequest) -> ApiResponse:
    toolpath_data = state.toolpaths.get(body.toolpathId)
    if not toolpath_data:
        raise HTTPException(status_code=404, detail="Toolpath not found")

    try:
        import datetime

        segments = toolpath_data.get("segments", [])
        layer_height = toolpath_data.get("layerHeight", 0.3)
        process_type = toolpath_data.get("processType", "unknown")
        total_layers = toolpath_data.get("totalLayers", 0)
        stats = toolpath_data.get("statistics", {})

        lines: list[str] = []

        # ---- Header ----
        lines.append("; Generated by OpenAxis")
        lines.append(f"; Date: {datetime.datetime.now().isoformat()}")
        lines.append(f"; Toolpath ID: {body.toolpathId}")
        lines.append(f"; Process: {process_type}")
        lines.append(f"; Layers: {total_layers}")
        lines.append(f"; Layer Height: {layer_height:.3f} mm")
        if stats:
            lines.append(f"; Segments: {stats.get('totalSegments', 0)}")
            lines.append(f"; Points: {stats.get('totalPoints', 0)}")
            est_time = stats.get("estimatedTime", 0)
            if est_time:
                lines.append(f"; Estimated Time: {est_time:.0f}s")
        lines.append("")

        # ---- Initialization ----
        lines.append("; --- Initialization ---")
        lines.append("G21 ; Set units to millimeters")
        lines.append("G90 ; Absolute positioning")
        lines.append("M82 ; Absolute extrusion")
        lines.append("G28 ; Home all axes")
        lines.append("G92 E0 ; Reset extruder")
        lines.append("")

        # ---- Segments ----
        current_z = 0.0
        current_layer = -1
        retract_dist = 2.0
        z_hop = 0.5
        extrusion = 0.0
        extrusion_width = 0.6

        for seg in segments:
            seg_layer = seg.get("layer", 0)
            seg_type = seg.get("type", "unknown")
            seg_speed = seg.get("speed", 1000)
            points = seg.get("points", [])
            if not points:
                continue

            # Layer change comment
            if seg_layer != current_layer:
                current_layer = seg_layer
                new_z = seg_layer * layer_height
                lines.append(f"\n; Layer {seg_layer} (Z={new_z:.3f})")
                if new_z != current_z:
                    lines.append(f"G0 Z{new_z:.3f}")
                    current_z = new_z

            # Travel moves: retract, Z-hop, rapid move, un-retract
            if seg_type.lower() in ("travel", "move", "rapid"):
                lines.append("; Travel")
                lines.append(f"G1 E{extrusion - retract_dist:.4f} F{40 * 60:.0f} ; Retract")
                lines.append(f"G0 Z{current_z + z_hop:.3f} ; Z-hop")
                pt = points[-1]
                x, y = pt[0], pt[1]
                z_val = pt[2] if len(pt) > 2 else current_z
                lines.append(f"G0 X{x:.3f} Y{y:.3f} Z{z_val + z_hop:.3f}")
                lines.append(f"G0 Z{z_val:.3f} ; Un-hop")
                lines.append(f"G1 E{extrusion:.4f} F{40 * 60:.0f} ; Un-retract")
                current_z = z_val
            else:
                # Print / Extrusion moves
                lines.append(f"; {seg_type.capitalize()}")
                for i, pt in enumerate(points):
                    x, y = pt[0], pt[1]
                    z_val = pt[2] if len(pt) > 2 else current_z
                    if i == 0:
                        lines.append(f"G0 X{x:.3f} Y{y:.3f}")
                    else:
                        prev = points[i - 1]
                        dx = x - prev[0]
                        dy = y - prev[1]
                        dist = (dx ** 2 + dy ** 2) ** 0.5
                        extrusion += dist * extrusion_width * layer_height / 10.0
                        lines.append(
                            f"G1 X{x:.3f} Y{y:.3f} E{extrusion:.4f} F{seg_speed:.0f}"
                        )
                    current_z = z_val

        # ---- Footer ----
        lines.append("")
        lines.append("; --- End G-code ---")
        lines.append(f"G1 E{extrusion - retract_dist:.4f} F{40 * 60:.0f} ; Final retract")
        lines.append(f"G0 Z{current_z + 10:.3f} ; Raise Z")
        lines.append("G28 X Y ; Home X/Y")
        lines.append("M84 ; Disable motors")
        lines.append("; OpenAxis export complete")

        gcode = "\n".join(lines)

        # Write to temp file
        output_dir = Path(tempfile.gettempdir()) / "openaxis_gcode"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"toolpath_{body.toolpathId}.gcode"
        output_path.write_text(gcode, encoding="utf-8")

        return ApiResponse(data={
            "gcodeContent": gcode,
            "gcodeFile": str(output_path),
            "lines": len(lines),
            "size": len(gcode),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

@app.get("/api/simulation/state")
async def simulation_state(id: Optional[str] = None) -> ApiResponse:
    if state.simulation_service:
        data = state.simulation_service.get_simulation_state(id)
    else:
        data = {"status": "no_simulation"}
    return ApiResponse(data=data)


@app.get("/api/simulation/trajectory")
async def simulation_trajectory(id: Optional[str] = None) -> ApiResponse:
    if state.simulation_service:
        data = state.simulation_service.get_trajectory(id)
    else:
        data = {"waypoints": [], "totalTime": 0}
    return ApiResponse(data=data)


@app.get("/api/simulation/list")
async def simulation_list() -> ApiResponse:
    if state.simulation_service:
        data = state.simulation_service.list_simulations()
    else:
        data = []
    return ApiResponse(data=data)


@app.post("/api/simulation/create")
async def simulation_create(body: SimulationCreateRequest) -> ApiResponse:
    toolpath_data = state.toolpaths.get(body.toolpathId)
    if not toolpath_data:
        raise HTTPException(status_code=404, detail="Toolpath not found")

    if state.simulation_service:
        robot_config = None
        if state.robot_service:
            robot_config = state.robot_service.get_robot_config()
        data = state.simulation_service.create_simulation(toolpath_data, robot_config)
        return ApiResponse(data=data)

    return ApiResponse(data={
        "id": "mock_sim",
        "status": "ready",
        "totalTime": 0,
        "totalWaypoints": 0,
    })


@app.post("/api/simulation/start")
async def simulation_start(body: SimulationStartRequest) -> ApiResponse:
    if state.simulation_service:
        sim_state = state.simulation_service.get_simulation_state()
        if sim_state.get("status") == "no_simulation" and body.toolpathId:
            toolpath_data = state.toolpaths.get(body.toolpathId, {})
            state.simulation_service.create_simulation(toolpath_data)
        data = state.simulation_service.get_simulation_state()
    else:
        data = {"status": "running", "toolpathId": body.toolpathId}
    return ApiResponse(data=data)


@app.post("/api/simulation/stop")
async def simulation_stop() -> ApiResponse:
    if state.simulation_service:
        state.simulation_service.stop_playback()
    return ApiResponse(data={"status": "stopped"})


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------


@app.get("/api/materials")
async def get_materials(process_type: Optional[str] = None, category: Optional[str] = None) -> ApiResponse:
    """Get all materials, optionally filtered by process type or category."""
    if not state.material_service:
        # Return built-in defaults even without service
        from openaxis.core.materials import BUILT_IN_MATERIALS
        materials = [m.to_dict() for m in BUILT_IN_MATERIALS]
        if process_type:
            materials = [m for m in materials if m['processType'] == process_type]
        if category:
            materials = [m for m in materials if m['category'] == category]
        return ApiResponse(data=materials)

    if process_type:
        data = state.material_service.get_materials_by_process(process_type)
    elif category:
        data = state.material_service.get_materials_by_category(category)
    else:
        data = state.material_service.get_all_materials()
    return ApiResponse(data=data)


@app.get("/api/materials/summary")
async def get_materials_summary() -> ApiResponse:
    """Get summary of available materials."""
    if not state.material_service:
        return ApiResponse(data={
            'totalMaterials': 0,
            'builtIn': 0,
            'custom': 0,
            'processTypes': [],
            'categories': [],
            'materialsPerProcess': {},
        })
    return ApiResponse(data=state.material_service.get_summary())


@app.get("/api/materials/process-types")
async def get_process_types() -> ApiResponse:
    """Get list of available process types."""
    if not state.material_service:
        return ApiResponse(data=['waam', 'pellet_extrusion', 'milling'])
    return ApiResponse(data=state.material_service.get_process_types())


@app.get("/api/materials/{material_id}")
async def get_material(material_id: str) -> ApiResponse:
    """Get a single material by ID."""
    if not state.material_service:
        raise HTTPException(status_code=503, detail="Material service unavailable")
    data = state.material_service.get_material_by_id(material_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Material '{material_id}' not found")
    return ApiResponse(data=data)


class CreateMaterialRequest(BaseModel):
    id: str
    name: str
    processType: str
    category: str = 'metal'
    description: str = ''
    properties: Dict[str, Any] = {}
    slicingDefaults: Dict[str, Any] = {}


@app.post("/api/materials")
async def create_material(req: CreateMaterialRequest) -> ApiResponse:
    """Create a custom material profile."""
    if not state.material_service:
        raise HTTPException(status_code=503, detail="Material service unavailable")
    data = state.material_service.create_custom_material(req.dict())
    return ApiResponse(data=data)


@app.delete("/api/materials/{material_id}")
async def delete_material(material_id: str) -> ApiResponse:
    """Delete a custom material (built-in materials cannot be deleted)."""
    if not state.material_service:
        raise HTTPException(status_code=503, detail="Material service unavailable")
    success = state.material_service.delete_custom_material(material_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete built-in material or material not found")
    return ApiResponse(data={"deleted": material_id})


# ---------------------------------------------------------------------------
# Work Frames
# ---------------------------------------------------------------------------


class CreateWorkFrameRequest(BaseModel):
    id: str
    name: str
    position: List[float] = [0.0, 0.0, 0.0]
    rotation: List[float] = [0.0, 0.0, 0.0]
    size: List[float] = [1.0, 0.05, 1.0]
    alignmentMethod: str = 'manual'
    color: str = '#3b82f6'


class UpdateWorkFrameRequest(BaseModel):
    class Config:
        extra = "allow"


class AlignFrameRequest(BaseModel):
    origin: List[float] = Field(min_length=3, max_length=3)
    zPoint: List[float] = Field(min_length=3, max_length=3)
    xPoint: List[float] = Field(min_length=3, max_length=3)


class TransformPointRequest(BaseModel):
    point: List[float] = Field(min_length=3, max_length=3)
    frameId: str
    direction: str = 'to_frame'  # 'to_frame' or 'from_frame'


@app.get("/api/workframes")
async def get_workframes() -> ApiResponse:
    """Get all work frames."""
    if not state.workframe_service:
        return ApiResponse(data=[{
            'id': 'default_workframe',
            'name': 'Build Platform',
            'position': [2000, 0, 0],
            'rotation': [0, 0, 0],
            'size': [1.5, 0.05, 1.5],
            'alignmentMethod': 'manual',
            'childPartIds': [],
            'isDefault': True,
            'visible': True,
            'color': '#3b82f6',
        }])
    return ApiResponse(data=state.workframe_service.get_all_frames())


@app.get("/api/workframes/{frame_id}")
async def get_workframe(frame_id: str) -> ApiResponse:
    """Get a single work frame."""
    if not state.workframe_service:
        raise HTTPException(status_code=503, detail="Workframe service unavailable")
    data = state.workframe_service.get_frame(frame_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Work frame '{frame_id}' not found")
    return ApiResponse(data=data)


@app.post("/api/workframes")
async def create_workframe(req: CreateWorkFrameRequest) -> ApiResponse:
    """Create a new work frame."""
    if not state.workframe_service:
        raise HTTPException(status_code=503, detail="Workframe service unavailable")
    data = state.workframe_service.create_frame(req.dict())
    return ApiResponse(data=data)


@app.put("/api/workframes/{frame_id}")
async def update_workframe(frame_id: str, body: UpdateWorkFrameRequest) -> ApiResponse:
    """Update a work frame."""
    if not state.workframe_service:
        raise HTTPException(status_code=503, detail="Workframe service unavailable")
    data = state.workframe_service.update_frame(frame_id, body.dict(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=404, detail=f"Work frame '{frame_id}' not found")
    return ApiResponse(data=data)


@app.delete("/api/workframes/{frame_id}")
async def delete_workframe(frame_id: str) -> ApiResponse:
    """Delete a work frame (cannot delete default)."""
    if not state.workframe_service:
        raise HTTPException(status_code=503, detail="Workframe service unavailable")
    success = state.workframe_service.delete_frame(frame_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete default frame or frame not found")
    return ApiResponse(data={"deleted": frame_id})


@app.post("/api/workframes/align")
async def align_workframe(req: AlignFrameRequest) -> ApiResponse:
    """Compute frame position and rotation from Z+X alignment method."""
    if not state.workframe_service:
        raise HTTPException(status_code=503, detail="Workframe service unavailable")
    position, rotation = state.workframe_service.compute_alignment_z_plus_x(
        tuple(req.origin), tuple(req.zPoint), tuple(req.xPoint)
    )
    return ApiResponse(data={
        'position': list(position),
        'rotation': list(rotation),
    })


@app.post("/api/workframes/transform-point")
async def transform_point(req: TransformPointRequest) -> ApiResponse:
    """Transform a point to/from a work frame's local coordinates."""
    if not state.workframe_service:
        raise HTTPException(status_code=503, detail="Workframe service unavailable")

    point = tuple(req.point)
    if req.direction == 'to_frame':
        result = state.workframe_service.transform_point_to_frame(point, req.frameId)
    else:
        result = state.workframe_service.transform_point_from_frame(point, req.frameId)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Work frame '{req.frameId}' not found")
    return ApiResponse(data={'point': list(result)})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationCheckRequest(BaseModel):
    toolpathId: str
    reachability: Optional[List[bool]] = None


@app.post("/api/validation/check")
async def validation_check(req: ValidationCheckRequest) -> ApiResponse:
    """Run full quality validation on a toolpath."""
    toolpath_data = state.toolpaths.get(req.toolpathId)
    if not toolpath_data:
        raise HTTPException(status_code=404, detail="Toolpath not found")

    if state.validation_service:
        report = state.validation_service.check_all(
            toolpath_data,
            reachability_array=req.reachability,
        )
        return ApiResponse(data=report.to_dict())

    # Fallback: return basic report without service
    return ApiResponse(data={
        'overallScore': 100,
        'recommendations': [],
        'reachability': {
            'total_points': 0,
            'reachable_count': 0,
            'unreachable_count': 0,
            'reachability_pct': 100.0,
        },
        'singularities': {
            'total_zones': 0,
            'zones': [],
        },
    })


# ---------------------------------------------------------------------------
# Post Processor
# ---------------------------------------------------------------------------


class PostProcessorExportRequest(BaseModel):
    toolpathId: str
    format: str = 'gcode'
    config: Optional[Dict[str, Any]] = None


@app.get("/api/postprocessor/formats")
async def postprocessor_formats() -> ApiResponse:
    """Get list of available export formats."""
    if state.postprocessor_service:
        return ApiResponse(data=state.postprocessor_service.get_available_formats())
    return ApiResponse(data=[
        {'id': 'gcode', 'name': 'G-code', 'extension': '.gcode', 'vendor': 'Generic', 'available': False},
        {'id': 'rapid', 'name': 'ABB RAPID', 'extension': '.mod', 'vendor': 'ABB', 'available': False},
        {'id': 'krl', 'name': 'KUKA KRL', 'extension': '.src', 'vendor': 'KUKA', 'available': False},
        {'id': 'fanuc', 'name': 'Fanuc LS', 'extension': '.ls', 'vendor': 'Fanuc', 'available': False},
    ])


@app.get("/api/postprocessor/config/{format_name}")
async def postprocessor_default_config(format_name: str) -> ApiResponse:
    """Get default configuration for a post processor format."""
    if not state.postprocessor_service:
        raise HTTPException(status_code=503, detail="Post processor service unavailable")
    return ApiResponse(data=state.postprocessor_service.get_default_config(format_name))


@app.post("/api/postprocessor/export")
async def postprocessor_export(req: PostProcessorExportRequest) -> ApiResponse:
    """Export toolpath in the specified format."""
    toolpath_data = state.toolpaths.get(req.toolpathId)
    if not toolpath_data:
        raise HTTPException(status_code=404, detail="Toolpath not found")

    if not state.postprocessor_service:
        raise HTTPException(status_code=503, detail="Post processor service unavailable")

    result = state.postprocessor_service.export(
        toolpath_data,
        format_name=req.format,
        config_overrides=req.config,
    )

    if 'error' in result and result['error']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Write to temp file
    import tempfile
    output_dir = Path(tempfile.gettempdir()) / "openaxis_exports"
    output_dir.mkdir(exist_ok=True)
    ext = result.get('extension', '.gcode')
    output_path = output_dir / f"toolpath_{req.toolpathId}{ext}"
    output_path.write_text(result['content'], encoding='utf-8')
    result['filePath'] = str(output_path)

    return ApiResponse(data=result)


# ---------------------------------------------------------------------------
# Toolpath Editor
# ---------------------------------------------------------------------------


class ToolpathModifyRequest(BaseModel):
    toolpathId: str
    action: str  # 'speed_override', 'deposition_override', 'delete', 'reverse', 'add_delay', 'split'
    segmentIndices: List[int] = Field(default_factory=list)
    value: Optional[float] = None  # new speed, new rate, delay seconds, split point index
    config: Optional[Dict[str, Any]] = None


@app.post("/api/toolpath/{toolpath_id}/modify")
async def toolpath_modify(toolpath_id: str, body: ToolpathModifyRequest) -> ApiResponse:
    """Apply a modification to a toolpath's segments."""
    toolpath_data = state.toolpaths.get(toolpath_id)
    if not toolpath_data:
        raise HTTPException(status_code=404, detail="Toolpath not found")

    if not state.toolpath_editor_service:
        raise HTTPException(status_code=503, detail="Toolpath editor service unavailable")

    action = body.action
    indices = body.segmentIndices
    value = body.value

    try:
        if action == 'speed_override' and value is not None:
            state.toolpath_editor_service.apply_speed_override(toolpath_data, indices, value)
        elif action == 'deposition_override' and value is not None:
            state.toolpath_editor_service.apply_deposition_override(toolpath_data, indices, value)
        elif action == 'delete':
            state.toolpath_editor_service.delete_segments(toolpath_data, indices)
        elif action == 'reverse':
            state.toolpath_editor_service.reverse_segments(toolpath_data, indices)
        elif action == 'add_delay' and value is not None and len(indices) > 0:
            state.toolpath_editor_service.add_delay(toolpath_data, indices[0], value)
        elif action == 'split' and value is not None and len(indices) > 0:
            state.toolpath_editor_service.split_segment(toolpath_data, indices[0], int(value))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        # Update stored toolpath
        state.toolpaths[toolpath_id] = toolpath_data
        return ApiResponse(data=toolpath_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Mesh Operations (Sprint 8)
# ---------------------------------------------------------------------------


class MeshBooleanRequest(BaseModel):
    geometryIdA: str
    geometryIdB: str
    operation: str  # 'union', 'subtract', 'intersect'
    resultId: Optional[str] = None


class MeshRepairRequest(BaseModel):
    geometryId: str


class MeshAnalyzeRequest(BaseModel):
    geometryId: str


class MeshOffsetRequest(BaseModel):
    geometryId: str
    distance: float


class MeshUndoRequest(BaseModel):
    geometryId: str


@app.post("/api/geometry/boolean")
async def geometry_boolean(body: MeshBooleanRequest) -> ApiResponse:
    """Perform a boolean operation on two geometry meshes."""
    if not state.mesh_service:
        raise HTTPException(status_code=503, detail="Mesh service unavailable")
    try:
        result = state.mesh_service.boolean(
            body.geometryIdA, body.geometryIdB, body.operation, body.resultId,
        )
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/geometry/repair")
async def geometry_repair(body: MeshRepairRequest) -> ApiResponse:
    """Repair a mesh (fill holes, fix normals, remove degenerate faces)."""
    if not state.mesh_service:
        raise HTTPException(status_code=503, detail="Mesh service unavailable")
    try:
        result = state.mesh_service.repair(body.geometryId)
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/geometry/analyze")
async def geometry_analyze(body: MeshAnalyzeRequest) -> ApiResponse:
    """Analyze mesh quality."""
    if not state.mesh_service:
        raise HTTPException(status_code=503, detail="Mesh service unavailable")
    try:
        result = state.mesh_service.analyze(body.geometryId)
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/geometry/offset")
async def geometry_offset(body: MeshOffsetRequest) -> ApiResponse:
    """Offset mesh uniformly (positive = outward)."""
    if not state.mesh_service:
        raise HTTPException(status_code=503, detail="Mesh service unavailable")
    try:
        result = state.mesh_service.offset(body.geometryId, body.distance)
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/geometry/undo")
async def geometry_undo(body: MeshUndoRequest) -> ApiResponse:
    """Undo the last mesh operation on a geometry."""
    if not state.mesh_service:
        raise HTTPException(status_code=503, detail="Mesh service unavailable")
    result = state.mesh_service.undo(body.geometryId)
    if result is None:
        raise HTTPException(status_code=400, detail="Nothing to undo")
    return ApiResponse(data=result)


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

@app.get("/api/monitoring/sensors")
async def monitoring_sensors() -> ApiResponse:
    import random
    import time as _time
    return ApiResponse(data={
        "timestamp": _time.time(),
        "temperature": round(220 + random.uniform(-5, 5), 1),
        "flowRate": round(10 + random.uniform(-1, 1), 2),
        "pressure": round(5 + random.uniform(-0.5, 0.5), 2),
    })


@app.get("/api/monitoring/system")
async def monitoring_system() -> ApiResponse:
    try:
        import psutil
        import os
        disk_path = "C:/" if os.name == "nt" else "/"
        return ApiResponse(data={
            "cpuUsage": psutil.cpu_percent(interval=0.1),
            "memoryUsage": psutil.virtual_memory().percent,
            "diskUsage": psutil.disk_usage(disk_path).percent,
            "networkLatency": round(psutil.cpu_times().idle % 50, 1),
        })
    except ImportError:
        return ApiResponse(data={
            "cpuUsage": 0,
            "memoryUsage": 0,
            "diskUsage": 0,
            "networkLatency": 0,
        })


# ---------------------------------------------------------------------------
# Static file serving (for converted meshes)
# ---------------------------------------------------------------------------

@app.get("/api/files/{file_path:path}")
async def serve_file(file_path: str) -> FileResponse:
    temp_dir = Path(tempfile.gettempdir()) / "openaxis_converted"
    full_path = temp_dir / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    # Security: ensure the resolved path is inside temp_dir
    if not full_path.resolve().is_relative_to(temp_dir.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    return FileResponse(str(full_path))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run_server(host: str = "localhost", port: int = 8080) -> None:
    """Run the FastAPI server with uvicorn."""
    import uvicorn

    logger.info(f"Starting OpenAxis backend on {host}:{port}")
    logger.info(f"Config directory: {CONFIG_DIR}")
    logger.info("Press Ctrl+C to stop")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
