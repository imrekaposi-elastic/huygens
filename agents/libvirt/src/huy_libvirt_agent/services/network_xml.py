"""libvirt network XML generation."""

from __future__ import annotations

from jinja2 import Template

NETWORK_TEMPLATE = Template("""<network>
  <name>{{ name }}</name>
  <bridge name='{{ bridge }}' stp='on' delay='0'/>
  <forward mode='nat'/>
  <ip address='{{ gateway }}' netmask='{{ netmask }}'>
    {% if dhcp %}<dhcp>
      <range start='{{ dhcp_start }}' end='{{ dhcp_end }}'/>
    </dhcp>{% endif %}
  </ip>
</network>
""")


def _cidr_to_parts(cidr: str) -> tuple[str, str, str, str]:
    import ipaddress

    net = ipaddress.ip_network(cidr, strict=False)
    hosts = list(net.hosts())
    gateway = str(hosts[0]) if hosts else str(net.network_address + 1)
    netmask = str(net.netmask)
    dhcp_start = str(hosts[1]) if len(hosts) > 1 else gateway
    dhcp_end = str(hosts[-1]) if hosts else dhcp_start
    return gateway, netmask, dhcp_start, dhcp_end


def render_network_xml(name: str, bridge: str, ipv4_cidr: str, dhcp: bool = True) -> str:
    gateway, netmask, dhcp_start, dhcp_end = _cidr_to_parts(ipv4_cidr)
    return NETWORK_TEMPLATE.render(
        name=name,
        bridge=bridge,
        gateway=gateway,
        netmask=netmask,
        dhcp=dhcp,
        dhcp_start=dhcp_start,
        dhcp_end=dhcp_end,
    )
