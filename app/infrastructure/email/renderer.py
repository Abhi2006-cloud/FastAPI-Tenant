"""Jinja2 HTML & Plain Text Email Template Renderer."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def html_to_plain_text(html_content: str) -> str:
    """Extract clean plain text from HTML content for email fallback."""
    # Remove style and script tags
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    # Convert <br> and <p> to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    # Extract links text and href
    text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r"\2 (\1)", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return text


class EmailRenderer:
    """Renders HTML and Plain Text versions of email templates using Jinja2."""

    def __init__(self, template_dir: Path | None = None) -> None:
        if template_dir is None:
            # Default to templates/emails relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            template_dir = project_root / "templates" / "emails"

        self.template_dir = template_dir
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, template_name: str, context: Dict[str, Any] | None = None) -> Tuple[str, str]:
        """Render template with context.

        Returns tuple of (html_content, text_content).
        """
        settings = get_settings()

        # Merge base default context variables
        full_context: Dict[str, Any] = {
            "company_name": settings.app_name,
            "support_email": settings.email_from_address,
            "frontend_url": settings.frontend_url,
            "from_name": settings.email_from_name,
            "from_address": settings.email_from_address,
        }
        if context:
            full_context.update(context)

        # Ensure .html extension
        filename = template_name if template_name.endswith(".html") else f"{template_name}.html"

        try:
            template = self.env.get_template(filename)
            html_content = template.render(**full_context)
            plain_text = html_to_plain_text(html_content)
            return html_content, plain_text
        except Exception as exc:
            logger.error("Failed to render email template '%s': %s", filename, exc)
            raise RuntimeError(f"Template rendering failed for '{filename}': {exc}") from exc


# Default renderer instance
email_renderer = EmailRenderer()
