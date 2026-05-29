package jwtutil

import (
	"fmt"

	"github.com/golang-jwt/jwt/v5"
)

type Claims struct {
	Sub            string                   `json:"sub"`
	Email          string                   `json:"email"`
	Username       string                   `json:"username"`
	PlatformRoles  []string                 `json:"platform_roles"`
	OrgMemberships []map[string]any         `json:"org_memberships"`
	ProjectRoles   []map[string]any         `json:"project_roles"`
	jwt.RegisteredClaims
}

func Parse(token string, secret, issuer string) (*Claims, error) {
	claims := &Claims{}
	parsed, err := jwt.ParseWithClaims(
		token,
		claims,
		func(t *jwt.Token) (any, error) {
			if t.Method != jwt.SigningMethodHS256 {
				return nil, fmt.Errorf("unexpected signing method")
			}
			return []byte(secret), nil
		},
		jwt.WithIssuer(issuer),
	)
	if err != nil {
		return nil, err
	}
	if !parsed.Valid {
		return nil, fmt.Errorf("invalid token")
	}
	return claims, nil
}
