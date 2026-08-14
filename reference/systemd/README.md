# Reference: systemd restart-policy drop-ins

Copy-paste drop-ins for [SERVICE_UNIT_STANDARD](../../standards/SERVICE_UNIT_STANDARD.md).

Install as a drop-in rather than editing the unit, so a package or repo update
cannot silently revert it:

```bash
# system scope
sudo mkdir -p /etc/systemd/system/<unit>.service.d
sudo cp tier-a-backoff-only.conf /etc/systemd/system/<unit>.service.d/restart-storm.conf
sudo systemctl daemon-reload

# user scope
mkdir -p ~/.config/systemd/user/<unit>.service.d
cp tier-b-backoff-and-limiter.conf ~/.config/systemd/user/<unit>.service.d/restart-storm.conf
systemctl --user daemon-reload
```

`daemon-reload` does not restart the service, so applying these is non-disruptive.

## Which tier?

Ask what happens when the unit stays permanently stopped.

| | Tier A | Tier B |
|---|---|---|
| **Use for** | core infra (container runtime, inference/embedding servers, node daemons) | leaf apps, optional services |
| **On permanent fault** | retries forever, backed off to 5min | lands in `failed` after 5 tries |
| **Risk it avoids** | a transient blip becoming a permanent outage | a dead unit silently retrying forever |

When in doubt pick Tier A. It always stops the storm, and it can never introduce
a new way for the service to stay down.

## Verify

```bash
./scripts/audit-service-units.sh          # exit 1 while any unit is exposed
```

Then prove the behavior rather than reading config back. Create a deliberately
broken unit and watch the journal:

```ini
# ~/.config/systemd/user/rs-selftest.service
[Unit]
StartLimitIntervalSec=30min
StartLimitBurst=5
[Service]
ExecStart=/nonexistent/python main.py
Restart=on-failure
RestartSec=2
RestartSteps=4
RestartMaxDelaySec=30
```

```bash
systemctl --user daemon-reload && systemctl --user start rs-selftest
sleep 75
journalctl --user -u rs-selftest -o short-iso | grep -E 'Scheduled restart|repeated too quickly'
```

Expected: restart gaps grow (`4s`, `8s`, `16s`, `30s` capped), then
`Start request repeated too quickly` and `ActiveState=failed`. Remove the unit
afterwards (`systemctl --user stop`, `reset-failed`, delete the file,
`daemon-reload`).
