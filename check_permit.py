import asyncio
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

ADDRESS = "1138 Dent Terrace"
PORTAL_URL = "https://permits.milton.ca/citizenportal/app/public-search"


async def check_permit():
    print(f"[{datetime.now()}] Starting permit check for: {ADDRESS}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("Loading portal...")
            await page.goto(PORTAL_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)

            # Screenshot immediately so we can see what loaded
            await page.screenshot(path="permit_check_screenshot.png", full_page=True)
            print("Initial screenshot saved.")

            # Print all input elements found on page
            inputs = await page.query_selector_all("input")
            print(f"Found {len(inputs)} input elements:")
            for i, inp in enumerate(inputs):
                placeholder = await inp.get_attribute("placeholder")
                input_type = await inp.get_attribute("type")
                input_id = await inp.get_attribute("id")
                input_class = await inp.get_attribute("class")
                print(f"  Input {i}: type={input_type}, id={input_id}, placeholder={placeholder}, class={input_class}")

            # Print page title and URL
            print(f"Page title: {await page.title()}")
            print(f"Page URL: {page.url}")

            # Print visible text
            body_text = await page.inner_text("body")
            print("--- BODY TEXT (first 2000 chars) ---")
            print(body_text[:2000])
            print("--- END ---")

            with open("permit_result.txt", "w") as f:
                f.write("DIAGNOSTIC_RUN")

        except Exception as e:
            print(f"ERROR: {e}")
            await page.screenshot(path="permit_check_screenshot.png", full_page=True)
            with open("permit_result.txt", "w") as f:
                f.write(f"ERROR\n{e}")
            sys.exit(1)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(check_permit())
