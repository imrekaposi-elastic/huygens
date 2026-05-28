Using different agents per hypervisor, such as in the agents subdirectory, there should be a management component. Here are the functional and non functional requirements

Non func:
- mircroservice based
- adaptable, extensible, modifyable
- A project consists of 1 or more networks. ip subnets are managed by a central ip subnet pool
- Helper for subnets (wizard how many projected networks, how many hosts per network, exceptions). use RFC 1918 for internal IP's
- Breakout network wireguard based centrally managed. admins can connect networks, ip addrressing should be auto assigned but visible
- API
- Responsive web frontend looking grapgically modern
- instant updates of status changes 
- per vm see performance overview in graph (cpu/mem/disk/net)
- per hypervisor see performance overview in graph if available like with libvirt (cpu/mem/disk/net)
- linking networks should be drag and drop — **Phase 6 MVP:** console Topology + control-plane reconciler; cross-host traffic validated manually; see [docs/PHASED_PLAN.md](docs/PHASED_PLAN.md) and [docs/operations/phase6-release-and-validation.md](docs/operations/phase6-release-and-validation.md)
- log in ECS format
- use opentelemetry throughout the application. be edot friendly.

Func:
In general I want a console where you configure infrastructure providers, regions and add agents under the region of the provider.
Compliancy users should be able to place qualitative characteristics under provider and region. eg; data sovereignity, BIO compliance etc etc.
The characteristics are arbitrary but can be configured with a description and a MSCW qualification. Resources underneath a region of a provider inherit those qualifications.
Note that the provider is leading, so Hetzner in Germany is something totally Different than Azure in Germany. Hetzner in Finland can hold some equal characteristics as Hetzner Germany, but does not need to be equal.
There should also be a general section telling which standards to what extent an organization should be compliant with, complete with description, url path etc for more information. 
all these configurations should be audited. Compliance check always has an owner and a validity check period (eg annually refresh)
All configuration objects have a desired state and an actual state. actual state should always be collected. config drift should be shown visually as with api (detected.config_drift: false/true).
Icons in the gui should be intuitive like a vm, firewall rule object, cloud-init, network, region, provider etc

- Admin section
    - RBAC module
        ROLES:
            admin
            compliance_admin
            platform admin
            Per project:
                project admin (full access for a project)
                compliance_reader (can read compliancy status)
                operator (CRUD vms/networks/cloudinits)
                auditor (can read everything, including logs)
                ssh access (ssh gateway access to resources wihtin the project)
                resource manager (defines limits quota per project)
                security engineer (firewall rule configuration)
                compliance engineer (deifnes asset criticality/compliance requirements--> those should be selected from organizational compliance items specified)
            further roles can be custom created and permissions per node object can be set (and also audited)
            Configuration of authentication backend
                LOCAL
                LDAP
                SAML 
                OIDC
    - Compliance notification alerter
    - Compliance Standards are creatable items should have a general name (for example ISO27001)
        - Subitems are controls that are linked to a compliance standard.
            - Controls consist of a name, description, rationale (the context)
            - Controls should have uploadable evidence, categorizable by: Design effectiveness, Implementation / existence and Operating effectiveness
            - Strong auditing and versioning (who uploaded and when)
            - Overall compliance status should be in dashboard overview (pie chart)
            - Solution should be strong enough so that 1000+ controls + evidence still navigates quickly (no slow database upserts)
            - Actual evidence should be stored in an object store, database just stores references
            - A compliance export should be possible in PDF form
        - A compliance cycle is repetitive, so you should clearly see for what compliance cycle the current environment is compliant
    - An ogranization can be subject to multiple compliance standards.
    - In the admin | compliance section, it should be possible to upload compliance packs. Those will be shipped seperately and jumpstarts organizations to start use this tool quickly. Examples are ISO27001, DIGID assessment, Pas Toe of Leg uit Lijst, BIO
        - The pack will be json, think of a data model already. Perhaps use digid assessment requirements as template since it's relatively small

    - Ip address management module for projects

- Operator section
    - CRUD networks (=project)
    - CRUD cloudinits
    - CRUD VM's

- Network section
    - publish resources 
    - connect networks between hypervisors

- Operator section 2
    - ssh gateway 
        - session recording

## Implementation map (Phase 7 — shipped in `huy-libvirt-agent`)

Strategic requirements above are delivered incrementally. **Phase 7 MVP + GRC** status in [docs/PHASED_PLAN.md](docs/PHASED_PLAN.md) and [docs/operations/phase7-compliance-and-lifecycle-guards.md](docs/operations/phase7-compliance-and-lifecycle-guards.md).

| FRAMEWORK_PLAN topic | Shipped | Service / console |
|----------------------|---------|-------------------|
| Qualitative characteristics on provider/region (MoSCoW, description) | Yes | `huy-compliance` — `/qualitative-characteristics`, Infrastructure link panel; Explorer inheritance |
| Org standards + asset criticality (“know why”) | Yes | Catalog + Explorer + project/VM/network assignment |
| Compliance checks (owner, validity) | Yes | `/compliance-checks`; alerter logs to structlog |
| GRC standards / controls / evidence / cycles | Yes | **Compliance → GRC**; object store for evidence bytes |
| Compliance packs (JSON bootstrap) | Yes | Validate + apply — [docs/compliance/packs.md](docs/compliance/packs.md) |
| PDF compliance export | Yes | Async job; console auto-download |
| Audit of compliance changes | Yes | PostgreSQL `compliance_audit_log` + structlog |
| Dashboard pie chart (overall GRC status) | **Deferred** | Overview KPI cards only; charts backlog |
| `config_drift` on all config objects | **Partial** | Placement rationale field reserved; inventory not wired |
| Desired vs actual state everywhere | **Partial** | Topology link drift (Phase 6); compliance drift deferred |
| Kibana / Elasticsearch compliance views | **Spike** | [docs/compliance/kibana/README.md](docs/compliance/kibana/README.md) |
| Custom RBAC roles beyond built-ins | Later phases | IAM Phase 1a built-ins |

