#!/usr/bin/env python3
"""
Simple validation script to check that TOC links match actual chapter headings
in consolidated markdown files.

Usage: python3 validate_toc_links.py [markdown_file]
"""

import re
import sys
from pathlib import Path


def extract_toc_links(content: str) -> list:
    """Extract all TOC links from the markdown content."""
    toc_links = []
    
    # Find the Table of Contents section
    toc_pattern = r'## Table of Contents\s*\n\n(.*?)\n\n---'
    toc_match = re.search(toc_pattern, content, re.DOTALL)
    
    if not toc_match:
        return toc_links
    
    toc_section = toc_match.group(1)
    
    # Extract all links from TOC section
    link_pattern = r'\[([^\]]+)\]\(#([^)]+)\)'
    links = re.findall(link_pattern, toc_section)
    
    for title, anchor in links:
        toc_links.append({
            'title': title,
            'anchor': anchor,
            'full_link': f'[{title}](#{anchor})'
        })
    
    return toc_links


def extract_chapter_headings(content: str) -> list:
    """Extract all chapter headings and generate their expected anchor slugs."""
    headings = []
    
    # Find all chapter headings (# Chapter X: Title and # Global Summary)
    chapter_pattern = r'^# (Chapter \d+: .+|Global Summary)$'
    matches = re.finditer(chapter_pattern, content, re.MULTILINE)
    
    for match in matches:
        heading_text = match.group(1)
        
        # Generate slug using same logic as _generate_markdown_slug
        slug = heading_text.lower()
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        
        headings.append({
            'text': heading_text,
            'expected_anchor': slug,
            'line': match.start()
        })
    
    return headings


def validate_toc_links(markdown_file: Path) -> bool:
    """
    Validate that all TOC links have matching chapter headings.
    
    Returns:
        True if all links are valid, False otherwise
    """
    try:
        content = markdown_file.read_text(encoding='utf-8')
    except Exception as e:
        print(f"❌ Error reading {markdown_file}: {e}")
        return False
    
    print(f"🔍 Validating TOC links in: {markdown_file}")
    print()
    
    # Extract TOC links and chapter headings
    toc_links = extract_toc_links(content)
    chapter_headings = extract_chapter_headings(content)
    
    if not toc_links:
        print("⚠️  No TOC links found")
        return True
    
    if not chapter_headings:
        print("⚠️  No chapter headings found")
        return True
    
    print(f"📋 Found {len(toc_links)} TOC links and {len(chapter_headings)} chapter headings")
    print()
    
    # Create a map of expected anchors to headings
    heading_map = {h['expected_anchor']: h for h in chapter_headings}
    
    # Validate each TOC link
    all_valid = True
    
    for i, link in enumerate(toc_links, 1):
        print(f"{i}. {link['full_link']}")
        
        if link['anchor'] in heading_map:
            heading = heading_map[link['anchor']]
            print(f"   ✅ Matches: # {heading['text']}")
        else:
            print(f"   ❌ No matching heading found for anchor: #{link['anchor']}")
            all_valid = False
        
        print()
    
    # Check for any headings without TOC links
    toc_anchors = {link['anchor'] for link in toc_links}
    orphaned_headings = [h for h in chapter_headings if h['expected_anchor'] not in toc_anchors]
    
    if orphaned_headings:
        print("🔍 Headings without TOC links:")
        for heading in orphaned_headings:
            print(f"   ⚠️  # {heading['text']} (expected anchor: #{heading['expected_anchor']})")
        print()
    
    # Summary
    if all_valid:
        print("🎉 All TOC links are valid!")
    else:
        print("❌ Some TOC links are broken!")
    
    return all_valid


def main():
    """Main script entry point."""
    if len(sys.argv) > 1:
        markdown_file = Path(sys.argv[1])
    else:
        # Default to most recent consolidated file in outputs
        outputs_dir = Path("outputs")
        if not outputs_dir.exists():
            print("❌ No outputs directory found. Run the summarizer first.")
            sys.exit(1)
        
        consolidated_files = list(outputs_dir.glob("*_consolidated.md"))
        if not consolidated_files:
            print("❌ No consolidated markdown files found in outputs/")
            sys.exit(1)
        
        # Use the most recent file
        markdown_file = max(consolidated_files, key=lambda f: f.stat().st_mtime)
    
    if not markdown_file.exists():
        print(f"❌ File not found: {markdown_file}")
        sys.exit(1)
    
    success = validate_toc_links(markdown_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
