import html
import re
from urllib.parse import urlsplit

from django import template
from django.utils.safestring import mark_safe


register = template.Library()

LINK_PATTERN = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
ITALIC_PATTERN = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
HEADING_PATTERN = re.compile(r"^(#{2,4})\s+(.+)$")
UNORDERED_ITEM_PATTERN = re.compile(r"^\s*[-+]\s+(.+)$")
ORDERED_ITEM_PATTERN = re.compile(r"^\s*\d+\.\s+(.+)$")
SAFE_LINK_SCHEMES = {"http", "https", "mailto"}


def _render_emphasis(value):
    escaped = html.escape(value)
    escaped = BOLD_PATTERN.sub(r"<strong>\1</strong>", escaped)
    return ITALIC_PATTERN.sub(r"<em>\1</em>", escaped)


def _render_inline(value):
    rendered = []
    cursor = 0

    for match in LINK_PATTERN.finditer(value):
        rendered.append(_render_emphasis(value[cursor:match.start()]))
        label, url = match.groups()
        scheme = urlsplit(url).scheme.lower()

        if scheme in SAFE_LINK_SCHEMES:
            target = ' target="_blank"' if scheme in {"http", "https"} else ""
            rendered.append(
                f'<a href="{html.escape(url, quote=True)}"{target} '
                f'rel="noopener noreferrer">{_render_emphasis(label)}</a>'
            )
        else:
            rendered.append(_render_emphasis(match.group(0)))

        cursor = match.end()

    rendered.append(_render_emphasis(value[cursor:]))
    return "".join(rendered)


@register.filter(name="render_blog_content")
def render_blog_content(value):
    """Render the editor's small Markdown subset while escaping all raw HTML."""
    lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output = []
    paragraph = []
    list_type = None
    list_items = []

    def flush_paragraph():
        if paragraph:
            output.append(f"<p>{'<br>'.join(_render_inline(line) for line in paragraph)}</p>")
            paragraph.clear()

    def flush_list():
        nonlocal list_type
        if list_type:
            items = "".join(f"<li>{_render_inline(item)}</li>" for item in list_items)
            output.append(f"<{list_type}>{items}</{list_type}>")
            list_items.clear()
            list_type = None

    for line in lines:
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        heading = HEADING_PATTERN.match(line)
        unordered_item = UNORDERED_ITEM_PATTERN.match(line)
        ordered_item = ORDERED_ITEM_PATTERN.match(line)

        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{_render_inline(heading.group(2))}</h{level}>")
        elif unordered_item or ordered_item:
            flush_paragraph()
            next_list_type = "ul" if unordered_item else "ol"
            if list_type and list_type != next_list_type:
                flush_list()
            list_type = next_list_type
            list_items.append((unordered_item or ordered_item).group(1))
        elif line.lstrip().startswith(">"):
            flush_paragraph()
            flush_list()
            quote = line.lstrip()[1:].lstrip()
            output.append(f"<blockquote>{_render_inline(quote)}</blockquote>")
        else:
            flush_list()
            paragraph.append(line)

    flush_paragraph()
    flush_list()
    return mark_safe("\n".join(output))
