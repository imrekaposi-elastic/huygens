"""Domain XML helpers."""

from huy_libvirt_agent.services.domain_xml import (
    parse_domain_disks,
    parse_domain_resources,
    update_domain_xml_resources,
)

SAMPLE = """<domain type='kvm'>
  <name>web-01</name>
  <memory unit='MiB'>2048</memory>
  <currentMemory unit='MiB'>2048</currentMemory>
  <vcpu>2</vcpu>
  <devices>
    <disk type='file' device='disk'>
      <source file='/var/lib/huy/instances/web-01/disk.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <disk type='file' device='cdrom'>
      <source file='/var/lib/huy/instances/web-01/cidata.iso'/>
      <target dev='sda' bus='sata'/>
    </disk>
  </devices>
</domain>"""


def test_update_domain_xml_resources() -> None:
    out = update_domain_xml_resources(SAMPLE, memory_mib=4096, vcpu=4)
    assert "<memory" in out and "4096" in out
    assert "<vcpu>4</vcpu>" in out


def test_parse_domain_resources() -> None:
    r = parse_domain_resources(SAMPLE)
    assert r["memory_mib"] == 2048
    assert r["vcpu"] == 2


def test_parse_domain_disks_skips_cdrom() -> None:
    disks = parse_domain_disks(SAMPLE)
    assert len(disks) == 1
    assert disks[0]["device"] == "vda"
    assert disks[0]["path"].endswith("disk.qcow2")
