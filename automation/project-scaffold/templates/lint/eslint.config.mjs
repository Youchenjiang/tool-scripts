// @ts-check
import js from "@eslint/js";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

/**
 * Project Scaffolding Strict Code Quality Config
 * 
 * Pre-aligned with:
 * - SonarCloud Quality Gate (e.g. S3358 no nested ternaries)
 * - DeepSource JavaScript / TypeScript Analyzer (class-methods-use-this)
 * - Zero non-null assertion policy (@typescript-eslint/no-non-null-assertion)
 * - Semantic naming policy (id-length)
 */
export default [
    js.configs.recommended,
    {
        files: ["**/*.{ts,tsx,js,jsx,mjs,cjs}"],
        languageOptions: {
            parser: tsParser,
            parserOptions: {
                ecmaVersion: "latest",
                sourceType: "module",
            },
        },
        plugins: {
            "@typescript-eslint": tsPlugin,
        },
        rules: {
            // 1. Strict null safety: ban non-null assertion operator (!)
            "@typescript-eslint/no-non-null-assertion": "error",

            // 2. Semantic identifiers: ban single-letter variables except 2D/3D math coordinates
            "id-length": ["error", { min: 2, exceptions: ["x", "y", "z", "_"] }],

            // 3. SonarCloud alignment: avoid complex nested ternary expressions (S3358)
            "no-nested-ternary": "error",

            // 4. DeepSource alignment: methods not using `this` must be declared static
            "class-methods-use-this": "error",

            // 5. Code cleanliness & dead code prevention
            "no-unused-vars": "off",
            "@typescript-eslint/no-unused-vars": [
                "error",
                {
                    argsIgnorePattern: "^_",
                    varsIgnorePattern: "^_",
                },
            ],
            "no-console": ["warn", { allow: ["warn", "error", "info"] }],
        },
    },
];
