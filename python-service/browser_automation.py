from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import logging
import time
from database import add_log, save_scraped_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def type_text_slowly(page, selector: str, text: str, delay: int = 50):
    """
    Type text character by character to simulate human typing.
    Never uses paste or fill - only types.
    """
    try:
        element = page.locator(selector).first
        await element.click()
        await asyncio.sleep(0.2)  # Small delay after click
        
        # Clear the field first by selecting all and deleting
        await page.keyboard.press("Control+A")
        await asyncio.sleep(0.1)
        await page.keyboard.press("Delete")
        await asyncio.sleep(0.1)
        
        # Type the entire text character by character with delay
        await page.keyboard.type(text, delay=delay)
        
        logger.info(f"Typed {len(text)} characters into {selector}")
        add_log("info", f"Typed {len(text)} characters into {selector}")
    except Exception as e:
        error_msg = f"Error typing into {selector}: {str(e)}"
        logger.error(error_msg)
        add_log("error", error_msg)
        raise

# Global variable to store latest screenshot path for live preview
_latest_screenshot_path = None
SCREENSHOT_FILENAME = "live_preview.png"  # Single file that gets overwritten

async def take_screenshot(page, step_name: str = None):
    """Take screenshot and store path for live preview - overwrites single file"""
    global _latest_screenshot_path
    from pathlib import Path
    
    try:
        # Use single filename that gets overwritten
        screenshot_path = Path(__file__).parent / SCREENSHOT_FILENAME
        await page.screenshot(path=str(screenshot_path), full_page=False)
        _latest_screenshot_path = str(screenshot_path)
        if step_name:
            add_log("info", f"Screenshot updated: {step_name}")
        logger.info(f"Screenshot saved to: {screenshot_path}")
        return str(screenshot_path)
    except Exception as e:
        error_msg = f"Failed to take screenshot: {str(e)}"
        logger.error(error_msg)
        add_log("error", error_msg)
        return None

async def perform_login(username: str, password: str, totp_code: str):
    """
    Perform ConEd login automation using headless browser.
    Types all values character by character, never pastes.
    """
    global _latest_screenshot_path
    import time
    from pathlib import Path
    
    # Initialize screenshot path
    screenshot_path = Path(__file__).parent / SCREENSHOT_FILENAME
    _latest_screenshot_path = str(screenshot_path)
    
    coned_url = "https://www.coned.com/en/login"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Set to False for visible browser (can watch in real-time)
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        try:
            add_log("info", f"Starting ConEd scraper - Navigating to {coned_url}")
            logger.info(f"Navigating to {coned_url}")
            await page.goto(coned_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # Wait for page to fully load
            await take_screenshot(page, "Login page loaded")
            add_log("info", "Page loaded successfully")
            
            # Wait for and type username
            logger.info("Looking for username field...")
            username_selectors = [
                'input[name="username"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[id*="username"]',
                'input[id*="email"]',
                'input[placeholder*="username" i]',
                'input[placeholder*="email" i]'
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        username_field = selector
                        break
                except:
                    continue
            
            if not username_field:
                # Take screenshot for debugging
                await page.screenshot(path="debug_username.png")
                raise Exception("Could not find username field. Screenshot saved as debug_username.png")
            
            logger.info(f"Found username field: {username_field}")
            add_log("info", f"Found username field: {username_field}")
            await type_text_slowly(page, username_field, username, delay=50)
            await asyncio.sleep(0.5)
            await take_screenshot(page, "Username entered")
            add_log("success", "Username entered successfully")
            
            # Wait for and type password
            logger.info("Looking for password field...")
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[id*="password"]',
                'input[placeholder*="password" i]'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        password_field = selector
                        break
                except:
                    continue
            
            if not password_field:
                await page.screenshot(path="debug_password.png")
                raise Exception("Could not find password field. Screenshot saved as debug_password.png")
            
            logger.info(f"Found password field: {password_field}")
            add_log("info", f"Found password field: {password_field}")
            await type_text_slowly(page, password_field, password, delay=50)
            await asyncio.sleep(0.5)
            await take_screenshot(page, "Password entered")
            add_log("success", "Password entered successfully")
            
            # Click login/submit button
            logger.info("Looking for submit button...")
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Sign In")',
                'button:has-text("Log In")',
                'button:has-text("Login")',
                'input[type="submit"]',
                'button[id*="submit"]',
                'button[id*="login"]'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        submit_button = selector
                        break
                except:
                    continue
            
            if not submit_button:
                await page.screenshot(path="debug_submit.png")
                raise Exception("Could not find submit button. Screenshot saved as debug_submit.png")
            
            logger.info(f"Found submit button: {submit_button}")
            add_log("info", f"Found submit button: {submit_button}")
            await page.locator(submit_button).first.click()
            add_log("info", "Login form submitted")
            await asyncio.sleep(3)  # Wait for potential redirect or TOTP field
            await take_screenshot(page, "After form submit")
            
            # Check if TOTP field appears
            logger.info("Checking for TOTP/MFA field...")
            totp_selectors = [
                'input[name*="totp"]',
                'input[name*="mfa"]',
                'input[name*="code"]',
                'input[name*="verification"]',
                'input[type="text"][placeholder*="code" i]',
                'input[type="text"][placeholder*="verification" i]',
                'input[id*="totp"]',
                'input[id*="mfa"]',
                'input[id*="code"]'
            ]
            
            totp_field = None
            for selector in totp_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        totp_field = selector
                        break
                except:
                    continue
            
            if totp_field:
                logger.info(f"Found TOTP field: {totp_field}")
                add_log("info", f"Found TOTP field: {totp_field}")
                await take_screenshot(page, "TOTP field found")
                await type_text_slowly(page, totp_field, totp_code, delay=50)
                await asyncio.sleep(0.5)
                await take_screenshot(page, "TOTP entered")
                add_log("success", "TOTP code entered successfully")
                
                # Submit TOTP
                submit_totp_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Verify")',
                    'button:has-text("Submit")',
                    'button:has-text("Continue")'
                ]
                
                for selector in submit_totp_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            await page.locator(selector).first.click()
                            break
                    except:
                        continue
                
                await asyncio.sleep(3)
                await take_screenshot(page, "After TOTP submit")
            
            # Check if login was successful
            current_url = page.url
            await take_screenshot(page, "Login result")
            
            # Wait a bit for page to fully load
            await asyncio.sleep(2)
            
            # Check for success by looking at page content, not just URL
            page_content = await page.content()
            page_text = await page.locator("body").inner_text()
            
            # Success indicators - check for actual page content
            success_indicators = [
                'my account',
                'account snapshot',
                'outstanding balance',
                'pay bill',
                'bill history',
                'energy use'
            ]
            
            # Error indicators
            error_keywords = [
                'invalid username or password',
                'incorrect password',
                'authentication failed',
                'login failed',
                'try again',
                'error signing in'
            ]
            
            # Check for errors first
            has_error = any(keyword in page_text.lower() for keyword in error_keywords)
            if has_error:
                raise Exception("Login failed - error detected on page")
            
            # Check for success indicators
            is_success = any(indicator in page_text.lower() for indicator in success_indicators)
            
            # Also check URL as fallback
            if not is_success:
                url_indicators = ['account', 'dashboard', 'my-account', 'accounts-billing']
                is_success = any(indicator in current_url.lower() for indicator in url_indicators)
            
            # If still not sure, check if we can see account elements
            if not is_success:
                try:
                    # Try to find account-related elements
                    account_elements = await page.locator('[class*="account"], [class*="balance"], [class*="bill"]').count()
                    if account_elements > 0:
                        is_success = True
                except:
                    pass
            
            logger.info(f"Login process completed. Final URL: {current_url}")
            add_log("success", f"Login process completed. Final URL: {current_url}")
            
            # Scrape data after successful login
            scraped_data = {}
            if is_success:
                try:
                    add_log("info", "Starting data scraping...")
                    # Navigate to account page if not already there
                    account_url = "https://www.coned.com/en/accounts-billing/my-account"
                    if account_url not in current_url:
                        add_log("info", f"Navigating to account page: {account_url}")
                        await page.goto(account_url, wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(3)  # Wait for page to load
                    
                    scraped_data = await scrape_account_data(page)
                    await take_screenshot(page, "Scraping complete")
                    add_log("success", "Data scraping completed successfully")
                    save_scraped_data(scraped_data, "success")
                except Exception as e:
                    error_msg = f"Data scraping failed: {str(e)}"
                    add_log("error", error_msg)
                    logger.error(error_msg)
                    save_scraped_data({}, "error", error_msg)
            
            await browser.close()
            add_log("info", "Browser closed")
            
            return {
                "success": is_success,
                "url": current_url,
                "screenshot": "login_result.png",
                "data": scraped_data
            }
            
        except PlaywrightTimeoutError as e:
            await page.screenshot(path="error_timeout.png")
            error_msg = f"Timeout error: {str(e)}"
            logger.error(error_msg)
            add_log("error", error_msg)
            save_scraped_data({}, "error", error_msg)
            await browser.close()
            raise Exception(f"Login timeout: {str(e)}")
        except Exception as e:
            await page.screenshot(path="error_general.png")
            error_msg = f"Login error: {str(e)}"
            logger.error(error_msg)
            add_log("error", error_msg)
            save_scraped_data({}, "error", error_msg)
            await browser.close()
            raise

async def scrape_account_data(page):
    """
    Scrape account data from ConEd account page.
    Extracts Account Balance and Current Bill PDF link.
    """
    import time
    scraped_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "url": page.url,
        "title": await page.title(),
        "account_balance": None,
        "current_bill_pdf_link": None,
        "current_bill_pdf_href": None,
    }
    
    try:
        # Wait for page to load
        add_log("info", "Waiting for account page to load...")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(2)  # Additional wait for dynamic content
        
        # Scrape Account Balance
        add_log("info", "Looking for Account Balance...")
        balance_selectors = [
            '.overview-bill-card__price.js-overview-bill-card-price.no-translate',
            '.overview-bill-card__price',
            'div.overview-bill-card__price',
            '[class*="overview-bill-card__price"]'
        ]
        
        account_balance = None
        for selector in balance_selectors:
            try:
                balance_element = page.locator(selector).first
                # Check if element exists
                try:
                    await balance_element.wait_for(state="visible", timeout=2000)
                    # Get the full text including the superscript
                    balance_text = await balance_element.inner_text()
                    
                    if balance_text:
                        # Clean up the balance text
                        balance_clean = balance_text.strip().replace('\n', ' ').replace('\t', ' ')
                        account_balance = balance_clean
                        add_log("success", f"Found Account Balance: {account_balance}")
                        break
                except:
                    # Element not found, try next selector
                    continue
            except Exception as e:
                add_log("warning", f"Balance selector {selector} failed: {str(e)}")
                continue
        
        if not account_balance:
            add_log("warning", "Could not find Account Balance element")
        else:
            scraped_data["account_balance"] = account_balance
        
        # Scrape Current Bill PDF Link
        add_log("info", "Looking for Current Bill PDF link...")
        bill_link_selectors = [
            'a.overview-bill-card__cta.js-bill-link.js-overview-bill-card__cta',
            'a.overview-bill-card__cta',
            'a[class*="overview-bill-card__cta"]',
            'a:has-text("View Current Bill")',
            'a:has-text("Current Bill")'
        ]
        
        bill_pdf_link = None
        bill_pdf_href = None
        
        for selector in bill_link_selectors:
            try:
                bill_element = page.locator(selector).first
                # Check if element exists
                try:
                    await bill_element.wait_for(state="visible", timeout=2000)
                    # Get the link text
                    link_text = (await bill_element.inner_text()).strip()
                    # Get the href attribute
                    href = await bill_element.get_attribute('href')
                    # Also check for onclick data attributes
                    data_type = await bill_element.get_attribute('data-type')
                    
                    if link_text or href:
                        bill_pdf_link = link_text if link_text else "View Current Bill (PDF)"
                        bill_pdf_href = href if href else "#"
                        scraped_data["current_bill_pdf_link"] = bill_pdf_link
                        scraped_data["current_bill_pdf_href"] = bill_pdf_href
                        scraped_data["bill_pdf_data_type"] = data_type
                        add_log("success", f"Found Current Bill PDF link: {bill_pdf_link}")
                        break
                except:
                    # Element not found, try next selector
                    continue
            except Exception as e:
                add_log("warning", f"Bill link selector {selector} failed: {str(e)}")
                continue
        
        if not bill_pdf_link:
            add_log("warning", "Could not find Current Bill PDF link element")
        
        # Take screenshot of the account page for verification
        try:
            screenshot_path = f"account_page_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            scraped_data["screenshot"] = screenshot_path
            add_log("info", f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            add_log("warning", f"Failed to save screenshot: {str(e)}")
            
    except Exception as e:
        error_msg = f"Error during data scraping: {str(e)}"
        add_log("error", error_msg)
        logger.error(error_msg)
        scraped_data["error"] = str(e)
    
    return scraped_data
