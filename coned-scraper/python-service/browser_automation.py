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

# Single screenshot filename that gets overwritten each scrape
# Captures the page state where account balance was found
SCREENSHOT_FILENAME = "account_balance.png"

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
            
            # Check if login was successful
            current_url = page.url
            
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
                    
                    scraped_data = await scrape_account_data(page, context)
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
                screenshot_path = Path(__file__).parent / SCREENSHOT_FILENAME
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
                    
                    # Get payment description
                    received_element = item.locator('.billing-payment-item__received').first
                    if await received_element.count() > 0:
                        item_data["description"] = (await received_element.inner_text()).strip()
                    else:
                        item_data["description"] = "Payment Received"
                    
                    # Get payment amount
                    amount_element = item.locator('.billing-payment-item__total-received').first
                    if await amount_element.count() > 0:
                        amount_text = await amount_element.inner_text()
                        item_data["amount"] = amount_text.strip()
                    
                    if item_data.get("bill_cycle_date") or item_data.get("amount"):
                        bill_history["ledger"].append(item_data)
                        add_log("info", f"Added payment: {item_data.get('amount')} on {item_data.get('bill_cycle_date')}")
                        
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
