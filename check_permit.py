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
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            print("Loading portal...")
            await page.goto(PORTAL_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            print("Typing address...")
            search_input = await page.wait_for_selector(
                'input[placeholder*="Search"], input[type="search"], input[placeholder*="address"], input[placeholder*="Address"]',
                timeout=20000
            )
            await search_input.click()
            await search_input.fill("")
            await search_input.type(ADDRESS, delay=100)
            await page.wait_for_timeout(2000)

            print("Waiting for map marker (blue dot)...")
            marker = await page.wait_for_selector(
                '.leaflet-marker-icon, [class*="marker"], [class*="pin"], svg circle, canvas',
                timeout=20000
            )
            await marker.click()
            await page.wait_for_timeout(2000)

            print("Looking for Select Property option...")
            select_btn = await page.wait_for_selector(
                'button:has-text("Select"), a:has-text("Select"), [class*="select-property"]',
                timeout=10000
            )
            await select_btn.click()
            await page.wait_for_timeout(2000)

            print("Expanding permit list...")
            plus_btn = await page.wait_for_selector(
                'button:has-text("+"), [class*="expand"], [class*="accordion"], [aria-label*="expand"]',
                timeout=10000
            )
            await plus_btn.click()
            await page.wait_for_timeout(2000)

            page_text = await page.inner_text("body")

            print("--- PAGE TEXT SNIPPET ---")
            print(page_text[:3000])
            print("--- END SNIPPET ---")

            issued_keywords = ["issued", "permit issued", "approved", "active"]
            found = [kw for kw in issued_keywords if kw.lower() in page_text.lower()]

            if found:
                print(f"PERMIT_FOUND: {', '.join(found)}")
                # Write result to file so workflow can read it
                with open("permit_result.txt", "w") as f:
                    f.write(f"FOUND\nKeywords: {', '.join(found)}\n\n{page_text[:2000]}")
            else:
                print("No issued permit detected yet.")
                with open("permit_result.txt", "w") as f:
                    f.write("NOT_FOUND")

            await page.screenshot(path="permit_check_screenshot.png", full_page=False)
            print("Screenshot saved.")

        except PlaywrightTimeout as e:
            print(f"ERROR: Timeout - {e}")
            with open("permit_result.txt", "w") as f:
                f.write(f"ERROR\nTimeout: {e}")
            sys.exit(1)

        except Exception as e:
            print(f"ERROR: {e}")
            with open("permit_result.txt", "w") as f:
                f.write(f"ERROR\n{e}")
            sys.exit(1)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(check_permit())
