package sshbridge

import (
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"sync"
	"sync/atomic"

	"github.com/gorilla/websocket"
	"golang.org/x/crypto/ssh"

	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/iam"
	"github.com/imrekaposi-elastic/huygens/services/ssh-gateway/internal/relay"
)

const ctrlPrefix = byte(0)

type resizeControl struct {
	Type string `json:"type"`
	Cols int    `json:"cols"`
	Rows int    `json:"rows"`
}

type wsWriter struct {
	ws *websocket.Conn
	mu sync.Mutex
}

func (w *wsWriter) writeBinary(data []byte) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.ws.WriteMessage(websocket.BinaryMessage, data)
}

func (w *wsWriter) writeText(data string) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.ws.WriteMessage(websocket.TextMessage, []byte(data))
}

type wsBinaryWriter struct {
	out      *wsWriter
	onOutput func([]byte) error
}

func (w *wsBinaryWriter) Write(p []byte) (int, error) {
	if len(p) == 0 {
		return 0, nil
	}
	if w.onOutput != nil {
		_ = w.onOutput(p)
	}
	if err := w.out.writeBinary(p); err != nil {
		return 0, err
	}
	return len(p), nil
}

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
	inputCh := make(chan []byte, 256)
	var pendingResize []resizeControl
	var resizeMu sync.Mutex
	var activeSess atomic.Pointer[ssh.Session]

	// Read browser/CLI WebSocket frames immediately so keystrokes are not lost during relay+SSH setup.
	go func() {
		defer close(inputCh)
		defer func() {
			if s := activeSess.Load(); s != nil {
				_ = s.Close()
			}
		}()
		for {
			_, msg, err := ws.ReadMessage()
			if err != nil {
				return
			}
			if len(msg) > 0 && msg[0] == ctrlPrefix {
				var ctrl resizeControl
				if json.Unmarshal(msg[1:], &ctrl) == nil && ctrl.Type == "resize" && ctrl.Cols > 0 && ctrl.Rows > 0 {
					if s := activeSess.Load(); s != nil {
						_ = s.WindowChange(ctrl.Rows, ctrl.Cols)
					} else {
						resizeMu.Lock()
						pendingResize = append(pendingResize, ctrl)
						resizeMu.Unlock()
					}
				}
				continue
			}
			inputCh <- msg
		}
	}()

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

	const defaultCols, defaultRows = 120, 32
	if err := sess.RequestPty("xterm-256color", defaultCols, defaultRows, ssh.TerminalModes{
		ssh.ECHO:          1,
		ssh.ICANON:        1,
		ssh.ISIG:          1,
		ssh.IEXTEN:        1,
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

	activeSess.Store(sess)
	resizeMu.Lock()
	for _, ctrl := range pendingResize {
		_ = sess.WindowChange(ctrl.Rows, ctrl.Cols)
	}
	resizeMu.Unlock()

	go func() {
		<-ctx.Done()
		_ = sess.Close()
	}()

	wsOut := &wsWriter{ws: ws}
	_ = wsOut.writeText("huy:ready\n")
	_, _ = stdin.Write([]byte("\r"))

	var wg sync.WaitGroup
	outWriter := &wsBinaryWriter{out: wsOut, onOutput: onOutput}

	wg.Add(1)
	go func() {
		defer wg.Done()
		_, _ = io.Copy(outWriter, stdout)
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		for msg := range inputCh {
			if onInput != nil {
				_ = onInput(msg)
			}
			if _, werr := stdin.Write(msg); werr != nil {
				return
			}
		}
	}()

	wg.Wait()
	return nil
}
