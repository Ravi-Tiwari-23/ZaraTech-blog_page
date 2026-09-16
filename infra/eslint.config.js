import eslint from "@eslint/js";
import awscdk from "eslint-plugin-awscdk";
import prettier from "eslint-config-prettier";
import tseslint from "typescript-eslint";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    files: ["**/*.ts"],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: { awscdk },
    rules: {
      ...awscdk.configs.recommended.rules,
    },
  },
  prettier,
);
