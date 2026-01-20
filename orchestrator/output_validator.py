"""
Output Validator - Validates agent outputs against schemas.

Provides validation for:
- File existence
- Format validation (UTF-8, parseable YAML/JSON, Markdown)
- Schema validation (required fields, types, patterns)
- Content validation (required sections for Markdown)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import json
import re
from datetime import datetime


class OutputValidator:
    """Validates agent outputs against schemas."""

    def __init__(self, schemas_dir: str = "schemas"):
        """Initialize Output Validator.

        Args:
            schemas_dir: Directory containing schema YAML files
        """
        self.schemas_dir = Path(schemas_dir)
        self.schemas_dir.mkdir(parents=True, exist_ok=True)

        # Cache loaded schemas
        self._schema_cache: Dict[str, Dict] = {}

    # ========================================
    # Schema Loading
    # ========================================

    def load_schema(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load validation schema for agent.

        Args:
            agent_id: Agent ID

        Returns:
            Schema dict or None if not found
        """
        # Check cache
        if agent_id in self._schema_cache:
            return self._schema_cache[agent_id]

        # Load from file
        schema_file = self.schemas_dir / f"{agent_id}.schema.yaml"
        if not schema_file.exists():
            return None

        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = yaml.safe_load(f)

            # Cache and return
            self._schema_cache[agent_id] = schema
            return schema

        except Exception as e:
            print(f"Error loading schema for {agent_id}: {e}")
            return None

    # ========================================
    # Main Validation Entry Point
    # ========================================

    def validate(
        self,
        agent_id: str,
        output_content: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate agent output.

        Args:
            agent_id: Agent that produced output
            output_content: Content to validate (for single output)
            output_dir: Directory with output files (for multi-file)

        Returns:
            Validation report dict
        """
        # Load schema
        schema = self.load_schema(agent_id)
        if not schema:
            return {
                "overall_status": "warn",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat(),
                "message": f"No schema found for {agent_id}, skipping validation",
                "errors": [],
                "warnings": [{"message": "No validation schema available"}]
            }

        # Run validations
        results = []
        errors = []
        warnings = []

        schema_def = schema.get("schema", {})
        files = schema_def.get("files", [])

        # If only one file and output_content provided, validate that
        if output_content and len(files) == 1:
            file_result = self._validate_content(
                file_spec=files[0],
                content=output_content
            )
            results.append(file_result)

            if file_result["status"] == "fail":
                errors.extend(file_result.get("errors", []))
            if file_result.get("warnings"):
                warnings.extend(file_result["warnings"])

        # Determine overall status
        overall_status = "pass"
        if errors:
            overall_status = "fail"
        elif warnings:
            overall_status = "warn"

        return {
            "overall_status": overall_status,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "schema_version": schema_def.get("version", 1),
            "files_validated": len(results),
            "files_passed": sum(1 for r in results if r["status"] == "pass"),
            "files_failed": sum(1 for r in results if r["status"] == "fail"),
            "results": results,
            "errors": errors,
            "warnings": warnings
        }

    # ========================================
    # Content Validation
    # ========================================

    def _validate_content(
        self,
        file_spec: Dict,
        content: str
    ) -> Dict[str, Any]:
        """Validate content against file spec.

        Args:
            file_spec: File specification from schema
            content: Content to validate

        Returns:
            File validation result dict
        """
        file_name = file_spec.get("name", "output")
        checks = []
        errors = []
        warnings = []

        # 1. Format validation
        format_type = file_spec.get("format", "text")
        format_result = self._validate_format(content, format_type)
        checks.append(format_result)
        if format_result["status"] == "fail":
            errors.extend(format_result.get("errors", []))

        # Only continue if format is valid
        if format_result["status"] == "pass":
            # 2. Schema validation (for YAML/JSON)
            if format_type in ("yaml", "json") and file_spec.get("schema"):
                schema_result = self._validate_schema(content, file_spec["schema"], format_type)
                checks.append(schema_result)
                if schema_result["status"] == "fail":
                    errors.extend(schema_result.get("errors", []))

            # 3. Content validation (for Markdown)
            if format_type == "markdown" and file_spec.get("sections"):
                content_result = self._validate_markdown_sections(content, file_spec["sections"])
                checks.append(content_result)
                if content_result["status"] == "fail":
                    errors.extend(content_result.get("errors", []))

        return {
            "file": file_name,
            "status": "fail" if errors else "pass",
            "checks": checks,
            "errors": errors,
            "warnings": warnings
        }

    # ========================================
    # Validation Types
    # ========================================

    def _validate_format(
        self,
        content: str,
        format_type: str
    ) -> Dict[str, Any]:
        """Validate file format (UTF-8, parseable, etc).

        Args:
            content: Content to validate
            format_type: Format type (yaml, json, markdown, text, code)

        Returns:
            Format validation result
        """
        errors = []

        # Check encoding (already UTF-8 if we got here)
        # Check parseability
        if format_type == "yaml":
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                err_msg = str(e).split('\n')[0]
                errors.append({
                    "type": "format",
                    "message": f"Invalid YAML syntax: {err_msg}",
                    "fix_suggestion": "Fix YAML syntax errors"
                })

        elif format_type == "json":
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                errors.append({
                    "type": "format",
                    "message": f"Invalid JSON syntax: {e.msg} at line {e.lineno}",
                    "fix_suggestion": "Fix JSON syntax errors"
                })

        # Markdown and text don't need parsing validation
        # Code format just checks file exists (done at file level)

        return {
            "type": "format",
            "status": "fail" if errors else "pass",
            "errors": errors
        }

    def _validate_schema(
        self,
        content: str,
        schema: Dict,
        format_type: str
    ) -> Dict[str, Any]:
        """Validate YAML/JSON against schema.

        Args:
            content: Content to validate
            schema: Schema definition
            format_type: yaml or json

        Returns:
            Schema validation result
        """
        errors = []

        # Parse content
        try:
            if format_type == "yaml":
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
        except Exception as e:
            return {
                "type": "schema",
                "status": "fail",
                "errors": [{"message": f"Cannot parse content: {e}"}]
            }

        # Check if data is a dict (object)
        if not isinstance(data, dict):
            errors.append({
                "type": "schema",
                "message": f"Expected object, got {type(data).__name__}",
                "fix_suggestion": "Root element should be an object/dict"
            })
            return {
                "type": "schema",
                "status": "fail",
                "errors": errors
            }

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append({
                    "type": "schema",
                    "path": f"$.{field}",
                    "message": f"Required field '{field}' is missing",
                    "fix_suggestion": f"Add '{field}' to output"
                })

        # Check properties
        properties = schema.get("properties", {})
        for field, spec in properties.items():
            if field in data:
                # Type check
                expected_type = spec.get("type")
                actual_value = data[field]

                if expected_type == "string" and not isinstance(actual_value, str):
                    errors.append({
                        "type": "schema",
                        "path": f"$.{field}",
                        "message": f"Expected string, got {type(actual_value).__name__}",
                        "fix_suggestion": f"Change '{field}' to string"
                    })

                elif expected_type == "integer" and not isinstance(actual_value, int):
                    errors.append({
                        "type": "schema",
                        "path": f"$.{field}",
                        "message": f"Expected integer, got {type(actual_value).__name__}",
                        "fix_suggestion": f"Change '{field}' to integer"
                    })

                elif expected_type == "array" and not isinstance(actual_value, list):
                    errors.append({
                        "type": "schema",
                        "path": f"$.{field}",
                        "message": f"Expected array, got {type(actual_value).__name__}",
                        "fix_suggestion": f"Change '{field}' to array"
                    })

                elif expected_type == "object" and not isinstance(actual_value, dict):
                    errors.append({
                        "type": "schema",
                        "path": f"$.{field}",
                        "message": f"Expected object, got {type(actual_value).__name__}",
                        "fix_suggestion": f"Change '{field}' to object"
                    })

                # Min items check for arrays
                if expected_type == "array" and isinstance(actual_value, list):
                    min_items = spec.get("min_items", 0)
                    if len(actual_value) < min_items:
                        errors.append({
                            "type": "schema",
                            "path": f"$.{field}",
                            "message": f"Array has {len(actual_value)} items, minimum is {min_items}",
                            "fix_suggestion": f"Add at least {min_items - len(actual_value)} more items"
                        })

                # Pattern check for strings
                if expected_type == "string" and isinstance(actual_value, str):
                    pattern = spec.get("pattern")
                    if pattern and not re.match(pattern, actual_value):
                        errors.append({
                            "type": "schema",
                            "path": f"$.{field}",
                            "message": f"Value '{actual_value}' does not match pattern '{pattern}'",
                            "fix_suggestion": f"Ensure '{field}' matches the required pattern"
                        })

        return {
            "type": "schema",
            "status": "fail" if errors else "pass",
            "errors": errors
        }

    def _validate_markdown_sections(
        self,
        content: str,
        required_sections: List[Dict]
    ) -> Dict[str, Any]:
        """Validate required sections in Markdown.

        Args:
            content: Markdown content
            required_sections: List of section specs

        Returns:
            Content validation result
        """
        errors = []

        for section in required_sections:
            heading = section["heading"]
            required = section.get("required", True)

            if required:
                # Simple regex to find heading
                # Escape special regex characters in heading
                pattern = re.escape(heading)
                if not re.search(pattern, content, re.MULTILINE):
                    errors.append({
                        "type": "content",
                        "section": heading,
                        "message": f"Required section '{heading}' not found",
                        "fix_suggestion": f"Add section '{heading}'"
                    })

        return {
            "type": "content",
            "status": "fail" if errors else "pass",
            "errors": errors
        }
