from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import logging
import time
from database import add_log, save_scraped_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Single screenshot filename that gets overwritten each scrape
# Captures the page state where account balance was found
SCREENSHOT_FILENAME = "account_balance.png"
# Live preview screenshot for console display
LIVE_PREVIEW_FILENAME = "live_preview.png"

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

async def take_live_preview(page, step_name: str = ""):
    """Take a live preview screenshot for console display"""
    try:
        from pathlib import Path
        screenshot_dir = Path("./data")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / LIVE_PREVIEW_FILENAME
        
        # Ensure page is ready before taking screenshot
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=2000)
        except:
            pass  # Continue even if wait times out
        
        await page.screenshot(path=str(screenshot_path), full_page=False)
        if step_name:
            add_log("debug", f"Live preview updated: {step_name}")
    except Exception as e:
        logger.debug(f"Failed to take live preview: {str(e)}")
        # Don't raise - preview failures shouldn't stop scraping

async def perform_login(username: str, password: str, totp_code: str):
    """
    Perform ConEd login automation using headless browser.
    Types all values character by character, never pastes.
    """
    import time
    from pathlib import Path
    
    coned_url = "https://www.coned.com/en/login"
    
    async with async_playwright() as p:
        # Force headless mode - check environment variable or default to True
        import os
        headless_mode = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
        
        browser = await p.chromium.launch(
            headless=headless_mode,  # Run in headless mode
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
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
            add_log("info", "Page loaded successfully")
            await take_live_preview(page, "Page loaded")
            
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
                raise Exception("Could not find username field")
            
            logger.info(f"Found username field: {username_field}")
            add_log("info", f"Found username field: {username_field}")
            await type_text_slowly(page, username_field, username, delay=50)
            await asyncio.sleep(0.5)
            add_log("success", "Username entered successfully")
            await take_live_preview(page, "Username entered")
            
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
                raise Exception("Could not find password field")
            
            logger.info(f"Found password field: {password_field}")
            add_log("info", f"Found password field: {password_field}")
            await type_text_slowly(page, password_field, password, delay=50)
            await asyncio.sleep(0.5)
            add_log("success", "Password entered successfully")
            await take_live_preview(page, "Password entered")
            
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
                raise Exception("Could not find submit button")
            
            logger.info(f"Found submit button: {submit_button}")
            add_log("info", f"Found submit button: {submit_button}")
            await page.locator(submit_button).first.click()
            add_log("info", "Login form submitted")
            await asyncio.sleep(3)  # Wait for potential redirect or TOTP field
            await take_live_preview(page, "Login form submitted")
            
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
                await type_text_slowly(page, totp_field, totp_code, delay=50)
                await asyncio.sleep(0.5)
                add_log("success", "TOTP code entered successfully")
                await take_live_preview(page, "TOTP code entered")
                
                # Submit TOTP - wait for button to be visible and enabled
                submit_totp_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Verify")',
                    'button:has-text("Submit")',
                    'button:has-text("Continue")',
                    'button:has-text("Sign In")',
                    'button:has-text("Log In")'
                ]
                
                totp_submitted = False
                for selector in submit_totp_selectors:
                    try:
                        button = page.locator(selector).first
                        if await button.count() > 0:
                            # Wait for button to be visible and enabled
                            await button.wait_for(state="visible", timeout=5000)
                            # Check if button is enabled
                            is_disabled = await button.get_attribute("disabled")
                            if is_disabled is None:
                                await button.click()
                                add_log("info", f"Clicked TOTP submit button: {selector}")
                                totp_submitted = True
                                break
                    except Exception as e:
                        logger.debug(f"TOTP submit selector {selector} failed: {str(e)}")
                        continue
                
                if not totp_submitted:
                    # Try pressing Enter as fallback
                    try:
                        await page.keyboard.press("Enter")
                        add_log("info", "Pressed Enter to submit TOTP")
                        totp_submitted = True
                    except Exception as e:
                        logger.warning(f"Failed to submit TOTP via Enter: {str(e)}")
                
                # Wait for navigation or page update after TOTP submission
                if totp_submitted:
                    try:
                        # Wait for navigation to start and complete
                        add_log("info", "Waiting for navigation after TOTP submission...")
                        # Wait for DOM to be ready first
                        await page.wait_for_load_state("domcontentloaded", timeout=15000)
                        # Then wait for network to be idle
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        await asyncio.sleep(2)  # Additional wait for dynamic content
                        add_log("info", "Navigation completed after TOTP submission")
                        await take_live_preview(page, "After TOTP submission")
                    except Exception as e:
                        logger.debug(f"Navigation wait timeout (may be normal): {str(e)}")
                        # Try waiting for load state with longer timeout
                        try:
                            await page.wait_for_load_state("load", timeout=10000)
                            await asyncio.sleep(3)  # Fallback wait
                        except:
                            await asyncio.sleep(5)  # Final fallback
            
            # Check if login was successful
            # Wait for page to be stable before accessing content
            try:
                add_log("info", "Waiting for page to stabilize before checking login status...")
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                await take_live_preview(page, "Page stabilized")
            except Exception as e:
                logger.debug(f"Page stabilization wait: {str(e)}")
                await asyncio.sleep(2)
                await take_live_preview(page, "After stabilization wait")
            
            current_url = page.url
            
            # Check for success by looking at page content, not just URL
            # Wrap content access in try-except to handle navigation errors
            page_content = None
            page_text = ""
            
            try:
                # Ensure page is not navigating before accessing content
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                page_content = await page.content()
                page_text = await page.locator("body").inner_text()
            except Exception as e:
                # If content access fails, try again after waiting
                logger.warning(f"Failed to get page content (may be navigating): {str(e)}")
                try:
                    await asyncio.sleep(3)
                    await page.wait_for_load_state("load", timeout=10000)
                    page_content = await page.content()
                    page_text = await page.locator("body").inner_text()
                except Exception as e2:
                    # If still failing, use URL as fallback
                    logger.warning(f"Still unable to get page content: {str(e2)}")
                    page_text = ""  # Will rely on URL check only
            
            # Check for errors first (only if we have page text)
            has_error = False
            if page_text:
                error_keywords = [
                    'invalid username or password',
                    'incorrect password',
                    'authentication failed',
                    'login failed',
                    'try again',
                    'error signing in',
                    'invalid code',
                    'verification failed'
                ]
                has_error = any(keyword in page_text.lower() for keyword in error_keywords)
            
            if has_error:
                raise Exception("Login failed - error detected on page")
            
            # Check for success indicators (only if we have page text)
            is_success = False
            if page_text:
                success_indicators = [
                    'my account',
                    'account snapshot',
                    'outstanding balance',
                    'pay bill',
                    'bill history',
                    'energy use'
                ]
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
                    
                    scraped_data = await scrape_account_data(page, context)
                    
                    # Scrape PDF bill URL
                    pdf_bill_url = await scrape_pdf_bill_url(page, context)
                    if pdf_bill_url:
                        scraped_data["pdf_bill_url"] = pdf_bill_url
                    
                    # Scrape bill history ledger
                    bill_history = await scrape_bill_history(page)
                    scraped_data["bill_history"] = bill_history
                    
                    # Screenshot was already taken in scrape_account_data after finding balance
                    # Just store the filename in scraped_data
                    scraped_data["screenshot_path"] = SCREENSHOT_FILENAME
                    
                    add_log("success", f"Data scraping completed successfully")
                    
                    save_scraped_data(scraped_data, "success", None, SCREENSHOT_FILENAME)
                except Exception as e:
                    error_msg = f"Data scraping failed: {str(e)}"
                    add_log("error", error_msg)
                    logger.error(error_msg)
                    save_scraped_data({}, "error", error_msg, None)
            
            await browser.close()
            add_log("info", "Browser closed")
            
            return {
                "success": is_success,
                "url": current_url,
                "screenshot": "login_result.png",
                "data": scraped_data
            }
            
        except PlaywrightTimeoutError as e:
            error_msg = f"Timeout error: {str(e)}"
            logger.error(error_msg)
            add_log("error", error_msg)
            save_scraped_data({}, "error", error_msg, None)
            await browser.close()
            raise Exception(f"Login timeout: {str(e)}")
        except Exception as e:
            error_msg = f"Login error: {str(e)}"
            logger.error(error_msg)
            add_log("error", error_msg)
            save_scraped_data({}, "error", error_msg, None)
            await browser.close()
            raise

async def scrape_account_data(page, context):
    """
    Scrape account data from ConEd account page.
    Extracts Account Balance only.
    """
    import time
    scraped_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "url": page.url,
        "title": await page.title(),
        "account_balance": None,
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
            # Take screenshot right after finding account balance
            try:
                from pathlib import Path
                # Use ./data for persistent storage
                screenshot_dir = Path("./data")
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = screenshot_dir / SCREENSHOT_FILENAME
                await page.screenshot(path=str(screenshot_path), full_page=False)
                add_log("info", f"Screenshot saved: {SCREENSHOT_FILENAME}")
            except Exception as e:
                add_log("warning", f"Failed to save screenshot: {str(e)}")
            
    except Exception as e:
        error_msg = f"Error during data scraping: {str(e)}"
        add_log("error", error_msg)
        logger.error(error_msg)
        scraped_data["error"] = str(e)
    
    return scraped_data

async def download_pdf_from_url(pdf_url: str) -> bool:
    """
    Download PDF from URL and save it locally.
    Returns True if successful, False otherwise.
    """
    import aiohttp
    from pathlib import Path
    
    try:
        add_log("info", f"Downloading PDF from: {pdf_url[:80]}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    add_log("info", f"PDF response: status={response.status}, content-type={content_type}")
                    
                    # Read the PDF content
                    pdf_content = await response.read()
                    
                    if len(pdf_content) > 1000:  # Sanity check - PDF should be at least 1KB
                        # Save to data directory
                        pdf_dir = Path("./data")
                        pdf_dir.mkdir(parents=True, exist_ok=True)
                        pdf_path = pdf_dir / "latest_bill.pdf"
                        
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_content)
                        
                        add_log("success", f"PDF saved: {pdf_path} ({len(pdf_content)} bytes)")
                        return True
                    else:
                        add_log("warning", f"PDF content too small: {len(pdf_content)} bytes")
                        return False
                else:
                    add_log("warning", f"PDF download failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        add_log("warning", f"Error downloading PDF: {str(e)}")
        return False

async def scrape_pdf_bill_url(page, context):
    """
    Scrape the PDF bill URL from ConEd account page.
    First tries to get the href directly from the View Current Bill link.
    If that doesn't work, clicks and waits for the new tab URL.
    Downloads the PDF and saves it locally.
    """
    pdf_url = None
    
    try:
        add_log("info", "Looking for View Current Bill link...")
        
        # Make sure we're on the account page
        account_url = "https://www.coned.com/en/accounts-billing/my-account"
        current_url = page.url
        if account_url not in current_url:
            add_log("info", f"Navigating to account page for PDF: {account_url}")
            await page.goto(account_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
        
        await take_live_preview(page, "Looking for PDF link")
        
        # Selectors for the "View Current Bill" button/link
        # Priority: links with href first (we can extract URL directly)
        pdf_link_selectors = [
            'a:has-text("View Current Bill")',
            'a.overview-bill-card__button',
            '.overview-bill-card a[href]',
            'a[href*="ViewBill"]',
            'a[href*="viewbill"]', 
            'a[href*="bill"][href*="pdf"]',
            '.js-overview-bill-card a[href]',
        ]
        
        # First approach: Try to get the href directly (no click needed)
        for selector in pdf_link_selectors:
            try:
                element = page.locator(selector).first
                count = await element.count()
                if count > 0:
                    add_log("info", f"Found element with selector: {selector}")
                    
                    # Try to get href attribute directly
                    href = await element.get_attribute('href')
                    if href:
                        add_log("info", f"Found href attribute: {href[:100]}...")
                        
                        # Check if it's a valid PDF URL or needs to be made absolute
                        if href.startswith('http'):
                            pdf_url = href
                            add_log("success", f"PDF URL extracted from href: {pdf_url[:100]}...")
                            return pdf_url
                        elif href.startswith('/'):
                            # Relative URL - make it absolute
                            pdf_url = f"https://www.coned.com{href}"
                            add_log("success", f"PDF URL (made absolute): {pdf_url[:100]}...")
                            return pdf_url
                        elif 'javascript:' not in href.lower():
                            pdf_url = href
                            add_log("success", f"PDF URL from href: {pdf_url[:100]}...")
                            return pdf_url
            except Exception as e:
                add_log("debug", f"Selector {selector} failed: {str(e)}")
                continue
        
        add_log("info", "No direct href found, trying click approach...")
        
        # Second approach: Click and capture new tab URL
        pdf_button_selectors = [
            'a:has-text("View Current Bill")',
            'button:has-text("View Current Bill")',
            'a:has-text("View Bill")',
            '.overview-bill-card__button',
            '[class*="view-bill"]',
        ]
        
        pdf_button = None
        for selector in pdf_button_selectors:
            try:
                element = page.locator(selector).first
                count = await element.count()
                if count > 0:
                    await element.wait_for(state="visible", timeout=5000)
                    pdf_button = element
                    add_log("info", f"Found clickable PDF button: {selector}")
                    break
            except:
                continue
        
        if not pdf_button:
            add_log("warning", "Could not find View Current Bill button")
            return None
        
        # Click and wait for new tab
        try:
            add_log("info", "Clicking View Current Bill button...")
            
            # Listen for new page (popup) before clicking
            async with context.expect_page(timeout=30000) as new_page_info:
                await pdf_button.click()
                add_log("info", "Button clicked, waiting for new tab to open...")
            
            new_page = await new_page_info.value
            add_log("info", f"New tab opened with initial URL: {new_page.url}")
            
            # Wait for the PDF page to fully load
            max_wait_time = 45  # Maximum 45 seconds to wait
            wait_interval = 3   # Check every 3 seconds
            elapsed = 0
            
            while elapsed < max_wait_time:
                await asyncio.sleep(wait_interval)
                elapsed += wait_interval
                
                try:
                    current_pdf_url = new_page.url
                    add_log("info", f"PDF tab URL ({elapsed}s): {current_pdf_url}")
                    
                    # Check if URL is a valid PDF URL
                    if current_pdf_url and current_pdf_url not in ["about:blank", "", "about:srcdoc"]:
                        # Check for PDF indicators - specifically Azure Blob Storage URL for ConEd
                        url_lower = current_pdf_url.lower()
                        if ('blob.core.windows.net' in url_lower or  # Azure Blob Storage
                            'cecony-bill' in url_lower or  # ConEd bill container
                            '.pdf' in url_lower or
                            'pdf' in url_lower or 
                            'document' in url_lower or
                            'viewbill' in url_lower or
                            len(current_pdf_url) > 100):  # Long URLs usually mean actual content
                            pdf_url = current_pdf_url
                            add_log("success", f"PDF URL captured: {pdf_url[:100]}...")
                            break
                    
                    # Also try to get any redirected URL from page content
                    try:
                        # Check for meta refresh or JavaScript redirect
                        meta_refresh = await new_page.locator('meta[http-equiv="refresh"]').get_attribute('content')
                        if meta_refresh and 'url=' in meta_refresh.lower():
                            redirect_url = meta_refresh.split('url=')[-1].strip()
                            if redirect_url:
                                add_log("info", f"Found meta refresh URL: {redirect_url}")
                                pdf_url = redirect_url if redirect_url.startswith('http') else f"https://www.coned.com{redirect_url}"
                                break
                    except:
                        pass
                    
                except Exception as e:
                    add_log("debug", f"Error checking PDF URL: {str(e)}")
                
                await take_live_preview(new_page, f"Waiting for PDF ({elapsed}s)")
            
            if not pdf_url:
                add_log("warning", f"PDF URL did not load within {max_wait_time} seconds")
            
            # Close the PDF tab
            try:
                await new_page.close()
                add_log("info", "Closed PDF tab")
            except:
                pass
                
        except Exception as e:
            add_log("warning", f"Click approach failed: {str(e)}")
        
    except Exception as e:
        error_msg = f"Error scraping PDF URL: {str(e)}"
        add_log("warning", error_msg)
        logger.warning(error_msg)
    
    # If we captured a URL, download the PDF
    if pdf_url:
        download_success = await download_pdf_from_url(pdf_url)
        if download_success:
            # Return a local path indicator instead of the expiring URL
            return "local:latest_bill.pdf"
        else:
            # Return the URL anyway as fallback
            return pdf_url
    
    return pdf_url

async def scrape_bill_history(page):
    """
    Scrape bill history ledger from ConEd bill history page.
    Navigates to bill history page, clicks Payments checkbox, and parses ledger.
    """
    import time
    bill_history = {
        "ledger": [],
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        bill_history_url = "https://www.coned.com/en/accounts-billing/my-account/bill-history-assistance"
        add_log("info", f"Navigating to bill history page: {bill_history_url}")
        
        await page.goto(bill_history_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # Wait for page to load
        
        # Click the Payments checkbox using xpath
        add_log("info", "Looking for Payments checkbox...")
        try:
            # Try xpath first
            payments_checkbox_xpath = '/html/body/div[3]/div[3]/div[3]/div[5]/div/div[1]/div/div/div/div/div[2]/div/label[1]'
            checkbox_selectors = [
                f'xpath={payments_checkbox_xpath}',
                'input#payments-check',
                'input[name="paymentscheck"]',
                'label:has-text("Payments")',
                '.js-check-payments'
            ]
            
            checkbox_found = False
            for selector in checkbox_selectors:
                try:
                    if selector.startswith('xpath='):
                        element = page.locator(selector)
                    else:
                        element = page.locator(selector).first
                    
                    count = await element.count()
                    if count > 0:
                        await element.wait_for(state="visible", timeout=5000)
                        await element.click()
                        add_log("success", "Clicked Payments checkbox")
                        checkbox_found = True
                        break
                except Exception as e:
                    add_log("info", f"Checkbox selector {selector} failed: {str(e)}, trying next...")
                    continue
            
            if not checkbox_found:
                add_log("warning", "Could not find Payments checkbox")
                return bill_history
            
            # Wait for ledger to load after clicking checkbox
            await asyncio.sleep(3)
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Parse the ledger items
            add_log("info", "Parsing bill history ledger...")
            
            # Find all ledger items - both payments and bills
            # Use more specific selectors based on the HTML structure
            payment_items = await page.locator('.billing-payment-item--received, .js-payment-item').all()
            bill_items = await page.locator('.js-bill-item, .billing-payment-item--bill').all()
            
            add_log("info", f"Found {len(payment_items)} payment items and {len(bill_items)} bill items")
            
            # Process payment items
            for item in payment_items:
                try:
                    item_data = {"type": "payment"}
                    
                    # Get bill cycle date
                    date_element = item.locator('.billing-payment-item__date .billing-payment-item__focus').first
                    if await date_element.count() > 0:
                        date_text = await date_element.inner_text()
                        date_text = date_text.replace('Bill Cycle:', '').replace('visually-hidden', '').strip()
                        # Clean up - remove any hidden text
                        date_text = ' '.join(date_text.split()).strip()
                        item_data["bill_cycle_date"] = date_text
                    
                    # Get payment description and extract payment date
                    received_element = item.locator('.billing-payment-item__received').first
                    if await received_element.count() > 0:
                        description_text = (await received_element.inner_text()).strip()
                        item_data["description"] = description_text
                        
                        # Try to extract payment date from description (e.g., "Payment Received 1/23/2026")
                        import re
                        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', description_text)
                        if date_match:
                            item_data["payment_date"] = date_match.group(1)
                    else:
                        item_data["description"] = "Payment Received"
                    
                    # Try to get payment date from data attribute if available
                    payment_link = item.locator('a[data-payment-date]').first
                    if await payment_link.count() > 0:
                        payment_date = await payment_link.get_attribute('data-payment-date')
                        if payment_date:
                            item_data["payment_date"] = payment_date
                    
                    # Get payment amount
                    amount_element = item.locator('.billing-payment-item__total-received').first
                    if await amount_element.count() > 0:
                        amount_text = await amount_element.inner_text()
                        item_data["amount"] = amount_text.strip()
                    
                    if item_data.get("bill_cycle_date") or item_data.get("amount"):
                        bill_history["ledger"].append(item_data)
                        payment_info = f"Added payment: {item_data.get('amount')}"
                        if item_data.get("payment_date"):
                            payment_info += f" on {item_data.get('payment_date')}"
                        elif item_data.get("bill_cycle_date"):
                            payment_info += f" (bill cycle: {item_data.get('bill_cycle_date')})"
                        add_log("info", payment_info)
                        
                except Exception as e:
                    add_log("warning", f"Error parsing payment item: {str(e)}")
                    continue
            
            # Process bill items
            for item in bill_items:
                try:
                    item_data = {"type": "bill"}
                    
                    # Get bill cycle date
                    date_element = item.locator('.billing-payment-item__date .billing-payment-item__focus').first
                    if await date_element.count() > 0:
                        date_text = await date_element.inner_text()
                        date_text = date_text.replace('Bill Cycle:', '').replace('visually-hidden', '').strip()
                        date_text = ' '.join(date_text.split()).strip()
                        item_data["bill_cycle_date"] = date_text
                    
                    # Get month range
                    months_element = item.locator('.billing-payment-item__months').first
                    if await months_element.count() > 0:
                        months_text = await months_element.inner_text()
                        item_data["month_range"] = months_text.strip()
                    
                    # Get bill total amount
                    total_element = item.locator('.billing-payment-item__total-amount').first
                    if await total_element.count() > 0:
                        total_text = await total_element.inner_text()
                        item_data["bill_total"] = total_text.strip()
                    
                    # Get bill date from data attribute if available
                    bill_link = item.locator('a.js-bill-link[data-bill-date]').first
                    if await bill_link.count() > 0:
                        bill_date = await bill_link.get_attribute('data-bill-date')
                        if bill_date:
                            item_data["bill_date"] = bill_date
                    
                    if item_data.get("bill_cycle_date") or item_data.get("bill_total"):
                        bill_history["ledger"].append(item_data)
                        add_log("info", f"Added bill: {item_data.get('bill_total')} for {item_data.get('month_range')}")
                        
                except Exception as e:
                    add_log("warning", f"Error parsing bill item: {str(e)}")
                    continue
            
            add_log("success", f"Parsed {len(bill_history['ledger'])} ledger entries")
            
        except Exception as e:
            error_msg = f"Error scraping bill history: {str(e)}"
            add_log("error", error_msg)
            logger.error(error_msg)
            bill_history["error"] = str(e)
            
    except Exception as e:
        error_msg = f"Error navigating to bill history page: {str(e)}"
        add_log("error", error_msg)
        logger.error(error_msg)
        bill_history["error"] = str(e)
    
    return bill_history
