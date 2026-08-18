import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const STYLES_DIR = path.resolve(__dirname, "..");
const COMPONENTS_DIR = path.resolve(__dirname, "../../components");
const APP_DIR = path.resolve(__dirname, "../../app");

function tokenNames(cssFile: string): Set<string> {
  const content = fs.readFileSync(path.join(STYLES_DIR, cssFile), "utf-8");
  const matches = content.matchAll(/--([a-z0-9-]+):/g);
  return new Set(Array.from(matches, (m) => m[1]!));
}

function walk(dir: string, exts: string[]): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "__tests__" || entry.name === "mocks" || entry.name === "node_modules") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full, exts));
    else if (exts.some((e) => entry.name.endsWith(e))) out.push(full);
  }
  return out;
}

// A hardcoded hex/rgb color literal in a component file, outside the token
// files themselves — this is the boundary constitution Principle VIII draws.
const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d/;

describe("design tokens", () => {
  it("dark and light sets define the same token names", () => {
    const dark = tokenNames("tokens.dark.css");
    const light = tokenNames("tokens.light.css");
    for (const name of dark) expect(light.has(name), `light set missing --${name}`).toBe(true);
    for (const name of light) expect(dark.has(name), `dark set missing --${name}`).toBe(true);
  });

  it("no component file contains a hardcoded color literal", () => {
    const files = [...walk(COMPONENTS_DIR, [".tsx", ".ts"]), ...walk(APP_DIR, [".tsx", ".ts"])];
    const offenders = files.filter((f) => COLOR_LITERAL.test(fs.readFileSync(f, "utf-8")));
    expect(offenders).toEqual([]);
  });
});
