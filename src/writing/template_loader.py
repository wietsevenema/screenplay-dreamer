"""Template loading and management functionality."""

from pathlib import Path
from typing import Dict, Optional, Any
from jinja2 import Template, Environment, FileSystemLoader


class TemplateLoader:
    """Handles loading and caching of prompt templates."""

    def __init__(self, root_dir: str = "prompts"):
        """Initialize with root prompts directory."""
        self.root_dir = Path(root_dir)
        self._cache: Dict[str, Template] = {}
        self.env = Environment(loader=FileSystemLoader(str(self.root_dir)))

    def get_template(
        self, template_path: str, use_cache: bool = True, **kwargs: Any
    ) -> Optional[str]:
        """
        Load and render a template from the given path relative to root_dir.

        Args:
            template_path: Path relative to root_dir (e.g. "system/architect.txt")
            use_cache: Whether to use cached template if available
            **kwargs: Variables to render in the template

        Returns:
            Rendered template string if found, None if not found
        """
        if use_cache and template_path in self._cache:
            return self._cache[template_path].render(**kwargs)

        try:
            template = self.env.get_template(template_path)
            if use_cache:
                self._cache[template_path] = template
            return template.render(**kwargs)
        except Exception:
            return None

    def clear_cache(self):
        """Clear the template cache."""
        self._cache.clear()
