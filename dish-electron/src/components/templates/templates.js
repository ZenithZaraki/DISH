/**
 * @file
 * this file exists to give a clear error message if the templates folder is ever
 * included as though it were a component
 */


throw new Error("the templates folder is not a component, it contains templates for common component styles and must not be included");
