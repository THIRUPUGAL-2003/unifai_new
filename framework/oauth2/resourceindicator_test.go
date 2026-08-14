package oauth2

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"

	unifai "github.com/unifai/unifai/core"
	"github.com/unifai/unifai/core/schemas"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDiscoverOAuthMetadataIncludesResourceIndicator(t *testing.T) {
	SetLogger(unifai.NewDefaultLogger(schemas.LogLevelError))

	var server *httptest.Server
	server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/mcp":
			w.Header().Set("WWW-Authenticate", `Bearer resource_metadata="`+server.URL+`/.well-known/oauth-protected-resource"`)
			w.WriteHeader(http.StatusUnauthorized)
		case "/.well-known/oauth-protected-resource":
			require.NoError(t, json.NewEncoder(w).Encode(ResourceMetadata{
				Resource:             server.URL,
				AuthorizationServers: []string{server.URL},
			}))
		case "/.well-known/oauth-authorization-server":
			require.NoError(t, json.NewEncoder(w).Encode(OAuthMetadata{
				AuthorizationURL: server.URL + "/authorize",
				TokenURL:         server.URL + "/token",
			}))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	metadata, err := DiscoverOAuthMetadata(context.Background(), server.URL+"/mcp")
	require.NoError(t, err)
	assert.Equal(t, server.URL, metadata.Resource)
	assert.Equal(t, server.URL+"/authorize", metadata.AuthorizationURL)
	assert.Equal(t, server.URL+"/token", metadata.TokenURL)
}

func TestOAuthRequestsIncludeResourceIndicator(t *testing.T) {
	const resource = "https://mcp.example.com"
	provider := &OAuth2Provider{}

	authorizeURL := provider.buildAuthorizeURLWithPKCE(
		"https://auth.example.com/authorize",
		"client-id",
		"https://gateway.example.com/callback",
		"state",
		"challenge",
		[]string{"read", "write"},
		resource,
	)
	parsedAuthorizeURL, err := url.Parse(authorizeURL)
	require.NoError(t, err)
	assert.Equal(t, resource, parsedAuthorizeURL.Query().Get("resource"))

	var receivedForms []url.Values
	tokenServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.NoError(t, r.ParseForm())
		receivedForms = append(receivedForms, r.PostForm)
		w.Header().Set("Content-Type", "application/json")
		_, err := w.Write([]byte(`{"access_token":"token","token_type":"Bearer"}`))
		require.NoError(t, err)
	}))
	defer tokenServer.Close()

	_, err = provider.exchangeCodeForTokensWithPKCE(
		context.Background(),
		tokenServer.URL,
		"code",
		"client-id",
		"",
		"https://gateway.example.com/callback",
		"verifier",
		resource,
	)
	require.NoError(t, err)

	_, err = provider.exchangeRefreshToken(
		context.Background(),
		tokenServer.URL,
		"client-id",
		"",
		"refresh-token",
		resource,
	)
	require.NoError(t, err)

	require.Len(t, receivedForms, 2)
	assert.Equal(t, resource, receivedForms[0].Get("resource"))
	assert.Equal(t, resource, receivedForms[1].Get("resource"))
	assert.NotContains(t, receivedForms[0], "client_secret")
	assert.NotContains(t, receivedForms[1], "client_secret")
}
