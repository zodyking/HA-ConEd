#!/usr/bin/env python3
"""
Test script for Con Edison browser-based login.

Tests Playwright browser automation to verify credentials are working.
"""

import argparse
import asyncio
import os
import sys

# Add parent directory to path to import browser_automation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python-service'))


async def test_browser_login(email: str, password: str, totp_secret: str):
    """Test browser-based login to Con Edison."""
    
    try:
        import pyotp
        from playwright.async_api import async_playwright
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("Install with: pip install playwright pyotp")
        print("Then run: playwright install chromium")
        return False

    print("=" * 60)
    print("BROWSER LOGIN TEST - Con Edison")
    print("=" * 60)
    print(f"Email: {email}")
    print(f"TOTP Secret: {'*' * (len(totp_secret) - 4)}{totp_secret[-4:]}" if totp_secret else "Not provided")
    print()

    # Generate TOTP code
    totp = pyotp.TOTP(totp_secret) if totp_secret else None
    totp_code = totp.now() if totp else ""
    print(f"Current TOTP Code: {totp_code}")
    print()

    coned_url = "https://www.coned.com/en/login"

    async with async_playwright() as p:
        print("[1] Launching browser...")
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        try:
            print(f"[2] Navigating to {coned_url}...")
            await page.goto(coned_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            print("    ✓ Page loaded")
            
            # Find and fill username
            print("[3] Entering username...")
            username_selectors = [
                'input[name="username"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[id*="username"]',
                'input[id*="email"]',
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    loc = page.locator(selector).first
                    if await loc.count() > 0 and await loc.is_visible():
                        username_field = selector
                        break
                except:
                    continue
            
            if not username_field:
                print("    ✗ Could not find username field")
                await browser.close()
                return False
            
            print(f"    Found field: {username_field}")
            await page.locator(username_field).fill(email)
            print(f"    ✓ Entered email")
            
            # Find and fill password
            print("[4] Entering password...")
            await page.locator('input[type="password"]').first.fill(password)
            print("    ✓ Entered password")
            
            # Submit form
            print("[5] Submitting login form...")
            await page.locator('button[type="submit"]').first.click()
            await asyncio.sleep(3)
            print("    ✓ Form submitted")
            
            # Check for TOTP field
            print("[6] Checking for TOTP/MFA field...")
            totp_selectors = [
                'input#form-login-mta-code',
                'input[name="LoginMFACode"]',
                'input[id*="mta"]',
                'input[name*="totp"]',
                'input[name*="mfa"]',
            ]
            
            totp_field = None
            for selector in totp_selectors:
                try:
                    loc = page.locator(selector).first
                    if await loc.count() > 0 and await loc.is_visible():
                        totp_field = selector
                        break
                except:
                    continue
            
            if totp_field and totp_code:
                print(f"    Found TOTP field: {totp_field}")
                await page.locator(totp_field).fill(totp_code)
                print(f"    ✓ Entered TOTP code: {totp_code}")
                
                # Submit TOTP
                await page.locator('button[type="submit"]').first.click()
                await asyncio.sleep(3)
                print("    ✓ TOTP submitted")
            elif totp_field:
                print("    ✗ TOTP field found but no TOTP secret provided")
            else:
                print("    No TOTP field (may not be required)")
            
            # Check result
            print("[7] Checking login result...")
            await asyncio.sleep(2)
            
            page_content = await page.content()
            page_text = await page.locator("body").inner_text()
            current_url = page.url
            
            # Check for errors
            error_keywords = [
                'invalid username or password',
                'incorrect password',
                'authentication failed',
                'login failed',
                'try again',
                'error signing in',
                'invalid code'
            ]
            
            has_error = any(keyword in page_text.lower() for keyword in error_keywords)
            
            if has_error:
                print("    ✗ LOGIN FAILED - Error detected on page")
                print(f"    Current URL: {current_url}")
                
                # Take screenshot
                await page.screenshot(path="login_failed.png")
                print("    Screenshot saved to login_failed.png")
                
                await browser.close()
                return False
            
            # Check for success
            success_indicators = [
                'my account',
                'account snapshot',
                'outstanding balance',
                'pay bill',
                'bill history'
            ]
            
            is_success = any(indicator in page_text.lower() for indicator in success_indicators)
            
            if is_success:
                print("    ✓ LOGIN SUCCESSFUL!")
                print(f"    Current URL: {current_url}")
                
                # Take screenshot
                await page.screenshot(path="login_success.png")
                print("    Screenshot saved to login_success.png")
            else:
                print("    ? Login status unclear")
                print(f"    Current URL: {current_url}")
                
                # Take screenshot
                await page.screenshot(path="login_unclear.png")
                print("    Screenshot saved to login_unclear.png")
            
            # Keep browser open for inspection
            print()
            print("Press Enter to close browser...")
            input()
            
            await browser.close()
            return is_success
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await page.screenshot(path="login_error.png")
                print("    Screenshot saved to login_error.png")
            except:
                pass
            
            await browser.close()
            return False

    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Test browser login to Con Edison")
    parser.add_argument("--email", "-e", help="Con Edison email", 
                        default=os.getenv("CONED_EMAIL"))
    parser.add_argument("--password", "-p", help="Con Edison password",
                        default=os.getenv("CONED_PASSWORD"))
    parser.add_argument("--totp-secret", "-t", help="TOTP secret for MFA",
                        default=os.getenv("CONED_TOTP_SECRET"))
    
    args = parser.parse_args()
    
    if not args.email or not args.password:
        print("ERROR: Email and password are required.")
        print()
        print("Usage:")
        print("  python test_credentials.py --email YOUR_EMAIL --password YOUR_PASSWORD --totp-secret YOUR_TOTP_SECRET")
        print()
        print("Or set environment variables:")
        print("  CONED_EMAIL, CONED_PASSWORD, CONED_TOTP_SECRET")
        sys.exit(1)
    
    result = asyncio.run(test_browser_login(args.email, args.password, args.totp_secret or ""))
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
