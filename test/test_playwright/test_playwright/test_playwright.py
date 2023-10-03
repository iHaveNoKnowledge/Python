import asyncio
from playwright.async_api import async_playwright

async def main():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    page = await browser.new_page()
    await page.goto("https://playwright.dev/")
    await page.screenshot(path="example.png")
    await browser.close()
    await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
