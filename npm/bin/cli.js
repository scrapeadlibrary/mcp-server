#!/usr/bin/env node

/**
 * npm wrapper for the ScrapeAdLibrary MCP server.
 * Spawns the Python package via uvx (preferred) or python3 -m.
 */

const { spawn } = require("child_process");

// Brand: keep the Python package/module names in one place.
const PY_PACKAGE = "scrapeadlibrary-mcp";
const PY_MODULE = "scrapeadlibrary_mcp.server";

function run(command, args) {
  const child = spawn(command, args, {
    stdio: "inherit",
    env: process.env,
  });
  child.on("error", (err) => {
    console.error(
      `Could not start the MCP server (${err.message}).\n` +
        `Install uv (https://docs.astral.sh/uv/) or run: pip install ${PY_PACKAGE}`
    );
    process.exit(1);
  });
  child.on("exit", (code) => process.exit(code ?? 1));
  return child;
}

// Try uvx first (fast, no install needed)
const uvx = spawn("uvx", [PY_PACKAGE], {
  stdio: "inherit",
  env: process.env,
});

uvx.on("error", () => {
  // uvx not available, fall back to python3 -m
  run("python3", ["-m", PY_MODULE]);
});

uvx.on("exit", (code) => {
  if (code !== null) process.exit(code);
});
