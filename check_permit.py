import asyncio
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

ADDRESS = "1138 Dent Terrace"
PORTAL_URL = "https://permits.milton.ca/citizenportal/app/public-search"
TO_EMAIL = "karungo@gmail.com"

# Set via GitHub Secrets
FROM_EMAIL = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")


def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
    print(f"Email sent: {subject}")


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

            # Find and fill the address search box
            print("Typing address...")
            search_input = await page.wait_for_selector(
                'input[placeholder*="Search"], input[type="search"], input[placeholder*="address"], input[placeholder*="Address"]',
                timeout=20000
            )
            await search_input.click()
            await search_input.fill("")
            await search_input.type(ADDRESS, delay=100)
            await page.wait_for_timeout(2000)

            # Wait for the blue dot / map marker to appear and click it
            print("Waiting for map marker (blue dot)...")
            # Try clicking a map pin/marker — Milton portal uses Leaflet or similar
            marker = await page.wait_for_selector(
                '.leaflet-marker-icon, [class*="marker"], [class*="pin"], svg circle, canvas',
                timeout=20000
            )
            await marker.click()
            await page.wait_for_timeout(2000)

            # Look for "Select Property" button or similar
            print("Looking for Select Property option...")
            select_btn = await page.wait_for_selector(
                'button:has-text("Select"), a:has-text("Select"), [class*="select-property"]',
                timeout=10000
            )
            await select_btn.click()
            await page.wait_for_timeout(2000)

            # Click the + / expand button to see permits
            print("Expanding permit list...")
            plus_btn = await page.wait_for_selector(
                'button:has-text("+"), [class*="expand"], [class*="accordion"], [aria-label*="expand"]',
                timeout=10000
            )
            await plus_btn.click()
            await page.wait_for_timeout(2000)

            # Grab the page text and look for permit status
            content = await page.content()
            page_text = await page.inner_text("body")

            print("Page content captured. Checking for permit status...")
            print("--- PAGE TEXT SNIPPET ---")
            print(page_text[:3000])
            print("--- END SNIPPET ---")

            # Keywords that indicate a permit has been issued
            issued_keywords = ["issued", "permit issued", "approved", "active"]
            found = [kw for kw in issued_keywords if kw.lower() in page_text.lower()]

            if found:
                send_email(
                    subject=f"🏠 Milton Permit UPDATE for {ADDRESS}",
                    body=(
                        f"A permit status change was detected for {ADDRESS}!\n\n"
                        f"Keywords found: {', '.join(found)}\n\n"
                        f"Check the portal: {PORTAL_URL}\n\n"
                        f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"--- Page text excerpt ---\n{page_text[:2000]}"
                    )
                )
                print("Permit found! Email sent.")
            else:
                print("No issued permit detected yet. No email sent.")

            # Take a screenshot for the Actions log
            await page.screenshot(path="permit_check_screenshot.png", full_page=False)
            print("Screenshot saved.")

        except PlaywrightTimeout as e:
            error_msg = f"Timeout while checking permit portal: {e}"
            print(f"ERROR: {error_msg}")
            send_email(
                subject=f"⚠️ Milton Permit Check - Timeout Error",
                body=f"{error_msg}\n\nCheck the portal manually: {PORTAL_URL}\n\nTime: {datetime.now()}"
            )
            sys.exit(1)

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"ERROR: {error_msg}")
            send_email(
                subject=f"⚠️ Milton Permit Check - Script Error",
                body=f"{error_msg}\n\nCheck the portal manually: {PORTAL_URL}\n\nTime: {datetime.now()}"
            )
            sys.exit(1)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(check_permit())
