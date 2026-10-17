"""
Template engine and loader for AsteroidOS application templates.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, Dict, List


TEMPLATE_DIR = Path(__file__).parent


def render_template_string(template_str: str, context: Dict[str, Any]) -> str:
    """
    Renders a template string replacing {{ key }} placeholders with values from context.
    Also handles basic whitespace stripping.
    """
    def replace_var(match):
        key = match.group(1).strip()
        val = context.get(key)
        return str(val) if val is not None else ""

    # Replace {{ var }}
    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace_var, template_str)


class TemplateManager:
    """Manages built-in and custom AsteroidOS application templates."""

    TEMPLATES = ["qml_cpp", "python"]

    @classmethod
    def list_templates(cls) -> List[str]:
        return list(cls.TEMPLATES)

    @classmethod
    def get_template_path(cls, template_name: str) -> Path:
        path = TEMPLATE_DIR / template_name
        if not path.is_dir():
            raise ValueError(f"Template '{template_name}' not found. Available: {cls.TEMPLATES}")
        return path

    @classmethod
    def render_template(cls, template_name: str, context: Dict[str, Any], destination_dir: Path) -> List[Path]:
        """
        Renders an entire template directory into destination_dir with context variables.

        Returns:
            List of generated file Paths.
        """
        src_dir = cls.get_template_path(template_name)
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        created_files: List[Path] = []

        for root, dirs, files in os.walk(src_dir):
            rel_root = Path(root).relative_to(src_dir)
            target_sub_dir = destination_dir / rel_root
            target_sub_dir.mkdir(parents=True, exist_ok=True)

            for file_name in files:
                src_file = Path(root) / file_name

                # Preserve .desktop.template suffix because CMake generate_desktop expects it
                if file_name.endswith(".desktop.template"):
                    dest_file_name = file_name
                elif file_name.endswith(".template"):
                    dest_file_name = file_name[:-9]
                else:
                    dest_file_name = file_name

                # If destination file name has variable like {{ app_name }}
                dest_file_name = render_template_string(dest_file_name, context)
                dest_file = target_sub_dir / dest_file_name

                with open(src_file, "r", encoding="utf-8") as f:
                    content = f.read()

                rendered_content = render_template_string(content, context)

                with open(dest_file, "w", encoding="utf-8") as f:
                    f.write(rendered_content)

                # Preserve execution permissions if source has them or is script
                if os.access(src_file, os.X_OK) or dest_file_name.endswith(".sh") or dest_file_name.endswith(".py"):
                    dest_file.chmod(0o755)

                created_files.append(dest_file)

        return created_files
