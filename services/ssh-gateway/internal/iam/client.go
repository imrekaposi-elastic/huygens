package iam

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

func New(baseURL, token string) *Client {
	return &Client{baseURL: baseURL, token: token, http: &http.Client{}}
}

type AuthorizeRequest struct {
	OrganizationID       string `json:"organization_id"`
	ProjectID            string `json:"project_id"`
	VMName               string `json:"vm_name"`
	VMAssignedToProject  bool   `json:"vm_assigned_to_project"`
	UserID               string `json:"user_id"`
	UserEmail            string `json:"user_email"`
	UserUsername         string `json:"user_username"`
	PlatformRoles        []string                 `json:"platform_roles"`
	OrgMemberships       []map[string]any         `json:"org_memberships"`
	ProjectRoles         []map[string]any         `json:"project_roles"`
}

type AuthorizeResponse struct {
	Allowed        bool     `json:"allowed"`
	Reason         string   `json:"reason"`
	LinuxUsername  *string  `json:"linux_username"`
	SudoersLines   []string `json:"sudoers_lines"`
	CAPublicKey    *string  `json:"ca_public_key"`
}

func (c *Client) Authorize(ctx context.Context, req AuthorizeRequest) (*AuthorizeResponse, error) {
	body, _ := json.Marshal(req)
	httpReq, err := http.NewRequestWithContext(
		ctx, http.MethodPost, c.baseURL+"/internal/v1/ssh/authorize", bytes.NewReader(body),
	)
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("X-Huy-Service-Token", c.token)
	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("iam authorize: status %d", resp.StatusCode)
	}
	var out AuthorizeResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return &out, nil
}

type SignCertRequest struct {
	OrganizationID   string `json:"organization_id"`
	LinuxUsername    string `json:"linux_username"`
	SessionID        string `json:"session_id"`
	PublicKeyOpenSSH string `json:"public_key_openssh"`
}

type SignCertResponse struct {
	CertificateOpenSSH string `json:"certificate_openssh"`
	ValidAfter         int64  `json:"valid_after"`
	ValidBefore        int64  `json:"valid_before"`
}

func (c *Client) SignCert(ctx context.Context, req SignCertRequest) (*SignCertResponse, error) {
	body, _ := json.Marshal(req)
	httpReq, err := http.NewRequestWithContext(
		ctx, http.MethodPost, c.baseURL+"/internal/v1/ssh/sign-cert", bytes.NewReader(body),
	)
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("X-Huy-Service-Token", c.token)
	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("iam sign-cert: status %d", resp.StatusCode)
	}
	var out SignCertResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return &out, nil
}
