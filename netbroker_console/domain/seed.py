from __future__ import annotations


INITIAL_STATE = {
    "queueDepth": 2416,
    "devices": [
        {"host": "SW-MTZ-CORE-01", "ip": "10.10.0.2", "vendor": "Cisco", "model": "Catalyst 9500", "site": "Matriz", "status": "UP", "cpu": 34, "backup": "Hoje"},
        {"host": "RTR-MTZ-WAN-01", "ip": "10.10.0.1", "vendor": "Juniper", "model": "MX204", "site": "Matriz", "status": "UP", "cpu": 41, "backup": "Hoje"},
        {"host": "FW-DC-EDGE-01", "ip": "10.20.0.5", "vendor": "Fortinet", "model": "FortiGate 200F", "site": "Datacenter", "status": "ALERTA", "cpu": 76, "backup": "Ontem"},
        {"host": "AP-FIL-03-12", "ip": "10.31.12.9", "vendor": "Aruba", "model": "AP-515", "site": "Filial 03", "status": "UP", "cpu": 19, "backup": "Hoje"},
        {"host": "RTR-REM-07", "ip": "10.44.7.1", "vendor": "Mikrotik", "model": "CCR2004", "site": "Remoto 07", "status": "DOWN", "cpu": 0, "backup": "3 dias"},
        {"host": "SW-DC-TOR-06", "ip": "10.20.6.2", "vendor": "Cisco", "model": "Nexus 93180", "site": "Datacenter", "status": "UP", "cpu": 53, "backup": "Hoje"},
        {"host": "FW-FIL-02", "ip": "10.32.0.5", "vendor": "Fortinet", "model": "FortiGate 80F", "site": "Filial 02", "status": "UP", "cpu": 48, "backup": "Hoje"},
        {"host": "SW-FIL-05-AC", "ip": "10.35.0.2", "vendor": "Aruba", "model": "CX 6200", "site": "Filial 05", "status": "ALERTA", "cpu": 68, "backup": "Ontem"},
    ],
    "alarms": [
        {"id": 1, "severity": "critical", "device": "RTR-REM-07", "text": "Site remoto sem resposta SNMP e ICMP ha 9 minutos.", "source": "Monitoring Service"},
        {"id": 2, "severity": "warning", "device": "FW-DC-EDGE-01", "text": "CPU acima de 75% durante cinco coletas consecutivas.", "source": "Fortinet Adapter"},
        {"id": 3, "severity": "warning", "device": "SW-FIL-05-AC", "text": "Interface uplink com descarte crescente de pacotes.", "source": "Aruba Adapter"},
        {"id": 4, "severity": "info", "device": "SW-MTZ-CORE-01", "text": "Backup de configuracao concluido com sucesso.", "source": "Backup Service"},
    ],
    "jobs": [
        {"name": "Backup de configuracoes", "desc": "Coleta configs via SSH, REST ou NETCONF e persiste no PostgreSQL.", "queue": "config.backup"},
        {"name": "Descoberta multivendor", "desc": "Varre sub-redes, identifica fabricante e cria Device canonico.", "queue": "device.discovery"},
        {"name": "Atualizacao de inventario", "desc": "Normaliza interfaces, versoes e modelos para o dominio central.", "queue": "inventory.sync"},
        {"name": "Remediacao de alarme", "desc": "Executa playbooks aprovados para eventos operacionais conhecidos.", "queue": "alarm.remediate"},
    ],
    "events": [
        ["10:42", "command.config.backup publicado pelo Configuration Service"],
        ["10:43", "Cisco Adapter converteu interfaces para modelo canonico"],
        ["10:44", "Monitoring Service correlacionou alarme de CPU no FW-DC-EDGE-01"],
        ["10:45", "OpenTelemetry fechou trace distribuido do job inventory.sync"],
    ],
    "audit": [],
}
