import asyncio
import sys
from datetime import datetime
from playwright.async_api import async_playwright

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
            print("Page loaded. Clicking Address box by coordinates...")

            # Address box is visually at top-right of map
            # Map starts ~x=168, y=365. Address input is at ~x=970, y=400
            await page.mouse.click(970, 400)
            await page.wait_for_timeout(1000)
            await page.keyboard.type(ADDRESS, delay=150)
            print(f"Typed: {ADDRESS}")
            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Look for "Zoom to" suggestion — check all frames
            print("Looking for Zoom to...")
            zoom_clicked = False
            for frame in page.frames:
                try:
                    zoom = await frame.wait_for_selector('text="Zoom to"', timeout=5000)
                    await zoom.click()
                    zoom_clicked = True
                    print(f"Clicked Zoom to in frame: {frame.url}")
                    break
                except:
                    continue

            if not zoom_clicked:
                print("Zoom to not found in any frame, trying main page...")
                try:
                    zoom = await page.wait_for_selector('text="Zoom to"', timeout=5000)
                    await zoom.click()
                    zoom_clicked = True
                    print("Clicked Zoom to on main page")
                except:
                    print("Zoom to not found anywhere — pressing Enter instead")
                    await page.keyboard.press("Enter")

            await page.wait_for_timeout(4000)
            await page.screenshot(path="permit_check_screenshot.png")
            print("Post-zoom screenshot taken.")

            # Now click "Select property" — check all frames and main page
            print("Looking for Select property...")
            select_clicked = False
            for frame in page.frames:
                try:
                    btn = await frame.wait_for_selector('text="Select property"', timeout=5000)
                    await btn.click()
                    select_clicked = True
                    print(f"Clicked Select property in frame: {frame.url}")
                    break
                except:
                    continue

            if not select_clicked:
                try:
                    btn = await page.wait_for_selector('text="Select property"', timeout=5000)
                    await btn.click()
                    print("Clicked Select property on main page")
                except:
                    print("Select property not found")

            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Scroll down to see permits
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # Try expanding permit section
            for frame in [page] + page.frames:
                try:
                    plus = await frame.wait_for_selector(
                        '[aria-expanded="false"], button:has-text("+"), [class*="expand"]',
                        timeout=3000
                    )
                    await plus.click()
                    print("Clicked expand button")
                    await page.wait_for_timeout(2000)
                    break
                except:
                    continue

            await page.screenshot(path="permit_check_screenshot.png")

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
