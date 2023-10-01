import re
from playwright.sync_api import sync_playwright

# with sync_playwright() as p:
#     browser = p.chromium.launch(headless=False, slow_mo=1000)
#     page = browser.new_page()
#     page.goto('https://google.com')
#     page.screenshot(path="ex.png")
#     print(page.title())

playwright = sync_playwright().start()
# Use playwright.chromium, playwright.firefox or playwright.webkit
# Pass headless=False to launch() to see the browser UI
browser = playwright.chromium.launch(headless=False, slow_mo=1000)
page = browser.new_page()
page.goto("https://playwright.dev/")

# browser.close()
# playwright.stop()
