import createClient from "openapi-fetch";

import type { paths } from "./generated/schema";

export type { components, operations, paths } from "./generated/schema";

export function createApiClient(baseUrl: string) {
  return createClient<paths>({ baseUrl });
}
