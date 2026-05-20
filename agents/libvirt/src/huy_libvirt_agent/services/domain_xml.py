"""libvirt domain XML generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

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


def update_domain_xml_resources(
    xml: str,
    *,
    vcpu: int | None = None,
    memory_mib: int | None = None,
) -> str:
    """Patch persistent domain XML for vCPU / memory (MiB)."""
    root = ET.fromstring(xml)
    if memory_mib is not None:
        for tag in ("memory", "currentMemory"):
            elem = root.find(tag)
            if elem is not None:
                elem.text = str(memory_mib)
                elem.set("unit", "MiB")
    if vcpu is not None:
        elem = root.find("vcpu")
        if elem is not None:
            elem.text = str(vcpu)
    return ET.tostring(root, encoding="unicode")


def parse_domain_resources(xml: str) -> dict[str, int | None]:
    """Read vCPU and memory (MiB) from domain XML."""
    root = ET.fromstring(xml)
    memory_mib: int | None = None
    mem = root.find("memory")
    if mem is not None and mem.text:
        unit = (mem.get("unit") or "KiB").lower()
        value = int(mem.text)
        if unit in ("mib", "m"):
            memory_mib = value
        elif unit in ("gib", "g"):
            memory_mib = value * 1024
        elif unit in ("kib", "k"):
            memory_mib = max(1, value // 1024)
        else:
            memory_mib = max(1, value // 1024)
    vcpu: int | None = None
    vcpu_elem = root.find("vcpu")
    if vcpu_elem is not None and vcpu_elem.text:
        vcpu = int(vcpu_elem.text.split()[0])
    return {"memory_mib": memory_mib, "vcpu": vcpu}


def parse_domain_disks(xml: str) -> list[dict[str, Any]]:
    """List data disks (exclude cloud-init cdrom) from domain XML."""
    root = ET.fromstring(xml)
    disks: list[dict[str, Any]] = []
    for disk in root.findall("./devices/disk"):
        if disk.get("device") == "cdrom":
            continue
        source = disk.find("source")
        path = source.get("file") if source is not None else None
        target = disk.find("target")
        device = target.get("dev") if target is not None else "disk"
        size_bytes: int | None = None
        if path:
            p = Path(path)
            if p.exists():
                size_bytes = p.stat().st_size
        disks.append({"device": device, "path": path, "size_bytes": size_bytes})
    return disks
