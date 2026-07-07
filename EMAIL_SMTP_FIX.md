# Email SMTP Fix Documentation

## Summary of Changes

The email SMTP service has been enhanced with:

### 1. **Improved Error Handling**
- Specific handling for different SMTP error types (authentication, timeout, connection)
- Detailed exception logging with full tracebacks
- Better error messages that guide troubleshooting

### 2. **Automatic Retry Logic**
- Transient errors (timeouts, server temporarily unavailable) trigger automatic retries
- Up to 2 retry attempts (configurable via `MAX_RETRIES`)
- 2-second delay between retries to allow server recovery

### 3. **Enhanced Configuration Validation**
- Validates SMTP credentials format before attempting connection
- Checks for missing configuration values
- Validates email address format

### 4. **Better Logging**
- Debug-level logging for connection stages
- Clear success/failure indicators (✓/✗)
- Signal log tracks each attempt with timestamps

### 5. **SSL/TLS Improvements**
- Explicit SSL context creation for secure connections
- Uses Port 465 (SMTP_SSL) for best compatibility with Gmail
- 30-second connection timeout (configurable)

### 6. **Diagnostic Tool**
- New `test_smtp.py` script for troubleshooting
- Tests DNS resolution, TCP connectivity, SMTP connection, and authentication
- Provides actionable troubleshooting steps for common issues

## Configuration Requirements

**File:** `ai_orchestration/core/config.py`

```python
SMTP_HOST = "smtp.gmail.com"      # Gmail SMTP server
SMTP_PORT = 465                    # SSL port
SMTP_USER = "your-email@gmail.com" # Your Gmail address
SMTP_PASS = "xxxx xxxx xxxx xxxx"  # Google App Password (16 chars)
```

## Getting Gmail App Password

1. Enable 2-Factor Authentication on your Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" and "Windows Computer"
4. Google will generate a 16-character password
5. Copy the password (spaces included) and set it as `SMTP_PASS`

⚠️ **IMPORTANT:** Use the **App Password**, not your regular Gmail password

## Testing Email Configuration

### Method 1: Using the Diagnostic Script

```bash
python test_smtp.py
```

This will:
- ✓ Verify all configuration values
- ✓ Test DNS resolution for `smtp.gmail.com`
- ✓ Test TCP connectivity to port 465
- ✓ Test SMTP connection
- ✓ Test authentication credentials
- ✓ Optionally send a test email

### Method 2: Check Logs

Monitor email delivery in real-time:

```bash
# On Windows PowerShell:
Get-Content neural_signals.log -Wait -Tail 50

# Or on terminal:
tail -f neural_signals.log
```

Look for patterns:
- `SUCCESS signal` = Email sent successfully
- `FAILED signal` = Delivery failed (see error details)
- `AUTH_FAILED` = Credentials incorrect
- `TIMEOUT` = Connection timeout

## Common Issues and Fixes

### Issue: "Authentication failed"
**Cause:** Incorrect SMTP_PASS or regular Gmail password used
**Fix:** 
1. Generate an App Password: https://myaccount.google.com/apppasswords
2. Update `SMTP_PASS` in config.py
3. Run `python test_smtp.py` to verify

### Issue: "Connection timeout"
**Cause:** Network or firewall blocking port 465
**Fix:**
1. Check firewall settings
2. Test with: `python test_smtp.py`
3. If DNS fails, try: `nslookup smtp.gmail.com`
4. Increase `SMTP_TIMEOUT` in mail_service.py if needed

### Issue: "Temporarily unavailable"
**Cause:** Gmail server rate-limiting or temporary issue
**Fix:**
1. The system will automatically retry (up to 2 times)
2. Check `neural_signals.log` for eventual SUCCESS
3. Gmail typically recovers within minutes

### Issue: No errors but emails not received
**Cause:** Emails going to spam/promotion folder
**Fix:**
1. Check Gmail spam/promotion folders
2. Mark Signly emails as "Not Spam"
3. Add sender to contacts
4. Check if email domain is blacklisted

## Configuration Variables

Added to `ai_orchestration/services/mail_service.py`:

```python
SMTP_TIMEOUT = 30       # Connection timeout in seconds
MAX_RETRIES = 2         # Number of retry attempts
RETRY_DELAY = 2         # Delay between retries in seconds
SIGNAL_LOG = "neural_signals.log"  # Log file location
```

These can be adjusted if needed:
- Increase `SMTP_TIMEOUT` for slow networks
- Increase `MAX_RETRIES` for flaky connections
- Decrease `RETRY_DELAY` for faster retry

## Files Modified

1. **ai_orchestration/services/mail_service.py**
   - Enhanced `_send_sync()` with error handling and retries
   - Improved `send_verification_signal()` with better logging
   - Improved `send_welcome_signal()` with better logging
   - Added `diagnose_smtp_config()` diagnostic function

2. **test_smtp.py** (NEW)
   - Comprehensive SMTP testing tool
   - Interactive test email sending
   - Troubleshooting guidance

## Monitoring Email Delivery

### Check Recent Logs
```bash
# Last 20 email attempts
Get-Content neural_signals.log -Tail 20

# Success rate
(Get-Content neural_signals.log | Select-String "SUCCESS").Count
(Get-Content neural_signals.log | Select-String "FAILED").Count
```

### Application Logs
Email delivery details are also logged to:
- Application logger: "Signly_Mail"
- Check your main application logs for detailed SMTP traces

## API Integration

The email functions maintain the same interface:

```python
# Send verification code
await send_verification_signal(email, otp_code, "registration")

# Send welcome email
await send_welcome_signal(email, user_name)
```

All error handling is now internal - these functions return `True` (success) or `False` (failure).

## Next Steps

1. ✓ **Verify Configuration:** Run `python test_smtp.py`
2. ✓ **Test Email Delivery:** Send a test email via the diagnostic script
3. ✓ **Monitor Logs:** Watch `neural_signals.log` for delivery status
4. ✓ **Check Spam Folder:** Ensure emails aren't being filtered
5. ✓ **Review Logs on Errors:** Look for specific error types above

---

**Need Help?** 
- Check application logs for detailed SMTP error traces
- Run diagnostic script for connection troubleshooting  
- Verify Gmail App Password at https://myaccount.google.com/apppasswords
