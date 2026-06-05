package session

import (
	"testing"
	"time"
)

func TestStorePutGetListCloseDelete(t *testing.T) {
	store := NewStore()
	sess := &Session{
		ID:             "sess-1",
		OrganizationID: "org-1",
		ProjectID:      "proj-1",
		VMName:         "web-01",
		UserID:         "user-1",
		Status:         "active",
		StartedAt:      time.Now().UTC(),
	}
	store.Put(sess)

	got, ok := store.Get("sess-1")
	if !ok || got.VMName != "web-01" {
		t.Fatalf("get = %+v ok=%v", got, ok)
	}

	list := store.List("org-1")
	if len(list) != 1 {
		t.Fatalf("list len = %d", len(list))
	}
	if len(store.List("other-org")) != 0 {
		t.Fatal("expected empty list for other org")
	}

	closed, ok := store.Close("sess-1")
	if !ok || closed.Status != "closed" || closed.EndedAt == nil {
		t.Fatalf("closed = %+v", closed)
	}

	store.Delete("sess-1")
	if _, ok := store.Get("sess-1"); ok {
		t.Fatal("expected session deleted")
	}
}
