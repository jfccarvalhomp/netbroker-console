# NetBroker Console

Aplicacao web para gerenciamento centralizado de equipamentos de rede multivendor, baseada na proposta arquitetural Layered + Broker do TCC.

O projeto entrega um frontend totalmente acessivel via web e um backend Python sem dependencias externas, preparado para Ubuntu Server 22.04/24.04 amd64.

## Funcionalidades

- Dashboard operacional com KPIs, eventos e saude da plataforma.
- Inventario canonico de dispositivos multivendor.
- Fila de alarmes com reconhecimento auditavel.
- Jobs de automacao simulando publicacao em broker.
- Auditoria de login, logout, acesso negado e acoes operacionais.
- Registro de adaptadores Cisco, Fortinet, Aruba, Juniper, Huawei e Mikrotik.
- Conversor de payload de fabricante para modelo canonico.
- Galeria de diagramas arquiteturais extraidos do trabalho.
- Endpoint `/metrics` em formato compativel com Prometheus.

## Arquitetura

- Frontend: `index.html`, `styles.css`, `app.js`
- Entrada backend: `server.py`
- Apresentacao HTTP: `netbroker_console/presentation/`
- Casos de uso: `netbroker_console/application/`
- Dominio canonico: `netbroker_console/domain/`
- Persistencia/infraestrutura: `netbroker_console/infrastructure/`
- Assets: `assets/`
- Estado runtime local: `data/state.json`
- Persistencia opcional em PostgreSQL: `scripts/setup-postgres-ubuntu.sh`
- Broker opcional RabbitMQ: `scripts/setup-rabbitmq-ubuntu.sh`
- Autenticacao opcional LDAP/AD: `scripts/setup-ldap-ubuntu.sh`
- Autenticacao opcional TACACS+: `scripts/setup-tacacs-ubuntu.sh`
- Autorizacao opcional Cisco ISE: `scripts/setup-ise-ubuntu.sh`
- Instalador systemd: `scripts/install-ubuntu.sh`

## Instalar no Ubuntu Server

Copie a pasta para o servidor e execute:

```bash
cd /home/<usuario>/netbroker-console
sudo bash scripts/install-ubuntu.sh
```

Depois acesse:

```text
http://IP_DO_SERVIDOR:8080/
```

## Habilitar PostgreSQL

Por padrao, a aplicacao usa JSON local para facilitar demonstracao e validacao. Para usar PostgreSQL no Ubuntu:

```bash
sudo bash scripts/setup-postgres-ubuntu.sh
```

O script instala PostgreSQL, cria banco/usuario, grava `/etc/netbroker-console.env` e reinicia o servico com `NETBROKER_STORE=postgres`.

## Habilitar RabbitMQ

Para transformar os jobs de automacao em mensagens assincronas reais:

```bash
sudo bash scripts/setup-rabbitmq-ubuntu.sh
```

O script instala RabbitMQ e `python3-pika`, habilita `NETBROKER_BROKER=rabbitmq` e cria o servico `netbroker-console-worker`, responsavel por consumir as filas:

- `device.discovery`
- `inventory.sync`
- `config.backup`
- `alarm.remediate`

Comandos uteis:

```bash
sudo systemctl status rabbitmq-server
sudo systemctl status netbroker-console-worker
sudo journalctl -u netbroker-console-worker -f
```

## Operacao

```bash
sudo systemctl status netbroker-console
sudo journalctl -u netbroker-console -f
sudo systemctl restart netbroker-console
```

## Autenticacao local

O console possui login local inicial e RBAC. As credenciais bootstrap padrao sao:

```text
Usuario: admin
Senha: admin123
Papel: admin
```

Em producao, altere `/etc/netbroker-console.env`:

```bash
sudo tee -a /etc/netbroker-console.env >/dev/null <<'ENV'
NETBROKER_ADMIN_USER=admin
NETBROKER_ADMIN_PASSWORD=SENHA_FORTE_AQUI
NETBROKER_ADMIN_ROLE=admin
ENV
sudo systemctl restart netbroker-console
```

Papeis previstos:

- `admin`
- `noc`
- `auditor`
- `readonly`

## Habilitar LDAP/Active Directory

O provedor local continua sendo o padrao. Para autenticar via LDAP/AD no Ubuntu:

Modo interativo recomendado:

```bash
bash scripts/configure-ldap-ubuntu.sh
```

Modo direto:

```bash
sudo NETBROKER_LDAP_URI="ldap://ad.example.local:389" \
  NETBROKER_LDAP_BASE_DN="DC=example,DC=local" \
  NETBROKER_LDAP_BIND_DN="CN=svc-netbroker,OU=Service Accounts,DC=example,DC=local" \
  NETBROKER_LDAP_BIND_PASSWORD="SENHA_DA_CONTA_DE_SERVICO" \
  NETBROKER_LDAP_GROUP_ROLE_MAP="CN=NetBroker Admins,OU=Groups,DC=example,DC=local=admin;CN=NetBroker NOC,OU=Groups,DC=example,DC=local=noc;CN=NetBroker Auditors,OU=Groups,DC=example,DC=local=auditor;CN=NetBroker Readonly,OU=Groups,DC=example,DC=local=readonly" \
  bash scripts/setup-ldap-ubuntu.sh
```

Variaveis principais:

- `NETBROKER_AUTH_PROVIDER=ldap`
- `NETBROKER_LDAP_URI`
- `NETBROKER_LDAP_BASE_DN`
- `NETBROKER_LDAP_BIND_DN`
- `NETBROKER_LDAP_BIND_PASSWORD`
- `NETBROKER_LDAP_USER_FILTER`
- `NETBROKER_LDAP_DEFAULT_ROLE`
- `NETBROKER_LDAP_GROUP_ROLE_MAP`

## Habilitar TACACS+

Modo interativo recomendado:

```bash
bash scripts/configure-tacacs-ubuntu.sh
```

Modo direto:

```bash
sudo NETBROKER_TACACS_HOST="10.0.0.10" \
  NETBROKER_TACACS_SECRET="SEGREDO_TACACS" \
  NETBROKER_TACACS_DEFAULT_ROLE="readonly" \
  NETBROKER_TACACS_USER_ROLE_MAP="admin=admin;operador=noc;auditor=auditor" \
  bash scripts/setup-tacacs-ubuntu.sh
```

Variaveis principais:

- `NETBROKER_AUTH_PROVIDER=tacacs`
- `NETBROKER_TACACS_HOST`
- `NETBROKER_TACACS_SECRET`
- `NETBROKER_TACACS_PORT`
- `NETBROKER_TACACS_TIMEOUT`
- `NETBROKER_TACACS_DEFAULT_ROLE`
- `NETBROKER_TACACS_USER_ROLE_MAP`

## Habilitar Cisco ISE para autorizacao

O ISE entra como camada de autorizacao depois do login local, LDAP ou TACACS+. Ele ajusta o papel RBAC final com base em usuario, perfil ISE ou SGT.

Modo interativo recomendado:

```bash
bash scripts/configure-ise-ubuntu.sh
```

Modo direto:

```bash
sudo NETBROKER_ISE_DEFAULT_ROLE="readonly" \
  NETBROKER_ISE_USER_ROLE_MAP="admin=admin;operador=noc;auditor=auditor" \
  NETBROKER_ISE_PROFILE_ROLE_MAP="NetBroker-Admin=admin;NetBroker-NOC=noc;NetBroker-Auditor=auditor" \
  NETBROKER_ISE_SGT_ROLE_MAP="16=admin;17=noc;18=auditor;19=readonly" \
  bash scripts/setup-ise-ubuntu.sh
```

Variaveis principais:

- `NETBROKER_ISE_ENABLED=true`
- `NETBROKER_ISE_DEFAULT_ROLE`
- `NETBROKER_ISE_USER_ROLE_MAP`
- `NETBROKER_ISE_PROFILE_ROLE_MAP`
- `NETBROKER_ISE_SGT_ROLE_MAP`

## Executar manualmente

```bash
python3 server.py --host 0.0.0.0 --port 8080
```

Com PostgreSQL:

```bash
NETBROKER_STORE=postgres \
NETBROKER_POSTGRES_DSN="dbname=netbroker_console user=netbroker_console password=SENHA host=127.0.0.1 port=5432" \
python3 server.py --host 0.0.0.0 --port 8080
```

Com RabbitMQ:

```bash
NETBROKER_BROKER=rabbitmq \
NETBROKER_RABBITMQ_URL="amqp://guest:guest@127.0.0.1:5672/%2f" \
python3 server.py --host 0.0.0.0 --port 8080
```

## Executar no Windows para teste local

```powershell
.\start-app.ps1 -Port 4190
```

Abra:

```text
http://127.0.0.1:4190/
```

## APIs

- `GET /api/health`
- `GET /api/auth/me`
- `GET /api/state`
- `GET /api/devices?vendor=Cisco&q=core`
- `GET /api/alarms`
- `GET /api/adapters`
- `GET /api/audit?limit=100`
- `POST /api/alarms/ack`
- `POST /api/jobs/run`
- `POST /api/telemetry/simulate`
- `POST /api/convert`
- `GET /metrics`
- `POST /api/auth/login`
- `POST /api/auth/logout`

Exemplo:

```bash
curl http://127.0.0.1:8080/api/health
curl -c /tmp/netbroker.cookies \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  http://127.0.0.1:8080/api/auth/login
curl -b /tmp/netbroker.cookies http://127.0.0.1:8080/api/state
```

## Licenca

Consulte [LICENSE.md](LICENSE.md).
