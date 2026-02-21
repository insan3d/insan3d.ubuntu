# insan3d's Ubuntu Collection

Ansible collection for managing Ubuntu Pro and FIPS compliance.

## Roles

### `insan3d.ubuntu.pro`

Manages Ubuntu Pro attachment and service state.

- Installs and configures Ubuntu Pro client
- Handles attachment with token
- Enables/disables Pro services
- Automatic reboot handling

**Variables:**
- `pro_token` - Ubuntu Pro authentication token
- `pro_services_enable` - List of services to enable
- `pro_services_disable` - List of services to disable

### `insan3d.ubuntu.fips`

Manages FIPS 140-2 and FIPS 140-3 compliance.

- Configures FIPS-certified kernel and packages
- Supports latest (with `livepatch`) and frozen releases
- Validates FIPS enablement/disablement
- Automatic reboot when required

**Variables:**
- `fips_status` - One of: `latest`, `frozen`, `absent`

## Modules

### `pro`

Custom Ansible module to manage Ubuntu Pro services with the `pro` CLI.

**Options:**
- `state` - Ubuntu Pro attachment state (attached/detached)
- `token` - Ubuntu Pro token for attachment
- `enabled` - Services to enable
- `disabled` - Services to disable

## Requirements

- Ubuntu 24.04 (Noble) or later
- Ansible 2.20+
- `ubuntu-advantage-tools` package (installed as dependency by `insan3d.ubuntu.pro` role)

## License

MIT.
