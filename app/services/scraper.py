from __future__ import annotations

import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, Tag

from app.services.importer import calculate_lead_score, map_columns

USER_AGENT = "BaxeoTanTradeResearchBot/1.0 (+public-buyer-research)"


@dataclass
class ScrapeResult:
    leads: list[dict[str, str | float | None]]
    warnings: list[str]


def scrape_public_buyers(
    url: str,
    *,
    render_javascript: bool = False,
    max_results: int = 50,
    item_selector: str = "article, li, .company, .company-card, .listing, [class*=company], [class*=listing]",
    name_selector: str = "h1, h2, h3, h4, .name, .company-name, [class*=title]",
) -> ScrapeResult:
    validate_public_url(url)
    if not allowed_by_robots(url):
        raise ValueError("This site's robots.txt does not allow automated access")
    html = fetch_page(url, render_javascript=render_javascript)
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(item_selector)
    if not items:
        items = [heading for heading in soup.select(name_selector) if isinstance(heading, Tag)]

    leads: list[dict[str, str | float | None]] = []
    seen: set[str] = set()
    for item in items[:max_results]:
        lead = extract_lead(item, url, name_selector)
        if not lead or lead["name"] in seen:
            continue
        seen.add(str(lead["name"]))
        leads.append(lead)
        time.sleep(0.1)
    warnings = [] if leads else ["No buyer cards were found. Try a narrower item selector or enable JavaScript rendering."]
    return ScrapeResult(leads=leads, warnings=warnings)


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public http(s) URLs are supported")
    addresses = socket.getaddrinfo(parsed.hostname, None)
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Private and local network URLs are not allowed")


def allowed_by_robots(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser(robots_url)
    try:
        response = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if response.status_code == 404:
            return True
        if not response.ok:
            return False
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except requests.RequestException as error:
        raise ValueError(f"Could not verify robots.txt: {error}") from error


def fetch_page(url: str, *, render_javascript: bool) -> str:
    if render_javascript:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--user-agent={USER_AGENT}")
            driver = webdriver.Chrome(options=options)
            try:
                driver.get(url)
                return driver.page_source
            finally:
                driver.quit()
        except Exception as error:
            raise ValueError(f"JavaScript rendering failed: {error}") from error
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    return response.text


def extract_lead(item: Tag, source_url: str, name_selector: str) -> dict[str, str | float | None] | None:
    name_node = item.select_one(name_selector) if item.name != "h1" else item
    name = clean_text(name_node.get_text(" ", strip=True) if name_node else item.get_text(" ", strip=True))
    if not name or len(name) < 3 or len(name) > 180:
        return None
    text = item.get_text(" ", strip=True)
    email_match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    phone_match = re.search(r"(?:\+?\d[\d ()-]{7,}\d)", text)
    link = item.select_one("a[href]")
    website = urljoin(source_url, link["href"]) if link and link.get("href") else source_url
    raw = {"name": name, "website": website, "email": email_match.group(0) if email_match else None, "phone": phone_match.group(0) if phone_match else None}
    mapping = map_columns(raw.keys())
    raw["lead_score"] = calculate_lead_score(raw, mapping)
    raw["source_url"] = source_url
    return raw


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -|\t\n")