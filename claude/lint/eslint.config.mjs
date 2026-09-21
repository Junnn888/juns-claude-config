// Flat config for the lint kit. Never copied into a project: `kit.sh` points
// ESLint here with --no-config-lookup so the project's own config, if any, is
// ignored and this one cannot be edited from inside the repo under review.
//
// Per-repo settings arrive via JUN_LINT_SETTINGS (a path to a JSON file that
// kit.sh writes under ~/.claude/lint/projects/). Unset or unreadable means
// "no Tailwind entry known", and the Tailwind rules stay off.

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import betterTailwindcss from "eslint-plugin-better-tailwindcss";
import sonarjs from "eslint-plugin-sonarjs";
import tseslint from "typescript-eslint";

const SOURCE_FILES = ["**/*.{js,jsx,mjs,cjs,ts,tsx}"];

function readSettings() {
  const location = process.env.JUN_LINT_SETTINGS;
  if (!location) return null;
  try {
    return JSON.parse(readFileSync(location, "utf8"));
  } catch {
    return null;
  }
}

const settings = readSettings();
const tailwindEntry =
  settings?.tailwindEntry && existsSync(resolve(process.cwd(), settings.tailwindEntry))
    ? settings.tailwindEntry
    : null;

// Anchored so the allowlist lookaheads see the whole class: data/aria/group-data
// attribute variants and the CSS functions that have no token equivalent.
const ARBITRARY_VALUE_PATTERN = [
  "^",
  "(?!.*(?:^|:)(?:group-|peer-)?(?:data|aria)-\\[)",
  "(?!.*\\[(?:calc|var|env|theme)\\()",
  "(?!.*\\[--)",
  ".*\\[([^\\[\\]]*?)\\](?!:)",
].join("");

const tailwindConfigs = tailwindEntry
  ? [
      {
        files: SOURCE_FILES,
        plugins: { "better-tailwindcss": betterTailwindcss },
        settings: {
          "better-tailwindcss": {
            entryPoint: tailwindEntry,
          },
        },
        rules: {
          "better-tailwindcss/no-restricted-classes": [
            "error",
            {
              restrict: [
                {
                  pattern: ARBITRARY_VALUE_PATTERN,
                  message: `Arbitrary bracket values are banned. Use a token from ${tailwindEntry} (@theme) instead`,
                },
              ],
            },
          ],
        },
      },
    ]
  : [];

export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/dist/**",
      "**/build/**",
      "**/out/**",
      "**/coverage/**",
      "**/.turbo/**",
      "**/.vercel/**",
      "**/.svelte-kit/**",
      "**/storybook-static/**",
      "**/generated/**",
      "**/__generated__/**",
      "**/*.d.ts",
    ],
  },
  {
    files: ["**/*.{js,jsx,mjs,cjs}"],
    languageOptions: {
      parser: tseslint.parser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tseslint.parser,
      ecmaVersion: "latest",
      sourceType: "module",
    },
  },
  {
    files: ["**/*.tsx"],
    languageOptions: {
      parser: tseslint.parser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
  {
    files: SOURCE_FILES,
    plugins: { sonarjs },
    // The project's own eslint-disable comments name plugins this kit does not
    // load, and ESLint reports each one as "Definition for rule X was not
    // found" — an error attributed to X, which lands in the snapshot and then
    // blocks the gate the moment anyone adds another disable comment. Ignoring
    // inline config drops that noise, and also stops a disable comment
    // silencing a kit rule, which the gate asks for anyway.
    linterOptions: { noInlineConfig: true },
    rules: {
      "max-lines": ["error", { max: 400, skipBlankLines: true, skipComments: true }],
      "max-lines-per-function": ["error", { max: 80, skipBlankLines: true, skipComments: true }],
      complexity: ["error", 12],
      "max-params": ["error", 4],
      "max-depth": ["error", 4],
      "sonarjs/cognitive-complexity": ["error", 15],
    },
  },
  ...tailwindConfigs,
];
