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

            # Get GIS frame
            gis_frame = None
            for frame in page.frames:
                if "GISpublicPortal" in frame.url:
                    gis_frame = frame
                    break

            if not gis_frame:
                raise Exception("GIS frame not found")

            iframe_el = await page.query_selector('iframe[src*="GISpublicPortal"]')
            box = await iframe_el.bounding_box()

            # Click the Address search box and type
            search_x = box['x'] + 800
            search_y = box['y'] + 35
            await page.mouse.click(search_x, search_y)
            await page.wait_for_timeout(500)
            await page.keyboard.type(ADDRESS, delay=150)
            print(f"Typed: {ADDRESS}")
            await page.wait_for_timeout(4000)

            # Check what the GIS frame says
            frame_text = await gis_frame.evaluate("() => document.body.innerText")
            print(f"GIS frame response: {frame_text[:500]}")
            await page.screenshot(path="permit_check_screenshot.png")

            if "no results" in frame_text.lower():
                print("No permit found yet — address returned no results. Monitoring continues.")
                with open("permit_result.txt", "w") as f:
                    f.write("NOT_FOUND")
                sys.exit(0)

            # Results exist! Address was found — permit may be issued
            print("Address found in portal! Proceeding to check permit status...")

            # Click Zoom to (just below search box)
            await page.mouse.click(search_x, box['y'] + 70)
            await page.wait_for_timeout(4000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Click the blue dot at map center
            map_x = box['x'] + 475
            map_y = box['y'] + 300
            await page.mouse.click(map_x, map_y)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Click Select property
            await page.mouse.click(map_x, map_y + 50)
            await page.wait_for_timeout(3000)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await page.screenshot(path="permit_check_screenshot.png")

            page_text = await page.inner_text("body")
            print("--- PAGE TEXT ---")
            print(page_text[:3000])
            print("--- END ---")

            print("PERMIT ACTIVITY DETECTED!")
            with open("permit_result.txt", "w") as f:
                f.write(f"FOUND\n\n{page_text[:2000]}")

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
