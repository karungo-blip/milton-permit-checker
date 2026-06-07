import asyncio
import sys
from datetime import datetime
from playwright.async_api import async_playwright

ADDRESS = "1138 Dent Terrace"
PORTAL_URL = "https://permits.milton.ca/citizenportal/app/public-search"
GIS_FRAME_URL = "https://permits.milton.ca/citizenportal/GISpublicPortalPublic.html"


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

            # Get the GIS frame
            gis_frame = None
            for frame in page.frames:
                if "GISpublicPortal" in frame.url:
                    gis_frame = frame
                    print(f"Found GIS frame: {frame.url}")
                    break

            if not gis_frame:
                print("GIS frame not found!")
                sys.exit(1)

            # Get the iframe element position on the main page
            iframe_el = await page.query_selector('iframe[src*="GISpublicPortal"]')
            if iframe_el:
                box = await iframe_el.bounding_box()
                print(f"iframe bounding box: {box}")
                iframe_x = box['x']
                iframe_y = box['y']
            else:
                # fallback estimate from screenshots
                iframe_x = 168
                iframe_y = 365
                print(f"iframe element not found, using estimate: x={iframe_x}, y={iframe_y}")

            # The search input inside the iframe is at roughly x=800, y=35 within the iframe
            # (top-right of the map widget)
            search_x = iframe_x + 800
            search_y = iframe_y + 35
            print(f"Clicking search box at page coords: {search_x}, {search_y}")
            await page.mouse.click(search_x, search_y)
            await page.wait_for_timeout(1000)
            await page.keyboard.type(ADDRESS, delay=150)
            print(f"Typed: {ADDRESS}")
            await page.wait_for_timeout(4000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Print shadow DOM content of GIS frame to find dropdown
            shadow_text = await gis_frame.evaluate("""
                () => {
                    function getText(root) {
                        let text = '';
                        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
                        let node;
                        while (node = walker.nextNode()) {
                            text += node.textContent + ' ';
                        }
                        // Also check shadow roots
                        const els = root.querySelectorAll('*');
                        for (const el of els) {
                            if (el.shadowRoot) {
                                text += getText(el.shadowRoot);
                            }
                        }
                        return text;
                    }
                    return getText(document);
                }
            """)
            print(f"GIS frame text (first 1000): {shadow_text[:1000]}")

            # Try clicking "Zoom to" via shadow DOM piercing JS
            zoom_result = await gis_frame.evaluate("""
                () => {
                    function findAndClick(root, text) {
                        const els = root.querySelectorAll('*');
                        for (const el of els) {
                            if (el.shadowRoot) {
                                const r = findAndClick(el.shadowRoot, text);
                                if (r) return r;
                            }
                            if (el.textContent && el.textContent.trim() === text) {
                                el.click();
                                return 'clicked: ' + el.tagName + ' class=' + el.className;
                            }
                        }
                        return null;
                    }
                    return findAndClick(document, 'Zoom to') || 'not found';
                }
            """)
            print(f"Zoom to shadow DOM result: {zoom_result}")

            await page.wait_for_timeout(4000)
            await page.screenshot(path="permit_check_screenshot.png")

            # If zoom to worked, now find the blue dot and click it
            # Try clicking center of map (where zoomed property should be)
            map_center_x = iframe_x + 450
            map_center_y = iframe_y + 400
            print(f"Clicking map center at: {map_center_x}, {map_center_y}")
            await page.mouse.click(map_center_x, map_center_y)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Try Select property via shadow DOM
            select_result = await gis_frame.evaluate("""
                () => {
                    function findAndClick(root, text) {
                        const els = root.querySelectorAll('*');
                        for (const el of els) {
                            if (el.shadowRoot) {
                                const r = findAndClick(el.shadowRoot, text);
                                if (r) return r;
                            }
                            if (el.textContent && el.textContent.trim().toLowerCase().includes(text.toLowerCase())) {
                                el.click();
                                return 'clicked: ' + el.tagName + ' class=' + el.className + ' text=' + el.textContent.trim().substring(0,50);
                            }
                        }
                        return null;
                    }
                    return findAndClick(document, 'Select property') || 'not found';
                }
            """)
            print(f"Select property shadow DOM result: {select_result}")

            await page.wait_for_timeout(3000)
            await page.screenshot(path="permit_check_screenshot.png")

            # Also try on main page
            select_main = await page.evaluate("""
                () => {
                    function findAndClick(root, text) {
                        const els = root.querySelectorAll('*');
                        for (const el of els) {
                            if (el.shadowRoot) {
                                const r = findAndClick(el.shadowRoot, text);
                                if (r) return r;
                            }
                            if (el.textContent && el.textContent.trim().toLowerCase().includes(text.toLowerCase())) {
                                el.click();
                                return 'clicked: ' + el.tagName;
                            }
                        }
                        return null;
                    }
                    return findAndClick(document, 'Select property') || 'not found';
                }
            """)
            print(f"Select property main page result: {select_main}")

            await page.wait_for_timeout(3000)
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
