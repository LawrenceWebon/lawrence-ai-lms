#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";

const sourcePath = "contracts/openapi/openapi.json";
const outputPath = "packages/api-client/src/generated/schema.d.ts";
const schema = JSON.parse(readFileSync(sourcePath, "utf8"));

function requireStepZeroShape() {
  if (!String(schema.openapi).startsWith("3.1.")) {
    throw new Error("The generated client requires an OpenAPI 3.1 document.");
  }
  const pathNames = Object.keys(schema.paths ?? {});
  if (pathNames.length !== 1 || pathNames[0] !== "/health") {
    throw new Error("Step 0 may generate only the /health API path.");
  }
  const healthOperation = schema.paths["/health"]?.get;
  if (
    healthOperation?.operationId !== "healthCheck" ||
    healthOperation?.responses?.["200"]?.content?.["application/json"]?.schema?.$ref !==
      "#/components/schemas/HealthResponse"
  ) {
    throw new Error("The /health operation no longer matches the frozen Step 0 client contract.");
  }
  const health = schema.components?.schemas?.HealthResponse;
  const properties = health?.properties ?? {};
  const required = health?.required ?? [];
  if (
    health?.type !== "object" ||
    properties.capabilities?.type !== "array" ||
    properties.capabilities?.items?.type !== "string" ||
    properties.service?.type !== "string" ||
    properties.status?.type !== "string" ||
    !["capabilities", "service", "status"].every((name) => required.includes(name))
  ) {
    throw new Error("HealthResponse no longer matches the frozen Step 0 client contract.");
  }
}

function render() {
  requireStepZeroShape();
  return `// GENERATED from contracts/openapi/openapi.json; DO NOT EDIT.
export interface paths {
  "/health": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["healthCheck"];
  };
}

export interface components {
  schemas: {
    HealthResponse: {
      capabilities: string[];
      service: string;
      status: string;
    };
  };
}

export interface operations {
  healthCheck: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: Record<string, unknown>;
        content: {
          "application/json": components["schemas"]["HealthResponse"];
        };
      };
    };
  };
}
`;
}

const expected = render();
if (process.argv.includes("--check")) {
  const current = readFileSync(outputPath, "utf8");
  if (current !== expected) {
    throw new Error(`Generated client drift detected; run node ${process.argv[1]}`);
  }
  console.log("Generated TypeScript API schema is current.");
} else {
  writeFileSync(outputPath, expected, "utf8");
  console.log(`Generated ${outputPath}`);
}
