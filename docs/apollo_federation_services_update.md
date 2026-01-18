# POZNÁMKA K KONFIGURACI PRO LADĚNÍ (DEBUG)

Tento dokument popisuje historickou změnu pro plně kontejnerizované prostředí, které **není relevantní** pro standardní vývojový postup pomocí `docker-compose.debug.yml`.

## Standardní Debugovací Konfigurace

Při použití `docker-compose.debug.yml` běží služba `evolution` (tento GQL subgraph) lokálně na vašem počítači na portu `8001`. Ostatní služby (včetně `apollo-gateway`) běží v Dockeru.

Aby se `apollo-gateway` mohla připojit k vaší lokální službě, používá se `proxy` služba, která je nakonfigurována takto:
- `proxy` přesměrovává požadavky na `http://host.docker.internal:8001`.
- `apollo-gateway` je nakonfigurována, aby komunikovala se službou `evolution` přes `http://proxy:8000/gql`.

Tato konfigurace je správná a není třeba ji měnit. Původní informace v tomto souboru se týkaly jiného scénáře a pro lokální vývoj je můžete ignorovat.
