"""
ABB RAPID Post Processor — generates .mod files for ABB IRC5 controllers.

Outputs MoveL/MoveJ instructions with speed data, zone data, and tool/wobj references.
Supports speed data from v5 to v5000, zone data from fine to z200.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from .base import PostProcessorBase, PostProcessorConfig, PointData


# ABB speed data presets (mm/s)
SPEED_DATA = {
    5: 'v5', 10: 'v10', 20: 'v20', 30: 'v30', 40: 'v40', 50: 'v50',
    60: 'v60', 80: 'v80', 100: 'v100', 150: 'v150', 200: 'v200',
    300: 'v300', 400: 'v400', 500: 'v500', 600: 'v600', 800: 'v800',
    1000: 'v1000', 1500: 'v1500', 2000: 'v2000', 2500: 'v2500',
    3000: 'v3000', 4000: 'v4000', 5000: 'v5000',
}


def nearest_speed_data(speed_mm_s: float) -> str:
    """Find the nearest ABB speed data preset."""
    speeds = sorted(SPEED_DATA.keys())
    closest = min(speeds, key=lambda s: abs(s - speed_mm_s))
    return SPEED_DATA[closest]


class RAPIDPostProcessor(PostProcessorBase):
    """ABB RAPID post processor generating .mod files."""

    def __init__(self, config: Optional[PostProcessorConfig] = None):
        cfg = config or PostProcessorConfig(
            format_name='rapid',
            file_extension='.mod',
            comment_prefix='! ',
            speed_units='mm/s',
            zone_data='z5',
            tool_name='tool0',
            work_object='wobj0',
        )
        super().__init__(cfg)
        self._target_count = 0

    def comment(self, text: str) -> str:
        return f"  ! {text}"

    @staticmethod
    def _euler_to_quaternion(rz_deg: float, ry_deg: float, rx_deg: float) -> Tuple[float, float, float, float]:
        """Convert ZYX Euler angles (degrees) to ABB quaternion [qw, qx, qy, qz].

        ABB RAPID robtarget quaternion convention: [q1,q2,q3,q4] = [qw,qx,qy,qz].
        ZYX Euler order = ABB convention (A=rz, B=ry, C=rx).
        Reference: ABB RAPID Reference Manual 3HAC046316, "robtarget" data type.
        """
        rz = math.radians(rz_deg)
        ry = math.radians(ry_deg)
        rx = math.radians(rx_deg)
        cz, sz = math.cos(rz / 2), math.sin(rz / 2)
        cy, sy = math.cos(ry / 2), math.sin(ry / 2)
        cx, sx = math.cos(rx / 2), math.sin(rx / 2)
        qw = cz * cy * cx + sz * sy * sx
        qx = cz * cy * sx - sz * sy * cx
        qy = cz * sy * cx + sz * cy * sx
        qz = sz * cy * cx - cz * sy * sx
        return (qw, qx, qy, qz)

    def _robtarget(self, pt: PointData) -> str:
        """Format a robtarget (position + quaternion).

        Orientation is derived from the slicing plane normal stored in pt.layer_normal.
        The normal defines the "up" direction of the print layer; the tool Z-axis
        aligns with it (approaches the surface perpendicular to the layer plane).

        HARDCODED CAVEAT: For planar Z-up slicing, layer_normal = [0,0,1] always,
        giving quaternion ≈ [0,0,-1,0] (tool pointing straight down). This is only
        correct when the build plate is horizontal and the robot base Z is vertical.
        For tilted build plates, positioners, or non-planar slicers the actual
        plane normal must come from the slicer geometry — [0,0,1] is only an
        approximation that happens to be correct for the common flat-plate case.

        ABB RAPID robtarget: [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax_a,...]]
        Reference: ABB RAPID Reference Manual 3HAC046316.
        """
        self._target_count += 1
        rz, ry, rx = self.normal_to_zyx_euler(pt.layer_normal)
        qw, qx, qy, qz = self._euler_to_quaternion(rz, ry, rx)
        return (
            f"[[{pt.x:.2f},{pt.y:.2f},{pt.z:.2f}],"
            f"[{qw:.6f},{qx:.6f},{qy:.6f},{qz:.6f}],"
            f"[0,0,0,0],"
            f"[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]]"
        )

    def header(self, toolpath_data: Dict[str, Any]) -> List[str]:
        name = self.config.program_name
        total_layers = toolpath_data.get('totalLayers', 0)
        total_points = toolpath_data.get('statistics', {}).get('totalPoints', 0)

        # TCP offset: [x,y,z,rx,ry,rz] meters + degrees ZYX, in flange frame.
        # Sourced from toolpath_data['tcpOffset'] when the export pipeline passes it.
        # HARDCODED CAVEAT: defaults to [0,0,150mm] if absent — a typical WAAM torch
        # standoff that is NOT derived from the actual UI tool configuration.
        # This will be replaced once the export endpoint threads tcpOffset through.
        # Until then: verify tooldata against the actual mounted tool before running.
        tcp = toolpath_data.get('tcpOffset', [0.0, 0.0, 0.15, 0.0, 0.0, 0.0])
        tx_mm = (tcp[0] if len(tcp) > 0 else 0.0) * 1000.0
        ty_mm = (tcp[1] if len(tcp) > 1 else 0.0) * 1000.0
        tz_mm = (tcp[2] if len(tcp) > 2 else 0.15) * 1000.0
        t_rx  = tcp[3] if len(tcp) > 3 else 0.0
        t_ry  = tcp[4] if len(tcp) > 4 else 0.0
        t_rz  = tcp[5] if len(tcp) > 5 else 0.0
        t_qw, t_qx, t_qy, t_qz = self._euler_to_quaternion(t_rz, t_ry, t_rx)
        mass = toolpath_data.get('toolMass', 5.0)

        lines = [
            f"MODULE {name}",
            f"  ! Generated by OpenAxis Post Processor",
            f"  ! Layers: {total_layers}, Points: {total_points}",
            f"  ! Format: ABB RAPID",
            f"  ! NOTE: tooldata sourced from toolpath tcpOffset field.",
            f"  !   Default Z={tz_mm:.1f}mm if tcpOffset absent. Verify before running.",
            f"",
            f"  ! Tool and work object declarations",
            f"  ! tooldata: [robhold, [[tcp_pos_mm], [tcp_quat]], [mass, [cog], [aom], Ix,Iy,Iz]]",
            f"  ! tcp_pos: TCP position in mm relative to flange origin.",
            f"  ! tcp_quat: [q1,q2,q3,q4]=[qw,qx,qy,qz] — TCP frame rotation in flange frame.",
            f"  PERS tooldata {self.config.tool_name}:=[TRUE,"
            f"[[{tx_mm:.2f},{ty_mm:.2f},{tz_mm:.2f}],[{t_qw:.6f},{t_qx:.6f},{t_qy:.6f},{t_qz:.6f}]],"
            f"[{mass:.1f},[0,0,{tz_mm/2:.1f}],[1,0,0,0],0,0,0]];",
            f"  PERS wobjdata {self.config.work_object}:=[FALSE,TRUE,\"\",[[0,0,0],[1,0,0,0]],[[0,0,0],[1,0,0,0]]];",
            f"",
            f"  PROC main()",
            f"    ! Initialize",
            f"    ConfL\\Off;",
            f"    SingArea\\Wrist;",
        ]
        return lines

    def footer(self) -> List[str]:
        return [
            f"    ! Program complete",
            f"    MoveJ [[0,0,500],[0,0,-1,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]],v200,z50,{self.config.tool_name}\\WObj:={self.config.work_object};",
            f"  ENDPROC",
            f"ENDMODULE",
        ]

    def linear_move(self, pt: PointData) -> List[str]:
        speed = nearest_speed_data(pt.speed)
        zone = self.config.zone_data
        target = self._robtarget(pt)
        return [
            f"    MoveL {target},{speed},{zone},{self.config.tool_name}\\WObj:={self.config.work_object};"
        ]

    def rapid_move(self, pt: PointData) -> List[str]:
        speed = nearest_speed_data(min(pt.speed * 2, 5000))
        target = self._robtarget(pt)
        return [
            f"    MoveJ {target},{speed},z50,{self.config.tool_name}\\WObj:={self.config.work_object};"
        ]

    def process_on_code(self, pt: PointData) -> List[str]:
        return [
            f"    ! Process ON",
            f"    SetDO DO_ProcessOn, 1;",
            f"    WaitTime 0.1;",
        ]

    def process_off_code(self, pt: PointData) -> List[str]:
        return [
            f"    ! Process OFF",
            f"    SetDO DO_ProcessOn, 0;",
            f"    WaitTime 0.1;",
        ]

    def layer_change_code(self, layer: int) -> List[str]:
        return [
            f"",
            f"    ! ===== Layer {layer} =====",
        ]
