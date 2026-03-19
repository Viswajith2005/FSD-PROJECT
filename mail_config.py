# ──────────────────────────────────────────
#  SendGrid SMTP Configuration
# ──────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()

MAIL_ENABLED   = True
MAIL_SENDER    = "viswajithguptatelagamsetty@gmail.com"
MAIL_PASSWORD  = os.environ.get("MAIL_PASSWORD", "")
MAIL_PORT      = 587
MAIL_HOST      = "smtp.sendgrid.net"
