import type { FieldValues, Resolver } from "react-hook-form";
import type { ZodType } from "zod";

/**
 * A minimal `react-hook-form` resolver backed by a Zod schema.
 *
 * The official `@hookform/resolvers` package isn't a project dependency, and the
 * adapter is small enough to own directly: run the schema's `safeParse`, return
 * the parsed (and coerced) values on success, or map the first issue per field
 * onto react-hook-form's error shape on failure.
 */
export function zodResolver<TIn extends FieldValues, TOut extends FieldValues>(
  schema: ZodType<TOut, TIn>
): Resolver<TIn, unknown, TOut> {
  return (values) => {
    const result = schema.safeParse(values);
    if (result.success) {
      return { values: result.data, errors: {} };
    }

    const errors: Record<string, { type: string; message: string }> = {};
    for (const issue of result.error.issues) {
      const key = issue.path[0];
      // Keep the first error per field — react-hook-form shows one message each.
      if (typeof key === "string" && !(key in errors)) {
        errors[key] = { type: issue.code, message: issue.message };
      }
    }

    return { values: {} as TOut, errors: errors as never };
  };
}
