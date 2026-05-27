package wireguard

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"

	"golang.org/x/crypto/curve25519"
)

// GenerateKeyPair returns WireGuard-compatible base64 private and public keys.
func GenerateKeyPair() (privateKey string, publicKey string, err error) {
	var priv [32]byte
	if _, err := rand.Read(priv[:]); err != nil {
		return "", "", err
	}
	priv[0] &= 248
	priv[31] &= 127
	priv[31] |= 64

	var pub [32]byte
	curve25519.ScalarBaseMult(&pub, &priv)

	privateKey = base64.StdEncoding.EncodeToString(priv[:])
	publicKey = base64.StdEncoding.EncodeToString(pub[:])
	return privateKey, publicKey, nil
}

func MustGenerateKeyPair() (string, string) {
	priv, pub, err := GenerateKeyPair()
	if err != nil {
		panic(fmt.Sprintf("wireguard keygen: %v", err))
	}
	return priv, pub
}
