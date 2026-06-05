package jwtutil

import (
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

const testSecret = "test-jwt-secret-key-minimum-32-bytes!"
const testIssuer = "huy-iam"

func signTestToken(t *testing.T, claims Claims) string {
	t.Helper()
	claims.RegisteredClaims = jwt.RegisteredClaims{
		Issuer:    testIssuer,
		ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Hour)),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString([]byte(testSecret))
	if err != nil {
		t.Fatalf("sign: %v", err)
	}
	return signed
}

func TestParseValidToken(t *testing.T) {
	signed := signTestToken(t, Claims{
		Sub:      "user-1",
		Email:    "u@example.com",
		Username: "u1",
		OrgMemberships: []map[string]any{
			{"organization_id": "org-1", "roles": []any{"admin"}},
		},
	})
	parsed, err := Parse(signed, testSecret, testIssuer)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if parsed.Sub != "user-1" || parsed.Username != "u1" {
		t.Fatalf("claims = %+v", parsed)
	}
}

func TestParseRejectsBadToken(t *testing.T) {
	if _, err := Parse("not-a-jwt", testSecret, testIssuer); err == nil {
		t.Fatal("expected error for invalid token")
	}
}

func TestParseRejectsWrongIssuer(t *testing.T) {
	signed := signTestToken(t, Claims{Sub: "user-1"})
	if _, err := Parse(signed, testSecret, "wrong-issuer"); err == nil {
		t.Fatal("expected issuer mismatch error")
	}
}
