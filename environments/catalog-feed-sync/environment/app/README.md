# catalog

Merchandising catalog service: mirrors supplier catalog feeds into the
storefront database and computes the prices customers actually pay.

```
python -m catalog sync --supplier acme          # latest drop in /srv/supplier-drop/acme
python -m catalog sync --supplier acme --feed F # a specific feed file
python -m catalog report --supplier acme        # list vs effective price, CSV
python -m catalog runs                          # sync history
```

The live database is `data/catalog.db` (override with `CATALOG_DB`).

## Tests

`pytest` from the repository root.
