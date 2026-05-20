"""Domain XML helpers."""

from huy_libvirt_agent.services.domain_xml import update_domain_xml_resources

SAMPLE = """<domain type='kvm'>
  <name>web-01</name>
  <memory unit='MiB'>2048</memory>
  <currentMemory unit='MiB'>2048</currentMemory>
  <vcpu>2</vcpu>
</domain>"""


def test_update_domain_xml_resources() -> None:
    out = update_domain_xml_resources(SAMPLE, memory_mib=4096, vcpu=4)
    assert "<memory" in out and "4096" in out
    assert "<vcpu>4</vcpu>" in out
