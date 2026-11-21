"""ledger command line.

    python -m ledger migrate  [--db PATH]          apply pending schema migrations
    python -m ledger status   [--db PATH]
    python -m ledger report   [--db PATH] [--as-of DATE]
    python -m ledger post     CODE AMOUNT_CENTS DATE [--memo M] [--db PATH]
    python -m ledger adjust   CODE AMOUNT_CENTS DATE --reason R --approved-by U [--db PATH]
    python -m ledger retention --today DATE [--db PATH]
"""

import argparse
import sys

import schemashift

from . import db, postings, reports, retention


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ledger")
    ap.add_argument("--db", default=db.DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    sub.add_parser("status")
    r = sub.add_parser("report")
    r.add_argument("--as-of")
    p = sub.add_parser("post")
    p.add_argument("code")
    p.add_argument("amount", type=int)
    p.add_argument("date")
    p.add_argument("--memo", default="")
    a = sub.add_parser("adjust")
    a.add_argument("code")
    a.add_argument("amount", type=int)
    a.add_argument("date")
    a.add_argument("--reason", required=True)
    a.add_argument("--approved-by", required=True)
    t = sub.add_parser("retention")
    t.add_argument("--today", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "migrate":
        try:
            for name in schemashift.upgrade(args.db, str(db.MIGRATIONS)):
                print(f"applied {name}")
        except schemashift.PreflightError as exc:
            print(f"schemashift: {exc}", file=sys.stderr)
            return 3
        return 0
    conn = db.connect(args.db)
    if args.cmd == "status":
        done = schemashift.applied_versions(conn)
        print(f"schema version {max(done) if done else 0}")
    elif args.cmd == "report":
        rows = reports.balances(conn, args.as_of)
        print(reports.format_report(rows))
        tb = reports.trial_balance(conn, args.as_of)
        print(f"\ntrial balance: debits {tb['debits'] / 100:,.2f}  credits {tb['credits'] / 100:,.2f}"
              f"  difference {tb['difference'] / 100:,.2f}")
    elif args.cmd == "post":
        print(postings.post_entry(conn, args.code, args.amount, args.date, args.memo))
    elif args.cmd == "adjust":
        print(postings.post_adjustment(conn, args.code, args.amount, args.date, args.reason,
                                       args.approved_by))
    elif args.cmd == "retention":
        print("archived:", ", ".join(retention.archive_closed(conn, args.today)) or "nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
