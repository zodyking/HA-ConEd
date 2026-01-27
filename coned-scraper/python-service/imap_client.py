"""
IMAP client for fetching ConEd payment confirmation emails
Extracts card last 4 digits for automatic payment attribution

STRICT CRITERIA:
- Only emails FROM: DoNotReply@billmatrix.com
- Only emails with exact SUBJECT from config (e.g., "Con Edison Payment Processed")
- Only emails in the specified Gmail label
- Extracts card from "Card Number ending in: XXXX" pattern
"""
import imaplib
import email
from email.header import decode_header
import quopri
import re
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Config file path
IMAP_CONFIG_FILE = Path("./data") / "imap_config.json"

# STRICT: Only accept emails from this sender
CONED_PAYMENT_SENDER = "DoNotReply@billmatrix.com"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_imap_config() -> Dict[str, Any]:
    """Load IMAP configuration"""
    if IMAP_CONFIG_FILE.exists():
        with open(IMAP_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_imap_config(config: Dict[str, Any]):
    """Save IMAP configuration"""
    IMAP_CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(IMAP_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def test_imap_connection(server: str, port: int, email_addr: str, password: str, use_ssl: bool = True, gmail_label: str = None) -> Dict[str, Any]:
    """Test IMAP connection with provided credentials"""
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(server, port)
        else:
            mail = imaplib.IMAP4(server, port)
        
        mail.login(email_addr, password)
        
        # List available folders/labels
        status, folders = mail.list()
        folder_list = []
        if status == 'OK':
            for f in folders:
                # Parse folder name from response
                match = re.search(r'"([^"]+)"$', f.decode() if isinstance(f, bytes) else f)
                if match:
                    folder_list.append(match.group(1))
        
        # Try to select the specified Gmail label if provided
        label_exists = False
        if gmail_label:
            # Gmail labels are accessed as folders
            try:
                status, data = mail.select(f'"{gmail_label}"')
                label_exists = status == 'OK'
            except:
                pass
        
        mail.select('INBOX')
        status, data = mail.status('INBOX', '(MESSAGES UNSEEN)')
        mail.logout()
        
        result = {
            'success': True,
            'message': 'Connection successful!',
            'mailbox_status': data[0].decode() if data else None,
            'available_folders': folder_list[:20]  # Limit to first 20
        }
        
        if gmail_label:
            result['label_exists'] = label_exists
            if not label_exists:
                result['message'] = f'Connected, but Gmail label "{gmail_label}" not found'
        
        return result
    except imaplib.IMAP4.error as e:
        return {
            'success': False,
            'message': f'IMAP error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Connection failed: {str(e)}'
        }

def decode_email_body(msg) -> str:
    """Properly decode email body including quoted-printable encoding"""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type in ('text/plain', 'text/html'):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        decoded = payload.decode(charset, errors='replace')
                        
                        # Handle quoted-printable encoded content
                        # Replace =0A with newlines, =3D with =, etc.
                        decoded = decoded.replace('=0A', '\n')
                        decoded = decoded.replace('=0D', '\r')
                        decoded = decoded.replace('=3D', '=')
                        
                        if content_type == 'text/html':
                            # Strip HTML tags
                            decoded = re.sub(r'<[^>]+>', ' ', decoded)
                        
                        body += decoded + "\n"
                except Exception as e:
                    logger.debug(f"Failed to decode part: {e}")
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='replace')
                
                # Handle quoted-printable
                body = body.replace('=0A', '\n')
                body = body.replace('=0D', '\r')
                body = body.replace('=3D', '=')
        except Exception as e:
            logger.debug(f"Failed to decode body: {e}")
    
    return body

def extract_card_from_email(email_body: str) -> Optional[str]:
    """
    Extract card last 4 digits from ConEd payment confirmation email
    
    STRICT: Only looks for "Card Number ending in: XXXX" pattern
    from BillMatrix emails
    """
    # Primary pattern from BillMatrix ConEd emails
    # Example: "Card Number ending in: 7545"
    patterns = [
        r'Card Number ending in[:\s]*(\d{4})',  # Primary: "Card Number ending in: 7545"
        r'Card Number ending\s*in[:\s]*(\d{4})',  # Handle line breaks
    ]
    
    for pattern in patterns:
        match = re.search(pattern, email_body, re.IGNORECASE | re.MULTILINE)
        if match:
            card_last_four = match.group(1)
            if len(card_last_four) == 4 and card_last_four.isdigit():
                logger.info(f"Extracted card ending: *{card_last_four}")
                return card_last_four
    
    # Fallback: Also check for "Wallet: Visa *XXXX" format (also in BillMatrix emails)
    wallet_match = re.search(r'Wallet:\s*\w+\s*\*(\d{4})', email_body, re.IGNORECASE)
    if wallet_match:
        card = wallet_match.group(1)
        if len(card) == 4 and card.isdigit():
            logger.info(f"Extracted card from wallet: *{card}")
            return card
    
    return None

def extract_payment_amount(email_body: str) -> Optional[str]:
    """Extract payment amount from email"""
    # Look for specific BillMatrix patterns
    patterns = [
        r'payment[^$]*\$\s*([\d,]+\.?\d*)',  # "payment ... of $248.50"
        r'Payment Amount[:\s]*\$\s*([\d,]+\.?\d*)',  # "Payment Amount: $248.50"
        r'\$\s*([\d,]+\.\d{2})',  # Any dollar amount with cents
    ]
    
    for pattern in patterns:
        match = re.search(pattern, email_body, re.IGNORECASE)
        if match:
            amount = match.group(1).replace(',', '')
            try:
                float(amount)
                return f"${amount}"
            except ValueError:
                continue
    
    return None

def extract_payment_date(email_body: str, email_date: datetime) -> str:
    """Extract payment date from email or use email date"""
    # Look for date patterns in BillMatrix format
    patterns = [
        r'made on\s*(\d{1,2}/\d{1,2}/\d{4})',  # "made on 01/24/2026"
        r'(\d{1,2}/\d{1,2}/\d{4})',  # Generic MM/DD/YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, email_body)
        if match:
            return match.group(1)
    
    # Fallback to email received date
    return email_date.strftime('%m/%d/%Y')

def fetch_coned_payment_emails(
    server: str,
    port: int,
    email_addr: str,
    password: str,
    use_ssl: bool = True,
    gmail_label: str = None,
    subject_filter: str = None
) -> List[Dict[str, Any]]:
    """
    Fetch ConEd payment confirmation emails with STRICT criteria:
    - FROM: DoNotReply@billmatrix.com
    - SUBJECT: exact match from config (e.g., "Con Edison Payment Processed")
    - LABEL: specified Gmail label
    
    Returns list of payment info:
    [
        {
            'card_last_four': '7545',
            'amount': '$248.50',
            'date': '01/24/2026',
            'email_date': '2026-01-24T16:01:42',
            'subject': 'Con Edison Payment Processed'
        }
    ]
    """
    results = []
    
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(server, port)
        else:
            mail = imaplib.IMAP4(server, port)
        
        mail.login(email_addr, password)
        
        # List all available folders/labels for debugging
        status, folder_list = mail.list()
        if status == 'OK':
            available_folders = []
            for f in folder_list:
                try:
                    decoded = f.decode() if isinstance(f, bytes) else f
                    available_folders.append(decoded)
                except:
                    pass
            logger.info(f"Available folders: {available_folders[:10]}...")  # Show first 10
        
        # Select the Gmail label if specified, otherwise INBOX
        folder_selected = 'INBOX'
        folder_msg_count = 0
        
        if gmail_label:
            # Gmail labels need special handling
            # Try multiple formats - Gmail can be picky
            folder_attempts = [
                gmail_label,                           # Direct: ConEd
                f'"{gmail_label}"',                    # Quoted: "ConEd"
                gmail_label.replace(' ', '-'),         # Dashes: Con-Ed  
                f'INBOX/{gmail_label}',                # Nested: INBOX/ConEd
                f'[Gmail]/{gmail_label}',              # Gmail system: [Gmail]/ConEd
            ]
            
            for folder in folder_attempts:
                try:
                    # Use select to get message count
                    status, data = mail.select(folder)
                    if status == 'OK':
                        folder_selected = folder
                        # data[0] contains message count
                        folder_msg_count = int(data[0]) if data and data[0] else 0
                        logger.info(f"SUCCESS: Selected folder '{folder}' with {folder_msg_count} messages")
                        break
                except Exception as e:
                    logger.debug(f"Could not select folder '{folder}': {e}")
            else:
                logger.warning(f"Could not find Gmail label '{gmail_label}', falling back to INBOX")
                status, data = mail.select('INBOX')
                folder_msg_count = int(data[0]) if data and data[0] else 0
        else:
            status, data = mail.select('INBOX')
            folder_msg_count = int(data[0]) if data and data[0] else 0
        
        logger.info(f"Working with folder: {folder_selected} ({folder_msg_count} total messages)")
        
        # Search ALL emails in the folder - do filtering in Python for reliability
        # Gmail IMAP search is notoriously unreliable for complex queries
        status, data = mail.search(None, 'ALL')
        if status != 'OK' or not data[0]:
            logger.info(f"No emails found in {folder_selected}")
            mail.logout()
            return results
        
        email_ids = data[0].split()
        logger.info(f"Fetching {len(email_ids)} emails from {folder_selected} for processing...")
        
        processed = 0
        skipped_sender = 0
        skipped_subject = 0
        
        for email_id in email_ids:
            try:
                status, data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Get sender
                from_addr = msg.get('From', '')
                
                # STRICT: Only accept emails from DoNotReply@billmatrix.com
                if CONED_PAYMENT_SENDER.lower() not in from_addr.lower():
                    skipped_sender += 1
                    continue
                
                # Get subject
                subject_raw = msg.get('Subject', '')
                subject, encoding = decode_header(subject_raw)[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or 'utf-8', errors='replace')
                
                # STRICT: Subject must contain the filter text
                if subject_filter and subject_filter.lower() not in subject.lower():
                    skipped_subject += 1
                    continue
                
                processed += 1
                
                # Get email date
                email_date_str = msg.get('Date', '')
                try:
                    email_date = email.utils.parsedate_to_datetime(email_date_str)
                except:
                    email_date = datetime.now(timezone.utc)
                
                # Decode email body properly
                body = decode_email_body(msg)
                
                if not body:
                    logger.warning(f"Empty body for email {email_id}")
                    continue
                
                # Extract card info using strict pattern
                card_last_four = extract_card_from_email(body)
                amount = extract_payment_amount(body)
                payment_date = extract_payment_date(body, email_date)
                
                if card_last_four:
                    results.append({
                        'card_last_four': card_last_four,
                        'amount': amount,
                        'date': payment_date,
                        'email_date': email_date.isoformat(),
                        'subject': subject,
                        'email_id': email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                    })
                    logger.info(f"Extracted payment: {amount} on {payment_date}, card *{card_last_four}")
                else:
                    logger.warning(f"Could not extract card number from email: {subject}")
                    
            except Exception as e:
                logger.warning(f"Failed to process email {email_id}: {e}")
        
        logger.info(f"=== EMAIL SCAN RESULTS ===")
        logger.info(f"Folder: {folder_selected}")
        logger.info(f"Total emails scanned: {len(email_ids)}")
        logger.info(f"From BillMatrix (DoNotReply@billmatrix.com): {processed}")
        logger.info(f"Skipped - wrong sender: {skipped_sender}")
        logger.info(f"Skipped - wrong subject: {skipped_subject}")
        logger.info(f"Payment emails with card numbers extracted: {len(results)}")
        mail.logout()
        
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        raise
    
    return results

def match_payments_to_emails(email_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Match email payment info to database payments and auto-attribute
    
    Matching logic:
    1. Find unverified payments in database
    2. For each payment, look for email with matching amount
    3. If card number found in email, look up user by card and attribute
    4. If no card match, use default payee if configured
    
    Returns stats about matches made
    """
    from database import get_unverified_payments, attribute_payment, get_user_by_card, get_default_payee
    
    stats = {
        'emails_processed': len(email_data),
        'payments_checked': 0,
        'matched_by_card': 0,
        'matched_by_default': 0,
        'unmatched': 0,
        'details': []
    }
    
    unverified = get_unverified_payments(limit=100)
    stats['payments_checked'] = len(unverified)
    
    logger.info(f"Processing {len(email_data)} emails against {len(unverified)} unverified payments")
    
    for payment in unverified:
        matched = False
        payment_amount = payment.get('amount', '').replace('$', '').replace(',', '').strip()
        payment_date = payment.get('payment_date', '')
        
        # Try to find matching email by amount
        for email_info in email_data:
            email_amount = (email_info.get('amount') or '').replace('$', '').replace(',', '').strip()
            
            if payment_amount and email_amount:
                try:
                    if abs(float(payment_amount) - float(email_amount)) < 0.01:
                        # Amount matches! Get card info
                        card_last_four = email_info.get('card_last_four')
                        
                        if card_last_four:
                            # Find user by card
                            user = get_user_by_card(card_last_four)
                            if user:
                                attribute_payment(
                                    payment['id'],
                                    user['id'],
                                    method='email_card',
                                    card_last_four=card_last_four
                                )
                                stats['matched_by_card'] += 1
                                stats['details'].append({
                                    'payment_id': payment['id'],
                                    'amount': payment_amount,
                                    'card': f"*{card_last_four}",
                                    'user': user['name'],
                                    'method': 'email_card'
                                })
                                matched = True
                                logger.info(f"Matched payment ${payment_amount} to user {user['name']} via card *{card_last_four}")
                                break
                            else:
                                logger.warning(f"Card *{card_last_four} not registered to any user")
                except (ValueError, TypeError) as e:
                    logger.debug(f"Amount comparison error: {e}")
                    continue
        
        if not matched:
            # No card match - try default payee
            default_payee = get_default_payee()
            if default_payee:
                attribute_payment(
                    payment['id'],
                    default_payee['id'],
                    method='default_rule',
                    card_last_four=None
                )
                stats['matched_by_default'] += 1
                stats['details'].append({
                    'payment_id': payment['id'],
                    'amount': payment_amount,
                    'user': default_payee['name'],
                    'method': 'default_rule'
                })
                matched = True
                logger.info(f"Assigned payment ${payment_amount} to default user {default_payee['name']}")
        
        if not matched:
            stats['unmatched'] += 1
            logger.info(f"Could not match payment ${payment_amount} from {payment_date}")
    
    return stats

def run_email_sync() -> Dict[str, Any]:
    """
    Run the full email sync process with strict criteria:
    - FROM: DoNotReply@billmatrix.com
    - SUBJECT: from config (e.g., "Con Edison Payment Processed")
    - LABEL: Gmail label from config
    """
    config = load_imap_config()
    
    if not config.get('enabled') or not config.get('server'):
        return {
            'success': False,
            'message': 'IMAP not configured or not enabled'
        }
    
    try:
        # Fetch emails with STRICT criteria
        emails = fetch_coned_payment_emails(
            server=config['server'],
            port=config.get('port', 993),
            email_addr=config['email'],
            password=config['password'],
            use_ssl=config.get('use_ssl', True),
            gmail_label=config.get('gmail_label'),  # Gmail label to search
            subject_filter=config.get('subject_filter')  # Exact subject filter
        )
        
        logger.info(f"Fetched {len(emails)} payment confirmation emails")
        
        # Match to payments
        stats = match_payments_to_emails(emails)
        
        # Update last sync time
        config['last_sync'] = utc_now_iso()
        config['last_sync_stats'] = stats
        save_imap_config(config)
        
        return {
            'success': True,
            'message': f"Found {len(emails)} payment emails, matched {stats['matched_by_card']} by card, {stats['matched_by_default']} by default",
            'emails_found': len(emails),
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Email sync failed: {e}")
        return {
            'success': False,
            'message': str(e)
        }

def preview_email_search(
    server: str,
    port: int,
    email_addr: str,
    password: str,
    use_ssl: bool = True,
    gmail_label: str = None,
    subject_filter: str = None,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Preview what emails would be found with the current search criteria
    Useful for testing/debugging IMAP settings
    """
    try:
        emails = fetch_coned_payment_emails(
            server=server,
            port=port,
            email_addr=email_addr,
            password=password,
            use_ssl=use_ssl,
            gmail_label=gmail_label,
            subject_filter=subject_filter
        )
        
        return {
            'success': True,
            'emails_found': len(emails),
            'preview': emails[:limit],
            'search_criteria': {
                'sender': CONED_PAYMENT_SENDER,
                'label': gmail_label,
                'subject': subject_filter
            }
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }


