"""Jinja2 filters for HTML template rendering.

These filters are used in article.html.j2 to format CEO3 article data.
"""

import re
from datetime import datetime


def format_date(date_string: str) -> str:
    """Format a CEO3 datetime string as a human-readable date.

    Args:
        date_string: Date string in format "YYYY-MM-DD HH:MM:SS"

    Returns:
        Formatted date string like "January 29, 2026"

    Examples:
        >>> format_date("2026-01-29 06:51:50")
        'January 29, 2026'
    """
    if not date_string:
        return ""
    try:
        dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return date_string


def format_authors(authors: list) -> str:
    """Format a list of CEO3 author objects as a comma-separated string.

    Args:
        authors: List of author dicts/objects with 'name' attribute

    Returns:
        Comma-separated author names

    Examples:
        >>> format_authors([{"name": "John"}, {"name": "Jane"}])
        'John, Jane'
    """
    if not authors:
        return ""
    names = []
    for author in authors:
        if isinstance(author, dict):
            name = author.get("name", "")
        else:
            name = getattr(author, "name", "")
        if name:
            names.append(name)
    return ", ".join(names)


def parse_tags(tags: list) -> list[str]:
    """Extract tag names from a list of CEO3 tag objects.

    Args:
        tags: List of tag dicts/objects with 'name' attribute

    Returns:
        List of tag name strings

    Examples:
        >>> parse_tags([{"name": "news"}, {"name": "top"}])
        ['news', 'top']
    """
    if not tags:
        return []
    names = []
    for tag in tags:
        if isinstance(tag, dict):
            name = tag.get("name", "")
        else:
            name = getattr(tag, "name", "")
        if name:
            names.append(name)
    return names


def parse_media_caption(content: str) -> dict:
    """Parse dominant media content to extract caption and credit.

    CEO3 dominant media content uses h5 for caption and h6 for credit:
    <h5>Caption text</h5><h6>Credit / Source</h6>

    Args:
        content: HTML content from dominantMedia.content field

    Returns:
        Dict with 'caption' and 'credit' keys (may be empty strings)

    Examples:
        >>> parse_media_caption('<h5>A photo.</h5><h6>John Doe / Daily Prince</h6>')
        {'caption': 'A photo.', 'credit': 'John Doe / Daily Prince'}
    """
    result = {"caption": "", "credit": ""}
    if not content:
        return result

    # Extract caption from h5 tag
    caption_match = re.search(r"<h5[^>]*>(.*?)</h5>", content, re.DOTALL | re.IGNORECASE)
    if caption_match:
        result["caption"] = caption_match.group(1).strip()

    # Extract credit from h6 tag
    credit_match = re.search(r"<h6[^>]*>(.*?)</h6>", content, re.DOTALL | re.IGNORECASE)
    if credit_match:
        result["credit"] = credit_match.group(1).strip()

    return result


def clean_content(html: str) -> str:
    """Sanitize HTML content by removing scripts and interactive embeds.

    Removes:
    - <script> tags and their content
    - <iframe> tags
    - <noscript> tags and their content

    This filter does NOT replace Flourish embeds - that's handled separately
    by the HTMLTransformer which replaces them with local chart images.

    Args:
        html: Raw HTML content from CEO3

    Returns:
        Sanitized HTML safe for static rendering

    Examples:
        >>> clean_content('<p>Hello</p><script>alert("x")</script>')
        '<p>Hello</p>'
    """
    if not html:
        return ""

    # Remove script tags and their content
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove iframe tags
    html = re.sub(r"<iframe[^>]*>.*?</iframe>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<iframe[^>]*/?>", "", html, flags=re.IGNORECASE)

    # Remove noscript tags and their content
    html = re.sub(r"<noscript[^>]*>.*?</noscript>", "", html, flags=re.DOTALL | re.IGNORECASE)

    return html.strip()


# Registry of all filters for easy registration with Jinja2
FILTERS = {
    "format_date": format_date,
    "format_authors": format_authors,
    "parse_tags": parse_tags,
    "parse_media_caption": parse_media_caption,
    "clean_content": clean_content,
}
