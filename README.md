# IFT401

Capstone: Stock Trading App

## Who to ask

| Area | Owner |
|---|---|
| AWS account, EC2, RDS | Ryan |
| Database password, GitHub repo | Tyler |

## Database

PostgreSQL 18 on Amazon RDS (`ift401-postgres`, us-east-1). Per the SAD network topology Ryan built, the database sits in a private subnet and only the EC2 app server (`IFT401-Flask-Server`) can reach it. From a laptop or CloudShell you connect through a Session Manager tunnel that relays traffic through EC2.

| Setting | Value |
|---|---|
| Database | `ift401` |
| Login | `ift401admin` (ask Tyler for the password) |
| Endpoint | `ift401-postgres.c23miiuyiy24.us-east-1.rds.amazonaws.com:5432` |
| EC2 instance | `i-0928910606c87c045` |

RDS requires SSL, so every connection string needs `?sslmode=require`.

### Connecting from your laptop

You need:

- Your AWS login for the IFT401 account
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
- Your credentials saved as a profile: `aws configure --profile ift401`

1. Start the tunnel and leave that terminal open. It works in Git Bash, PowerShell, macOS and CloudShell:

   ```bash
   aws ssm start-session --profile ift401 --region us-east-1 --target i-0928910606c87c045 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters "host=ift401-postgres.c23miiuyiy24.us-east-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433"
   ```

   Wait for `Waiting for connections...`.

2. In the repo root, create a `.env` file with only these two lines from `.env.example`, and replace `PASSWORD` with the real one. Ask Tyler for it when you set this up:

   ```ini
   FLASK_APP=run
   DATABASE_URL=postgresql://ift401admin:PASSWORD@localhost:5433/ift401?sslmode=require
   ```

   `.env` is gitignored. Never commit it, and never put the real password in `.env.example`. Run the app from a second terminal while the tunnel stays open in the first.

3. Optional: check the connection with psql.

   ```bash
   psql "host=localhost port=5433 dbname=ift401 user=ift401admin sslmode=require" -c '\dt'
   ```

In CloudShell, leave out `--profile ift401`. To run the tunnel in the background, add `> tunnel.log 2>&1 &` to the end of the command. CloudShell ends idle sessions after about 20 minutes, which also stops the tunnel.

### Troubleshooting

| Error | Fix |
|---|---|
| `Connection refused` on port 5433 | The tunnel isn't running. Start it again. |
| `password authentication failed` | Wrong login or password. Check with Tyler. |
| `no pg_hba.conf entry ... no encryption` | Add `?sslmode=require` to the connection string. |
| `TargetNotConnected` from `aws ssm` | The EC2 instance is stopped. Start it in the EC2 console. |

### Test data

The database is seeded with fake data so you can check reads and writes against known values.

| Login | Password | What it's for |
|---|---|---|
| `admin` | `Password123!` | Administrator screens (ADM-xxx) |
| `demo` | `Password123!` | Transaction history matches SAD Wireframe 4. Has 2 pending orders (Wireframe 7) and 1 cancelled order |
| `newcustomer` | `Password123!` | No activity. Tests the empty history (CUS-311) and empty portfolio screens |

There are 12 more customers with deposits, trades and holdings, plus one rejected order (CUS-406).

- **Stocks:** 9. ACME, NVDA, AMD and SPCX use the Wireframe 8 prices. OLDC is inactive, so it should not appear on the market board.
- **Price history:** hourly prices for 2026-09-09 to 2026-09-11.
- **Market clock:** paused at Monday 2026-09-14 10:00, during market hours.
- **Market hours:** 9:30 AM to 4:00 PM.
- **Holidays:** 2026-09-07, 2026-11-26 and 2026-12-25.

`demo`'s cash balance is $1,997.50.

### Tables

| Table | Holds | SAD |
|---|---|---|
| `customers` | Name, username, email, password hash, `is_admin` | CUS-1xx |
| `cash_accounts` | One per customer, `balance` | CUS-106, CUS-2xx |
| `orders` | Buy and sell orders and their status | CUS-4xx, CUS-5xx |
| `portfolio_holdings` | Shares owned per customer per stock (`share_quantity`) | CUS-6xx |
| `transactions` | Deposits, withdrawals, buys and sells, each with the resulting balance | CUS-3xx |
| `stocks` | Ticker, prices, daily open/high/low, volume | ADM-1xx, SYS-1xx |
| `price_history` | Every generated price | SYS-101 |
| `market_hours` | Opening and closing time | ADM-2xx |
| `market_schedule` | Which simulated dates are holidays | ADM-3xx |
| `market_clock` | The current simulated date and time | ADM-302 |

### Reminders

- Allowed values are case-sensitive: `order_type` is `Buy`/`Sell`; `status` is `Pending`/`Executed`/`Cancelled`/`Rejected`; `transaction_type` is `Deposit`/`Withdrawal`/`Buy`/`Sell`.
- `transactions.amount` is negative for withdrawals and buys.
- Set `orders.submitted_at` and `transactions.transaction_date` from `get_simulated_datetime()`, not the real clock.
- Market cap isn't stored. Calculate it as `current_price * volume` (SYS-110).
- The database rejects negative balances, negative share counts and order quantities of 0 or less. Validate in code too so users get a clear message.
- Change tables only through Flask-Migrate: edit the model in `app/models/`, run `flask db migrate -m "..."`, and commit the file. Check with the team before running `flask db upgrade` against RDS. Current migration: `05d0d8db0ebb`.
