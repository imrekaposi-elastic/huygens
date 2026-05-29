package inventory

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
)

type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

func New(baseURL, token string) *Client {
	return &Client{baseURL: baseURL, token: token, http: &http.Client{}}
}

type SSHTarget struct {
	OrganizationID string   `json:"organization_id"`
	ProjectID      string   `json:"project_id"`
	AgentID        string   `json:"agent_id"`
	VMName         string   `json:"vm_name"`
	GuestIP        string   `json:"guest_ip"`
	RelayHost      string   `json:"relay_host"`
	RelayPort      int      `json:"relay_port"`
	SSHReady       bool     `json:"ssh_ready"`
	IPs            []string `json:"ips"`
}

func (c *Client) ResolveTarget(
	ctx context.Context, organizationID, projectID, vmName string,
) (*SSHTarget, error) {
	q := url.Values{}
	q.Set("organization_id", organizationID)
	q.Set("project_id", projectID)
	q.Set("vm_name", vmName)
	u := c.baseURL + "/internal/v1/ssh/target?" + q.Encode()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-Huy-Service-Token", c.token)
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("target not found")
	}
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("inventory target: status %d", resp.StatusCode)
	}
	var out SSHTarget
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return &out, nil
}
