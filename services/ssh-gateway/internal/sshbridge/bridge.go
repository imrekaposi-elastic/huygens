package sshbridge

import (
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"fmt"
	"sync"

	"github.com/gorilla/websocket"
	"golang.org/x/crypto/ssh"

	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/iam"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/relay"
)

type SessionTarget struct {
	OrganizationID string
	SessionID      string
	AgentID        string
	GuestIP        string
	RelayHost      string
	RelayPort      int
	RelayWSURL     string
	LinuxUser      string
}

// BridgeWebSocket runs an SSH client to the guest via the agent relay and copies PTY I/O to ws.
func BridgeWebSocket(
	ctx context.Context,
	ws *websocket.Conn,
	iamClient *iam.Client,
	relaySecret string,
	target SessionTarget,
	onInput, onOutput func([]byte) error,
) error {
	relayConn, err := relay.DialRelaySSH(
		target.RelayHost,
		target.RelayPort,
		target.RelayWSURL,
		relaySecret,
		target.SessionID,
		target.AgentID,
		target.GuestIP,
		target.LinuxUser,
	)
	if err != nil {
		return fmt.Errorf("relay: %w", err)
	}
	defer relayConn.Close()

	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return fmt.Errorf("generate key: %w", err)
	}
	signer, err := ssh.NewSignerFromKey(priv)
	if err != nil {
		return fmt.Errorf("signer: %w", err)
	}
	pubLine := string(ssh.MarshalAuthorizedKey(signer.PublicKey()))
	signed, err := iamClient.SignCert(ctx, iam.SignCertRequest{
		OrganizationID:   target.OrganizationID,
		LinuxUsername:    target.LinuxUser,
		SessionID:        target.SessionID,
		PublicKeyOpenSSH: pubLine,
	})
	if err != nil {
		return fmt.Errorf("sign cert: %w", err)
	}
	certPub, _, _, _, err := ssh.ParseAuthorizedKey([]byte(signed.CertificateOpenSSH))
	if err != nil {
		return fmt.Errorf("parse cert: %w", err)
	}
	cert, ok := certPub.(*ssh.Certificate)
	if !ok {
		return fmt.Errorf("expected ssh certificate")
	}
	certSigner, err := ssh.NewCertSigner(cert, signer)
	if err != nil {
		return fmt.Errorf("cert signer: %w", err)
	}

	addr := target.GuestIP + ":22"
	sshConn, chans, reqs, err := ssh.NewClientConn(relayConn, addr, &ssh.ClientConfig{
		User:            target.LinuxUser,
		Auth:            []ssh.AuthMethod{ssh.PublicKeys(certSigner)},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), //nolint:gosec // guest keys rotate; trust via org CA user cert
	})
	if err != nil {
		return fmt.Errorf("ssh connect: %w", err)
	}
	client := ssh.NewClient(sshConn, chans, reqs)
	defer client.Close()

	sess, err := client.NewSession()
	if err != nil {
		return fmt.Errorf("ssh session: %w", err)
	}
	defer sess.Close()

	if err := sess.RequestPty("xterm", 80, 24, ssh.TerminalModes{
		ssh.ECHO:          1,
		ssh.TTY_OP_ISPEED: 14400,
		ssh.TTY_OP_OSPEED: 14400,
	}); err != nil {
		return fmt.Errorf("pty: %w", err)
	}
	stdin, err := sess.StdinPipe()
	if err != nil {
		return err
	}
	stdout, err := sess.StdoutPipe()
	if err != nil {
		return err
	}
	if err := sess.Shell(); err != nil {
		return fmt.Errorf("shell: %w", err)
	}

	var wg sync.WaitGroup
	done := make(chan struct{})

	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			_, msg, err := ws.ReadMessage()
			if err != nil {
				return
			}
			if onInput != nil {
				_ = onInput(msg)
			}
			if _, werr := stdin.Write(msg); werr != nil {
				return
			}
		}
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		buf := make([]byte, 32*1024)
		for {
			n, err := stdout.Read(buf)
			if n > 0 {
				if onOutput != nil {
					_ = onOutput(buf[:n])
				}
				if werr := ws.WriteMessage(websocket.BinaryMessage, buf[:n]); werr != nil {
					return
				}
			}
			if err != nil {
				return
			}
		}
	}()

	wg.Wait()
	close(done)
	return nil
}
