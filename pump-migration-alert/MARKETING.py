# TEE-BOT Marketing Materials
# Copy these exactly. Word for word.

# ══════════════════════════════════════════════════════
# TWITTER THREAD — Post this the moment your first
# alert fires. Attach a screenshot of the Telegram alert.
# ══════════════════════════════════════════════════════

TWITTER_THREAD = """

TWEET 1 (with screenshot of your alert):
──────────────────────────────────────────
I built a bot that detects Pump.fun tokens before they migrate to Raydium.

It just sent this alert 6 minutes before migration.

Here's how it works 🧵

TWEET 2:
──────────────────────────────────────────
Most people find out a token is migrating from Twitter or Telegram groups.

By then the price has already moved.

My bot reads the bonding curve directly on-chain and alerts at 85% bonded.

That's a 5-10 minute head start.

TWEET 3:
──────────────────────────────────────────
The bot runs 24/7. Every 30 seconds it checks Pump.fun for tokens hitting the migration zone.

Before sending the alert it also checks:
✅ Mint authority renounced
✅ No whale concentration
✅ Dev wallet history

You get the call AND the safety data.

TWEET 4:
──────────────────────────────────────────
It's free to follow.

Telegram channel: [YOUR CHANNEL LINK]

Built with Python + Helius RPC.

If you want a custom version (auto-buy, Discord alerts, whale tracking) → DM me.

TWEET 5:
──────────────────────────────────────────
Not selling anything.

Just a tool I built for myself and decided to share.

Follow the channel. Tell me what you'd add to make it more useful.

[YOUR CHANNEL LINK]

"""

# ══════════════════════════════════════════════════════
# TELEGRAM GROUPS TO JOIN AND POST IN
# After your first 5 real alerts, share this message:
# ══════════════════════════════════════════════════════

TELEGRAM_ANNOUNCEMENT = """

🤖 I built a free Pump.fun migration alert bot.

It monitors bonding curves on-chain and sends alerts when tokens hit 85% bonded — before they hit Raydium.

Each alert includes:
📊 Bonding progress
✅ Contract renounced check  
⚠️ Whale concentration check
⏱️ Estimated minutes to migration

Free channel: [YOUR CHANNEL LINK]

No paid tiers. No spam. Just alerts when tokens are about to graduate.

"""

# ══════════════════════════════════════════════════════
# DM CONVERSION SCRIPT
# When someone DMs asking about a custom version,
# use this exact flow:
# ══════════════════════════════════════════════════════

DM_CONVERSATION = """

THEY SAY: "Can you add auto-buy on migration?"
──────────────────────────────────────────────
YOU SAY:
"Yes, I can build that. It would auto-buy a fixed SOL amount 
when the bot detects migration and execute via Jupiter.

Delivery: 3-4 days.
Price: $150

Includes:
- Auto-buy on migration signal
- Configurable SOL amount per trade
- Stop-loss built in
- Telegram confirmation on every trade

Want me to scope it out properly?"

──────────────────────────────────────────────

THEY SAY: "Can you make one for Discord instead of Telegram?"
──────────────────────────────────────────────
YOU SAY:
"Yes, Discord webhooks are straightforward to add.

$80 for Discord webhook integration on top of the base bot.
$120 if you want Discord + Telegram both.

Delivery: 2 days. Do you want the full bot or just the alerts?"

──────────────────────────────────────────────

THEY SAY: "How much for a private version just for me?"
──────────────────────────────────────────────
YOU SAY:
"Private version means:
- Your own bot instance (no shared channel)
- Custom alert thresholds
- Priority updates
- Direct support

$200 one-time setup + $30/month hosting if you want me to 
host it, or one-time $200 and you run it yourself.

What features do you need beyond the base migration alert?"

──────────────────────────────────────────────

THEY SAY: "Can you add whale wallet tracking?"
──────────────────────────────────────────────
YOU SAY:
"Yes. I track a list of known profitable wallets and add 
a signal to each alert when one of them buys.

Adds about a week of build time to curate the wallet list properly.

$250 total for migration alerts + smart wallet overlay.

Want the full spec before committing?"

──────────────────────────────────────────────

RULE: Never start with "I can't" or "that's hard".
Start with "Yes" or "Yes, here's how that works".
Give a price and a delivery date on every enquiry.
Never work for free. Your time is already paying off in learning.

"""

# ══════════════════════════════════════════════════════
# PRICING LADDER (increase as you get testimonials)
# ══════════════════════════════════════════════════════

PRICING = """

WEEK 1-2 (no testimonials yet):
  Basic private bot:     $100
  Auto-buy feature:      $80 add-on
  Discord alerts:        $60 add-on

WEEK 3-4 (first testimonial):
  Basic private bot:     $150
  Auto-buy feature:      $120 add-on
  Whale tracking:        $150 add-on

MONTH 2 (2+ testimonials):
  Basic private bot:     $250
  Full custom build:     $400-600
  Monthly retainer:      $100/month maintenance

MONTH 3+:
  Price what the market pays.
  If nobody haggles, you're too cheap.

"""

if __name__ == "__main__":
    print("Marketing materials loaded.")
    print("Twitter thread:", len(TWITTER_THREAD.split("TWEET")), "tweets")
    print("Pricing tiers: 3")
