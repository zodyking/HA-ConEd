"""
IMAP client for fetching ConEd payment confirmation emails
Extracts card last 4 digits for automatic payment attribution
"""
import imaplib
import email
from email.header import decode_header
import re
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Config file path
IMAP_CONFIG_FILE = Path("./data") / "imap_config.json"

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

def test_imap_connection(server: str, port: int, email_addr: str, password: str, use_ssl: bool = True) -> Dict[str, Any]:
    """Test IMAP connection with provided credentials"""
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(server, port)
        else:
            mail = imaplib.IMAP4(server, port)
        
        mail.login(email_addr, password)
        mail.select('INBOX')
        
        # Get mailbox status
        status, data = mail.status('INBOX', '(MESSAGES UNSEEN)')
        mail.logout()
        
        return {
            'success': True,
            'message': 'Connection successful!',
            'mailbox_status': data[0].decode() if data else None
        }
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

def extract_card_from_email(email_body: str) -> Optional[str]:
    """Extract card last 4 digits from ConEd payment confirmation email"""
    # Patterns to look for card numbers
    patterns = [
        r'Card Number ending in[:\s]*\*?(\d{4})',
        r'Wallet:\s*\w+\s*\*(\d{4})',
        r'Card ending in[:\s]*\*?(\d{4})',
        r'ending in[:\s]*\*?(\d{4})',
        r'card[:\s]*\*+(\d{4})',
        r'Visa\s*\*(\d{4})',
        r'Mastercard\s*\*(\d{4})',
        r'Amex\s*\*(\d{4})',
        r'Discover\s*\*(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, email_body, re.IGNORECASE)
        if match:
            card_last_four = match.group(1)
            # Exclude account numbers (typically longer patterns we don't want)
            # Also exclude confirmation numbers
            if len(card_last_four) == 4:
                return card_last_four
    
    return None

def extract_payment_amount(email_body: str) -> Optional[str]:
    """Extract payment amount from email"""
    patterns = [
        r'\$\s*([\d,]+\.?\d*)',
        r'amount[:\s]*\$?\s*([\d,]+\.?\d*)',
        r'payment of[:\s]*\$?\s*([\d,]+\.?\d*)',
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
    # Try to find date in email body
    patterns = [
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}-\d{1,2}-\d{4})',
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
    days_back: int = 30,
    folder: str = 'INBOX'
) -> List[Dict[str, Any]]:
    """
    Fetch ConEd payment confirmation emails and extract card info
    
    Returns list of payment info:
    [
        {
            'card_last_four': '7545',
            'amount': '$248.50',
            'date': '1/24/2026',
            'email_date': '2026-01-24T10:30:00',
            'subject': 'Payment Confirmation'
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
        mail.select(folder)
        
        # Search for ConEd payment emails
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')
        
        # Search criteria for ConEd payment emails
        search_criteria = [
            f'(FROM "coned" SINCE {since_date})',
            f'(FROM "billmatrix" SINCE {since_date})',
            f'(SUBJECT "payment" FROM "consolidated" SINCE {since_date})',
            f'(SUBJECT "payment confirmation" SINCE {since_date})',
        ]
        
        email_ids = set()
        for criteria in search_criteria:
            try:
                status, data = mail.search(None, criteria)
                if status == 'OK' and data[0]:
                    email_ids.update(data[0].split())
            except Exception as e:
                logger.debug(f"Search criteria failed: {criteria}, error: {e}")
        
        for email_id in email_ids:
            try:
                status, data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Get email date
                email_date_str = msg.get('Date', '')
                try:
                    email_date = email.utils.parsedate_to_datetime(email_date_str)
                except:
                    email_date = datetime.now()
                
                # Get subject
                subject, encoding = decode_header(msg.get('Subject', ''))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or 'utf-8', errors='replace')
                
                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == 'text/plain':
                            try:
                                body += part.get_payload(decode=True).decode('utf-8', errors='replace')
                            except:
                                pass
                        elif content_type == 'text/html':
                            try:
                                html = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                # Strip HTML tags for searching
                                body += re.sub(r'<[^>]+>', ' ', html)
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                    except:
                        pass
                
                # Check if this is a payment confirmation
                if not any(kw in body.lower() for kw in ['payment', 'received', 'confirmation', 'thank you']):
                    continue
                
                # Extract card info
                card_last_four = extract_card_from_email(body)
                amount = extract_payment_amount(body)
                payment_date = extract_payment_date(body, email_date)
                
                if card_last_four or amount:
                    results.append({
                        'card_last_four': card_last_four,
                        'amount': amount,
                        'date': payment_date,
                        'email_date': email_date.isoformat(),
                        'subject': subject,
                        'email_id': email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                    })
            except Exception as e:
                logger.warning(f"Failed to process email {email_id}: {e}")
        
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
    
    Returns stats about matches made
    """
    from database import get_unverified_payments, attribute_payment, get_user_by_card, get_default_payee
    
    stats = {
        'emails_processed': len(email_data),
        'matched_by_card': 0,
        'matched_by_default': 0,
        'unmatched': 0
    }
    
    unverified = get_unverified_payments(limit=100)
    
    for payment in unverified:
        matched = False
        
        # Try to find matching email by amount and date
        for email_info in email_data:
            # Compare amounts (strip $ and whitespace)
            payment_amount = payment.get('amount', '').replace('$', '').replace(',', '').strip()
            email_amount = (email_info.get('amount') or '').replace('$', '').replace(',', '').strip()
            
            if payment_amount and email_amount:
                try:
                    if abs(float(payment_amount) - float(email_amount)) < 0.01:
                        # Amount matches, check if card info available
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
                                matched = True
                                break
                except (ValueError, TypeError):
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
                matched = True
        
        if not matched:
            stats['unmatched'] += 1
    
    return stats

def run_email_sync() -> Dict[str, Any]:
    """Run the full email sync process"""
    config = load_imap_config()
    
    if not config.get('enabled') or not config.get('server'):
        return {
            'success': False,
            'message': 'IMAP not configured'
        }
    
    try:
        # Fetch emails
        emails = fetch_coned_payment_emails(
            server=config['server'],
            port=config.get('port', 993),
            email_addr=config['email'],
            password=config['password'],
            use_ssl=config.get('use_ssl', True),
            days_back=config.get('days_back', 30)
        )
        
        # Match to payments
        stats = match_payments_to_emails(emails)
        
        # Update last sync time
        config['last_sync'] = utc_now_iso()
        config['last_sync_stats'] = stats
        save_imap_config(config)
        
        return {
            'success': True,
            'message': f"Synced {len(emails)} emails, {stats['matched_by_card']} matched by card",
            'stats': stats
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }

