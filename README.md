# Elaboration
Find potential circular dependencies in Ada programs

Work only from source files, no parsing of Ada sematics or syntax.

Collect package names from the filenames.
Collect with'd packages by scanning each file for the with statements.
