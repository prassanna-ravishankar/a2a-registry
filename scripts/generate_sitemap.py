#!/usr/bin/env python3
"""
Generate sitemap.xml from registry.json
This script should be run after building the website to update the sitemap with current data.
"""

import json
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


def generate_sitemap(registry_path: Path, output_path: Path) -> None:
    """Generate sitemap.xml from registry.json"""

    # Read registry data
    with open(registry_path) as f:
        registry_data = json.load(f)

    agents = registry_data.get("agents", [])

    # Get current date in ISO format
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Create XML structure
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    urlset.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    urlset.set("xsi:schemaLocation",
               "http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd")

    # Main page
    url = SubElement(urlset, "url")
    SubElement(url, "loc").text = "https://www.a2aregistry.org/"
    SubElement(url, "lastmod").text = current_date
    SubElement(url, "changefreq").text = "daily"
    SubElement(url, "priority").text = "1.0"

    # Registry JSON API
    url = SubElement(urlset, "url")
    SubElement(url, "loc").text = "https://www.a2aregistry.org/registry.json"
    SubElement(url, "lastmod").text = current_date
    SubElement(url, "changefreq").text = "daily"
    SubElement(url, "priority").text = "0.8"

    # Example agent (if exists)
    url = SubElement(urlset, "url")
    SubElement(url, "loc").text = "https://hello.a2aregistry.org/"
    SubElement(url, "lastmod").text = current_date
    SubElement(url, "changefreq").text = "weekly"
    SubElement(url, "priority").text = "0.7"

    # Pretty print XML
    xml_str = minidom.parseString(tostring(urlset, encoding="unicode")).toprettyxml(indent="  ")
    # Remove extra blank lines
    xml_str = "\n".join([line for line in xml_str.split("\n") if line.strip()])

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(xml_str)

    print(f"✓ Generated sitemap with {len(agents)} agents")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    # Paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    registry_path = repo_root / "docs" / "registry.json"
    output_path = repo_root / "docs" / "sitemap.xml"

    # Check if registry exists
    if not registry_path.exists():
        print(f"Warning: {registry_path} not found. Using fallback sitemap generation.")
        # Fallback: use website/public/sitemap.xml template
        registry_path = repo_root / "website" / "public" / "registry.json"
        output_path = repo_root / "website" / "public" / "sitemap.xml"

    generate_sitemap(registry_path, output_path)
