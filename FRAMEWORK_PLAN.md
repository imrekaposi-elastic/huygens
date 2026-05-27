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

