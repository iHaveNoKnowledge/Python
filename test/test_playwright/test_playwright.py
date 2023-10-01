from playwright.sync import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()