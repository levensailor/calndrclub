# AWS SES Migration Guide

This guide explains the migration from SMTP to AWS SES for email delivery in the Calndr Club application.

## 🔄 What Changed

### Before (SMTP)
- Used direct SMTP connection with `smtplib`
- Required SMTP server credentials (host, port, username, password)
- Limited scalability and deliverability features

### After (AWS SES)
- Uses AWS Simple Email Service with `boto3`
- Better deliverability, reputation management, and analytics
- More reliable and scalable email delivery

## 🛠️ Setup Requirements

### 1. AWS Account Setup
1. Create an AWS account if you don't have one
2. Create an IAM user with SES permissions
3. Generate access keys for the IAM user

### 2. SES Permissions
The IAM user needs these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail",
                "ses:SendRawEmail",
                "ses:GetSendQuota",
                "ses:GetSendStatistics",
                "ses:ListVerifiedEmailAddresses",
                "ses:VerifyEmailIdentity",
                "ses:GetIdentityVerificationAttributes"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. Environment Variables
Update your `.env` file with these new variables:

```bash
# AWS SES Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
SES_SENDER_EMAIL=noreply@calndr.club
SES_SENDER_NAME=Calndr Club

# Remove old SMTP variables (no longer needed)
# SMTP_HOST=
# SMTP_PORT=
# SMTP_USER=
# SMTP_PASSWORD=
```

## 🚀 Quick Setup

### Option 1: Use the Setup Script
```bash
cd backend
python setup_ses.py
```

This script will:
- Check your AWS credentials
- Verify SES configuration
- List verified email addresses
- Help verify your sender email
- Set up configuration sets for tracking

### Option 2: Manual Setup

1. **Verify Sender Email**
   ```bash
   aws ses verify-email-identity --email-address noreply@calndr.club --region us-east-1
   ```

2. **Check Verification Status**
   ```bash
   aws ses get-identity-verification-attributes --identities noreply@calndr.club --region us-east-1
   ```

3. **Request Production Access** (if needed)
   - Go to AWS SES Console
   - Request to move out of sandbox mode
   - This allows sending to unverified email addresses

## 📧 Email Features

### Coparent Invitations
- Professional HTML templates
- Branded design with Calndr Club styling
- Clear call-to-action buttons
- Fallback plain text version

### Email Verification
- 6-digit verification codes
- 10-minute expiration
- Secure HTML formatting
- Mobile-friendly design

## 🔍 Monitoring & Analytics

### SES Metrics
- Bounce rates
- Complaint rates
- Delivery statistics
- Send quotas and limits

### CloudWatch Integration
The setup script creates a configuration set that sends metrics to CloudWatch for monitoring:
- Email sends
- Bounces
- Complaints
- Deliveries

## 🛡️ Security Best Practices

### 1. IAM Security
- Use least-privilege IAM policies
- Rotate access keys regularly
- Use IAM roles in production (EC2/ECS)

### 2. Email Reputation
- Monitor bounce rates (keep < 5%)
- Monitor complaint rates (keep < 0.1%)
- Use verified domains for better deliverability

### 3. Rate Limiting
- SES has built-in rate limiting
- Default: 14 emails/second in sandbox
- Higher limits available in production

## 🚨 Troubleshooting

### Common Issues

#### 1. "Email address not verified"
```
MessageRejected: Email address not verified
```
**Solution**: Verify the sender email address in SES console or use the setup script.

#### 2. "Account is in sandbox mode"
```
MessageRejected: Email address not verified. The following identities failed the check in region
```
**Solution**: Request production access in SES console.

#### 3. "Credentials not found"
```
NoCredentialsError: Unable to locate credentials
```
**Solution**: Check AWS credentials in environment variables or AWS credentials file.

#### 4. "Rate exceeded"
```
Throttling: Rate exceeded
```
**Solution**: Implement retry logic or request higher sending limits.

### Debug Mode
Enable debug logging in your application:
```python
import logging
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
```

## 📊 Migration Checklist

- [ ] AWS account created
- [ ] IAM user with SES permissions created
- [ ] Access keys generated
- [ ] Environment variables updated
- [ ] Sender email verified in SES
- [ ] Production access requested (if needed)
- [ ] Configuration set created
- [ ] Email templates tested
- [ ] Monitoring set up
- [ ] Old SMTP configuration removed

## 🔗 Useful Links

- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [SES Sending Limits](https://docs.aws.amazon.com/ses/latest/dg/manage-sending-quotas.html)
- [SES Best Practices](https://docs.aws.amazon.com/ses/latest/dg/best-practices.html)
- [Moving out of SES Sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

## 💡 Tips

1. **Start with Sandbox**: Test thoroughly in sandbox mode before requesting production access
2. **Use Templates**: Consider using SES templates for consistent branding
3. **Monitor Metrics**: Set up CloudWatch alarms for bounce/complaint rates
4. **Backup Plan**: Keep SMTP as fallback option during migration
5. **Test Thoroughly**: Test all email types (verification, invitations, etc.)
