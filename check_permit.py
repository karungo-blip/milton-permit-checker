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
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("Loading portal...")
            await page.goto(PORTAL_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            await page.screenshot(path="permit_check_screenshot.png")
            print("Page loaded.")

            # The search box has placeholder "Address" and is inside the ESRI map
            print("Finding address search box...")
            search_input = await page.wait_for_selector(
                'input[placeholder="Address"]',
                timeout=20000
            )
            await search_input.click()
            await page.wait_for_timeout(500)
            await search_input.type(ADDRESS, delay=150)
            print(f"Typed: {ADDRESS}")
            await page.wait_for_timeout(3000)

            # Screenshot after typing
            await page.screenshot(path="permit_check_screenshot.png")

            # Click "Zoom to" from the autocomplete suggestions
            print("Looking for Zoom to / suggestion dropdown...")
            zoom_to = await page.wait_for_selector(
                'text="Zoom to", [class*="suggestion"], [class*="autocomplete"] li, [class*="search-result"]',
                timeout=10000
            )
            await zoom_to.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")
            print("Clicked Zoom to.")

            # Click the blue circle/dot on the map
            print("Looking for blue circle on map...")
            blue_dot = await page.wait_for_selector(
                'circle, [class*="esri-icon"], svg circle, [class*="map-point"], canvas',
                timeout=15000
            )
            await blue_dot.click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path="permit_check_screenshot.png")
            print("Clicked blue dot.")

            # Click "Select property"
            print("Looking for Select property button...")
            select_btn = await page.wait_for_selector(
                'text="Select property", button:has-text("Select property"), a:has-text("Select property")',
                timeout=10000
            )
            await select_btn.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")
            print("Clicked Select property.")

            # Scroll down to see permits
            await page.keyboard.press("End")
            await page.wait_for_timeout(2000)

            # Click the + expand button
            print("Looking for expand/+ button...")
            try:
                plus_btn = await page.wait_for_selector(
                    'button:has-text("+"), [class*="expand"], [aria-expanded="false"], [class*="accordion"]',
                    timeout=10000
                )
                await plus_btn.click()
                await page.wait_for_timeout(2000)
            except:
                print("No + button found, continuing...")

            await page.screenshot(path="permit_check_screenshot.png")

            # Get all page text
            page_text = await page.inner_text("body")
            print("--- PAGE TEXT ---")
            print(page_text[:3000])
            print("--- END ---")

            issued_keywords = ["issued", "permit issued", "approved", "active"]
            found = [kw for kw in issued_keywords if kw.lower() in page_text.lower()]

            if found:
                print(f"PERMIT_FOUND: {', '.join(found)}")
                with open("permit_result.txt", "w") as f:
                    f.write(f"FOUND\nKeywords: {', '.join(found)}\n\n{page_text[:2000]}")
            else:
                print("No issued permit detected yet.")
                with open("permit_result.txt", "w") as f:
                    f.write("NOT_FOUND")

        except PlaywrightTimeout as e:
            print(f"ERROR: Timeout - {e}")
            await page.screenshot(path="permit_check_screenshot.png")
            with open("permit_result.txt", "w") as f:
                f.write(f"ERROR\nTimeout: {e}")
            sys.exit(1)

        except Exception as e:
            print(f"ERROR: {e}")
            await page.screenshot(path="permit_check_screenshot.png")
            with open("permit_result.txt", "w") as f:
                f.write(f"ERROR\n{e}")
            sys.exit(1)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(check_permit())
