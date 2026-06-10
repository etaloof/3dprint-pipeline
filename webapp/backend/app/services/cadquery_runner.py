"""CadQuery execution and STL/STEP export (fallback pipeline)."""
from __future__ import annotations

import asyncio
import logging
import re
import textwrap
from pathlib import Path

log = logging.getLogger(__name__)

DEMO_BOX_TEMPLATE = textwrap.dedent(
    """
    import cadquery as cq

    length = {length}
    width = {width}
    height = {height}
    wall = {wall}

    result = (
        cq.Workplane("XY")
        .box(length, width, height)
        .faces(">Z")
        .shell(-wall)
    )

    cq.exporters.export(result, "output.step")
    cq.exporters.export(result, "output.stl")
    """
).strip()


def parse_box_dimensions(prompt: str) -> tuple[float, float, float, float]:
    """Heuristic dimension parser for demo / quick fallback."""
    nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*(?:mm|×|x|\*)?", prompt.lower())]
    if len(nums) >= 3:
        return nums[0], nums[1], nums[2], max(1.2, min(nums[0], nums[1], nums[2]) * 0.05)
    return 80.0, 60.0, 40.0, 2.0


def build_demo_script(prompt: str, material: str) -> str:
    length, width, height, wall = parse_box_dimensions(prompt)
    return DEMO_BOX_TEMPLATE.format(
        length=length, width=width, height=height, wall=wall
    )


async def execute_cadquery_script(
    code: str,
    work_dir: Path,
    timeout: int = 120,
) -> dict:
    """Execute CadQuery Python in a subprocess and collect exports."""
    work_dir.mkdir(parents=True, exist_ok=True)
    script_path = work_dir / "model.py"
    script_path.write_text(code)

    proc = await asyncio.create_subprocess_exec(
        "python3",
        str(script_path),
        cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "CadQuery execution timed out"}

    stl = work_dir / "output.stl"
    step = work_dir / "output.step"
    return {
        "ok": proc.returncode == 0 and stl.exists(),
        "returncode": proc.returncode,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
        "stl_path": str(stl) if stl.exists() else None,
        "step_path": str(step) if step.exists() else None,
    }


def cadquery_available() -> bool:
    try:
        import cadquery  # noqa: F401

        return True
    except ImportError:
        return False
