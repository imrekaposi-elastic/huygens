.PHONY: install dev test lint openapi run

AGENT_DIR := agents/libvirt

install dev test lint openapi run:
	$(MAKE) -C $(AGENT_DIR) $@
