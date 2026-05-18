"""libvirt domain XML generation."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Template

DOMAIN_TEMPLATE = Template("""<domain type='kvm'>
  <name>{{ name }}</name>
  <metadata>
    <huy:labels xmlns:huy='https://huygens.local/ns/1.0'>
      <huy:country>{{ labels.country }}</huy:country>
      <huy:city>{{ labels.city }}</huy:city>
      <huy:company>{{ labels.company }}</huy:company>
    </huy:labels>
  </metadata>
  <memory unit='MiB'>{{ memory_mib }}</memory>
  <vcpu>{{ vcpu }}</vcpu>
  <os>
    <type arch='x86_64' machine='pc'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
  </features>
  <cpu mode='host-passthrough'/>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{{ disk_path }}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='{{ cloud_init_iso }}'/>
      <target dev='sda' bus='sata'/>
      <readonly/>
    </disk>
    <interface type='network'>
      <source network='{{ network }}'/>
      <model type='virtio'/>
    </interface>
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
      <source mode='bind' path='/var/lib/libvirt/qemu/{{ name }}.agent'/>
    </channel>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
  </devices>
</domain>
""")


def render_domain_xml(
    name: str,
    labels: dict[str, str],
    disk_path: Path,
    cloud_init_iso: Path,
    network: str,
    vcpu: int,
    memory_mib: int,
) -> str:
    return DOMAIN_TEMPLATE.render(
        name=name,
        labels=labels,
        disk_path=str(disk_path),
        cloud_init_iso=str(cloud_init_iso),
        network=network,
        vcpu=vcpu,
        memory_mib=memory_mib,
    )
