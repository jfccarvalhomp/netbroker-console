# NetBroker Console

Aplicacao web para gerenciamento centralizado de equipamentos de rede multivendor, baseada na proposta arquitetural Layered + Broker do TCC.

O projeto entrega um frontend totalmente acessivel via web e um backend Python sem dependencias externas, preparado para Ubuntu Server 22.04/24.04 amd64.

## Funcionalidades

- Dashboard operacional com KPIs, eventos e saude da plataforma.
- Inventario canonico de dispositivos multivendor.
- Fila de alarmes com reconhecimento auditavel.
- Jobs de automacao simulando publicacao em broker.
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
- Estado runtime: `data/state.json`
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

## Operacao

```bash
sudo systemctl status netbroker-console
sudo journalctl -u netbroker-console -f
sudo systemctl restart netbroker-console
```

## Executar manualmente

```bash
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
- `GET /api/state`
- `GET /api/devices?vendor=Cisco&q=core`
- `GET /api/alarms`
- `POST /api/alarms/ack`
- `POST /api/jobs/run`
- `POST /api/telemetry/simulate`
- `POST /api/convert`
- `GET /metrics`

Exemplo:

```bash
curl http://127.0.0.1:8080/api/health
```

## Licenca

Consulte [LICENSE.md](LICENSE.md).
