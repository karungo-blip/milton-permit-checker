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

            # Click the Address box and type
            print("Clicking Address box...")
            await page.mouse.click(970, 400)
            await page.wait_for_timeout(1000)
            await page.keyboard.type(ADDRESS, delay=150)
            print(f"Typed: {ADDRESS}")
            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Print all text visible on page including shadow DOM
            # Try clicking the first suggestion by coordinates
            # The dropdown typically appears just below the search box
            # Search box is at y~400, dropdown item would be at y~430
            print("Clicking dropdown suggestion at y=440...")
            await page.mouse.click(910, 440)
            await page.wait_for_timeout(4000)
            await page.screenshot(path="permit_check_screenshot.png")
            print("Clicked dropdown area.")

            # Print what frames exist and their content
            print(f"Number of frames: {len(page.frames)}")
            for i, frame in enumerate(page.frames):
                print(f"Frame {i}: {frame.url}")
                try:
                    txt = await frame.inner_text("body")
                    if "zoom" in txt.lower() or "select" in txt.lower() or "property" in txt.lower():
                        print(f"  >> Relevant content: {txt[:500]}")
                except:
                    pass

            # Try clicking "Zoom to" via JavaScript in all frames
            print("Trying JS click on Zoom to text...")
            for frame in page.frames:
                try:
                    result = await frame.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.innerText && el.innerText.trim() === 'Zoom to') {
                                    el.click();
                                    return 'clicked: ' + el.tagName + ' ' + el.className;
                                }
                            }
                            return 'not found';
                        }
                    """)
                    print(f"Frame {frame.url} JS result: {result}")
                    if result != 'not found':
                        break
                except Exception as e:
                    print(f"Frame JS error: {e}")

            await page.wait_for_timeout(4000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Now try clicking Select property via JS
            print("Trying JS click on Select property...")
            for frame in page.frames:
                try:
                    result = await frame.evaluate("""
                        () => {
                            const all = document.querySelectorAll('*');
                            for (const el of all) {
                                if (el.innerText && el.innerText.trim().toLowerCase().includes('select property')) {
                                    el.click();
                                    return 'clicked: ' + el.tagName + ' ' + el.className;
                                }
                            }
                            return 'not found';
                        }
                    """)
                    print(f"Select property JS result: {result}")
                    if result != 'not found':
                        break
                except Exception as e:
                    print(f"JS error: {e}")

            await page.wait_for_timeout(4000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Scroll down
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
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
