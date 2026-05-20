import { describe, expect, it } from "vitest";
import { isValidOrgSlug, slugFromName } from "@/auth/setup";

describe("slugFromName", () => {
  it("normalizes names", () => {
    expect(slugFromName("Acme Corp")).toBe("acme-corp");
    expect(slugFromName("  Foo---Bar  ")).toBe("foo-bar");
  });
});

describe("isValidOrgSlug", () => {
  it("accepts IAM slug pattern", () => {
    expect(isValidOrgSlug("acme")).toBe(true);
    expect(isValidOrgSlug("acme-corp-2")).toBe(true);
    expect(isValidOrgSlug("-bad")).toBe(false);
    expect(isValidOrgSlug("")).toBe(false);
  });
});
