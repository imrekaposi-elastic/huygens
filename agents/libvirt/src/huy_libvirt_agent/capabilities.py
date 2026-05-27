"""Agent capability tokens for control-plane negotiation."""

CAP_WIREGUARD_BREAKOUT = "wireguard.breakout"
CAP_FLAT_LOCAL_PEER = "flat_breakout.local_peer"

AGENT_CAPABILITIES: tuple[str, ...] = (
    CAP_WIREGUARD_BREAKOUT,
    CAP_FLAT_LOCAL_PEER,
)
