#!/usr/bin/env python3
"""Inspect HTML structure of Vietnamese news sites."""
import requests
from bs4 import BeautifulSoup

def inspect_cafef():
    """Inspect CafeF structure."""
    url = "https://cafef.vn/tai-chinh-ngan-hang.chn"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")
    
    print("=== CAFEF ===")
    # Look for article titles
    for selector in ["h3.title", "h3", ".title", "a.title"]:
        items = soup.select(selector)[:3]
        if items:
            print(f"Selector '{selector}': {len(items)} items found")
            for item in items:
                text = item.get_text(strip=True)
                href = item.get("href") or item.find("a", href=True)
                if isinstance(href, str) and href:
                    print(f"  - {text[:50]}... -> {href}")
                elif href:
                    print(f"  - {text[:50]}... -> {href.get('href', 'no href')}")
    
    # Look for images
    imgs = soup.select("img")[:5]
    for img in imgs:
        src = img.get("data-src") or img.get("src")
        if src:
            print(f"  Image: {src}")

def inspect_tuoitre():
    """Inspect Tuoi Tre structure."""
    url = "https://tuoitre.vn/the-thao.htm"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")
    
    print("\n=== TUOI TRE ===")
    for selector in ["h3.title", "h3", ".title", "a.title"]:
        items = soup.select(selector)[:3]
        if items:
            print(f"Selector '{selector}': {len(items)} items found")
            for item in items:
                text = item.get_text(strip=True)
                href = item.get("href") or item.find("a", href=True)
                if isinstance(href, str) and href:
                    print(f"  - {text[:50]}... -> {href}")
                elif href:
                    print(f"  - {text[:50]}... -> {href.get('href', 'no href')}")
    
    imgs = soup.select("img")[:5]
    for img in imgs:
        src = img.get("data-src") or img.get("src")
        if src:
            print(f"  Image: {src}")

def inspect_vnexpress():
    """Inspect VNExpress structure."""
    url = "https://vnexpress.net/the-thao"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")
    
    print("\n=== VNEXPRESS ===")
    items = soup.select("h3.title-news a")[:3]
    for item in items:
        print(f"  - {item.get_text(strip=True)[:50]}... -> {item.get('href')}")
    
    imgs = soup.select("img")[:5]
    for img in imgs:
        src = img.get("data-src") or img.get("src")
        if src:
            print(f"  Image: {src}")

if __name__ == "__main__":
    inspect_vnexpress()
    inspect_cafef()
    inspect_tuoitre()