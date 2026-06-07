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

            # The map is inside an iframe — find it
            print("Looking for iframe...")
            frames = page.frames
            print(f"Found {len(frames)} frames")
            for f in frames:
                print(f"  Frame URL: {f.url}")

            # Try finding the input in all frames
            search_input = None
            target_frame = None

            for frame in page.frames:
                try:
                    inp = await frame.wait_for_selector(
                        'input[placeholder="Address"]',
                        timeout=5000
                    )
                    if inp:
                        search_input = inp
                        target_frame = frame
                        print(f"Found search input in frame: {frame.url}")
                        break
                except:
                    continue

            if not search_input:
                # Try clicking by coordinates — Address box is top-right of map
                # Map appears to start around x=150, y=320 in the screenshot
                # Address box is at roughly x=870, y=358 based on screenshot
                print("Input not found in frames, trying coordinate click...")
                await page.mouse.click(870, 358)
                await page.wait_for_timeout(1000)
                await page.keyboard.type(ADDRESS, delay=150)
            else:
                await search_input.click()
                await page.wait_for_timeout(500)
                await search_input.type(ADDRESS, delay=150)

            print(f"Typed address: {ADDRESS}")
            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Look for "Zoom to" suggestion in any frame
            print("Looking for Zoom to suggestion...")
            zoom_clicked = False
            for frame in page.frames:
                try:
                    zoom = await frame.wait_for_selector(
                        'text="Zoom to"',
                        timeout=5000
                    )
                    await zoom.click()
                    zoom_clicked = True
                    print("Clicked Zoom to")
                    break
                except:
                    continue

            if not zoom_clicked:
                print("Zoom to not found, trying keyboard Enter...")
                await page.keyboard.press("Enter")

            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Click blue circle — try coordinate-based click in center of map
            print("Clicking blue circle...")
            for frame in page.frames:
                try:
                    dot = await frame.wait_for_selector(
                        'circle, [class*="esri-feature"], [class*="graphic"]',
                        timeout=5000
                    )
                    await dot.click()
                    print("Clicked dot via selector")
                    break
                except:
                    continue

            await page.wait_for_timeout(2000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Click Select property
            print("Looking for Select property...")
            select_clicked = False
            for frame in page.frames:
                try:
                    btn = await frame.wait_for_selector(
                        'text="Select property"',
                        timeout=5000
                    )
                    await btn.click()
                    select_clicked = True
                    print("Clicked Select property")
                    break
                except:
                    continue

            if not select_clicked:
                # Try on main page
                try:
                    btn = await page.wait_for_selector(
                        'text="Select property"',
                        timeout=5000
                    )
                    await btn.click()
                    print("Clicked Select property on main page")
                except:
                    print("Select property not found")

            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Scroll down and check for permit status
            await page.keyboard.press("End")
            await page.wait_for_timeout(2000)

            # Try clicking + button
            try:
                plus = await page.wait_for_selector(
                    '[aria-expanded="false"], button:has-text("+"), [class*="expand"]',
                    timeout=5000
                )
                await plus.click()
                await page.wait_for_timeout(2000)
            except:
                print("No expand button found")

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
