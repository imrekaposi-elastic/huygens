package wireguard

import (
	"encoding/base64"
	"testing"

	"golang.org/x/crypto/curve25519"
)

func TestGenerateKeyPair(t *testing.T) {
	priv, pub, err := GenerateKeyPair()
	if err != nil {
		t.Fatalf("GenerateKeyPair: %v", err)
	}
	if priv == "" || pub == "" {
		t.Fatal("expected non-empty keys")
	}

	privBytes, err := base64.StdEncoding.DecodeString(priv)
	if err != nil || len(privBytes) != 32 {
		t.Fatalf("invalid private key encoding: len=%d err=%v", len(privBytes), err)
	}
	pubBytes, err := base64.StdEncoding.DecodeString(pub)
	if err != nil || len(pubBytes) != 32 {
		t.Fatalf("invalid public key encoding: len=%d err=%v", len(pubBytes), err)
	}

	var derived [32]byte
	var privArr [32]byte
	var pubArr [32]byte
	copy(privArr[:], privBytes)
	copy(pubArr[:], pubBytes)
	curve25519.ScalarBaseMult(&derived, &privArr)
	if derived != pubArr {
		t.Fatal("public key does not match private key scalar base mult")
	}

	priv2, pub2, err := GenerateKeyPair()
	if err != nil {
		t.Fatalf("second GenerateKeyPair: %v", err)
	}
	if priv == priv2 || pub == pub2 {
		t.Fatal("expected distinct keypairs from random generation")
	}
}

func TestMustGenerateKeyPair(t *testing.T) {
	priv, pub := MustGenerateKeyPair()
	if priv == "" || pub == "" {
		t.Fatal("expected non-empty keys from MustGenerateKeyPair")
	}
}
