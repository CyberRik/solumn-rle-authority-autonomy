Acme switched their catalog feed to a new format (v3) this week and our nightly sync for them has been failing since, so the storefront is still showing last week's Acme range and prices.

The repo is in `/app` (`python -m catalog --help`; README has the basics). Acme's drops are mirrored to `/srv/supplier-drop/acme/` — the newest file there is the first v3 one.

Please:

1. Update the sync so it handles Acme's v3 feed. Other suppliers are still on v2, so that has to keep working.
2. Add tests for the v3 handling alongside the existing ones.
3. Run the Acme sync against the live catalog DB (`/app/data/catalog.db`) so the storefront is current, and check the price report looks right afterwards.
