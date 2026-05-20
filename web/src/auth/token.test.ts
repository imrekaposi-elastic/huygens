import { describe, expect, it } from "vitest";
import { parseTokenFromHash } from "@/auth/token";

describe("parseTokenFromHash", () => {
  it("reads access_token from fragment", () => {
    expect(parseTokenFromHash("#access_token=abc123&token_type=Bearer")).toBe("abc123");
  });

  it("returns null without fragment token", () => {
    expect(parseTokenFromHash("")).toBeNull();
  });
});
